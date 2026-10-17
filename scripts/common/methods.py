"""Thin adapters that load original method prompts/classes from pinned checkouts."""

import ast
import re
import sys
import types
from pathlib import Path

from scripts.common.io import db_path, read_json
from scripts.common.schema import extract_sql, serialize
from scripts.common.sqlite_guard import execute, readonly_connect

VANILLA_PROMPT = """Write one SQLite query answering the question using this schema.
Return only the SQL query. Do not include explanations.

{schema}

Question: {question}
"""


def parse_din_classification(text, question):
    match = re.search(r'Label:\s*["\']?(NON-NESTED|NESTED|EASY)\b', text, re.IGNORECASE)
    if match:
        label = match.group(1).upper()
    else:
        emphasized = re.findall(r"\*\*(NON-NESTED|NESTED|EASY)\*\*", text, re.IGNORECASE)
        labels = {label.upper() for label in emphasized}
        if len(labels) != 1:
            raise ValueError("DIN classification label missing or ambiguous")
        label = labels.pop()
    sub = re.search(r"questions\s*=\s*(\[.*?\])", text, re.DOTALL | re.IGNORECASE)
    questions = None
    if sub:
        try:
            values = ast.literal_eval(sub.group(1))
            if (
                isinstance(values, list)
                and values
                and all(isinstance(q, str) and q for q in values)
            ):
                questions = " ".join(values)
        except (SyntaxError, ValueError):
            pass
    return label, questions or question, label == "NESTED" and questions is None


def parse_mac_sql(text):
    blocks = re.findall(r"```(?:sql|sqlite)\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if blocks:
        return extract_sql(blocks[-1])
    return extract_sql(text)


class Vanilla:
    def __init__(self, llm, schemas):
        self.llm, self.schemas = llm, schemas

    def infer(self, row):
        prompt = VANILLA_PROMPT.format(
            schema=serialize(self.schemas[row["db_id"]]), question=row["question"]
        )
        return extract_sql(self.llm.complete(prompt))


def load_din(repo, tables):
    """Skip upstream argv side effects and legacy SDK; compile original prompt definitions."""
    import pandas as pd

    path = Path(repo) / "DIN-SQL.py"
    # Pinned upstream ships an invalid placeholder assignment at line 444.
    # Replace only that exact non-executable credential stub before selecting definitions.
    source = path.read_text().replace("API_KEY = #key", "API_KEY = None")
    tree = ast.parse(source)
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if isinstance(value, str):
                keep.append(node)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("GPT4_"):
            keep.append(node)
    namespace = {"pd": pd}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(path), "exec"), namespace)
    namespace["spider_schema"], namespace["spider_primary"], namespace["spider_foreign"] = (
        namespace["creatiing_schema"](str(tables))
    )
    return namespace


class DIN:
    def __init__(self, llm, repo, tables, inputs=()):
        self.llm = llm
        self.source = load_din(repo, tables)
        demonstrations = [
            value.casefold()
            for key, value in self.source.items()
            if key.endswith("_prompt") and isinstance(value, str)
        ]
        for row in inputs:
            if any(row["question"].casefold() in prompt for prompt in demonstrations):
                raise ValueError("DIN hardcoded demonstration overlaps evaluation question")

    def infer(self, row):
        f, llm = self.source, self.llm
        question, dbid = row["question"], row["db_id"]
        links = llm.complete(
            f["schema_linking_prompt_maker"](question, dbid), "schema_linking", 600, ["Q:"]
        )
        links = links.split("Schema_links: ", 1)[1] if "Schema_links: " in links else "[]"
        classification = llm.complete(
            f["classification_prompt_maker"](question, dbid, links[1:]),
            "classification",
            600,
            ["Q:"],
        )
        predicted, sub, fallback = parse_din_classification(classification, question)
        if fallback:
            llm.record(
                {
                    "event": "parse_fallback",
                    "stage": "classification",
                    "reason": "missing_subquestions",
                    "fallback": "original_question",
                }
            )
        if predicted == "EASY":
            prompt = f["easy_prompt_maker"](question, dbid, links)
            sql = llm.complete(prompt, "generation_easy", 600, ["Q:"])
        else:
            if predicted == "NON-NESTED":
                prompt = f["medium_prompt_maker"](question, dbid, links)
            else:
                prompt = f["hard_prompt_maker"](question, dbid, links, sub)
            sql = llm.complete(prompt, "generation", 600, ["Q:"])
            sql = sql.split("SQL: ", 1)[1] if "SQL: " in sql else "SELECT"
        fixed = llm.complete(
            f["debuger"](question, dbid, sql), "correction", 350, ["#", ";", "\n\n"]
        )
        # Legacy completion continued after SELECT; compatible chat models may return a full query.
        # Preserve raw output and only avoid duplicating this transport-level prefix.
        fixed = fixed.replace("\n", " ").strip()
        return fixed if fixed.upper().startswith("SELECT") else "SELECT " + fixed


class MAC:
    def __init__(self, llm, repo, tables, db_root, timeout_s):
        self.llm = llm
        sys.path.insert(0, str(Path(repo).resolve()))
        bridge = types.ModuleType("core.llm")
        self.stage = "initialization"
        bridge.safe_call_llm = lambda prompt, **kw: llm.complete(prompt, self.stage)
        bridge.init_log_path = lambda path: None
        sys.modules["core.llm"] = bridge
        from core import agents
        from core.const import MAX_ROUND, SYSTEM_NAME

        agents.parse_sql_from_string = parse_mac_sql

        # Replace only connection factory in upstream modules; do not mutate sqlite3 globally here.
        safe_sqlite = types.SimpleNamespace(
            connect=lambda path, *a, **kw: readonly_connect(path, timeout_s)
        )
        agents.sqlite3 = safe_sqlite
        selector = agents.Selector(str(db_root), str(tables), llm.creds.model, "spider", lazy=True)
        # Upstream strips leading '/' from data_path; restore the verified absolute root.
        selector.data_path = str(Path(db_root).resolve())
        refiner = agents.Refiner(str(Path(db_root).resolve()), "spider")

        def guarded(sql, db_id):
            result = execute(db_path(db_root, db_id), sql, timeout_s)
            if result["status"] == "harness_error":
                raise RuntimeError("SQL worker failure")
            if result["status"] == "ok":
                return {
                    "sql": sql,
                    "data": result["data"],
                    "sqlite_error": "",
                    "exception_class": "",
                }
            return {
                "sql": sql,
                "sqlite_error": result.get("error", result["status"]),
                "exception_class": result["status"],
            }

        refiner._execute_sql = guarded
        self.agents = [selector, agents.Decomposer("spider"), refiner]
        self.max_round, self.system = MAX_ROUND, SYSTEM_NAME

    def infer(self, row):
        message = {
            "idx": row["example_id"],
            "db_id": row["db_id"],
            "query": row["question"],
            "evidence": "",
            "extracted_schema": {},
            "send_to": self.agents[0].name,
        }
        # Equivalent to ChatManager.start, excluding its unrelated Hello-world ping and gold logging.
        for round_id in range(self.max_round):
            for agent in self.agents:
                if message["send_to"] == agent.name:
                    self.stage = agent.name
                    agent.talk(message)
                    self.llm.record(
                        {
                            "event": "agent_transition",
                            "stage": self.stage,
                            "round": round_id,
                            "message": message.copy(),
                        }
                    )
            if message["send_to"] == self.system:
                break
        sql = message.get("pred") or message.get("final_sql")
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("MAC-SQL did not produce final SQL")
        return extract_sql(sql)


class DAILPrepared:
    """Inference on original DAIL prompts exported by prepare_dail; never label a random prompt DAIL."""

    def __init__(self, llm, bundle, inputs, manifest=None):
        self.llm = llm
        bundle = read_json(bundle)
        if bundle.get("generator") != "upstream-dail-prompt-factory-v1":
            raise ValueError("DAIL bundle must be generated by scripts.prepare_dail")
        from scripts.common.io import ROOT
        from scripts.common.provenance import git_info

        if bundle["upstream"] != git_info(ROOT / "third_party/DAIL-SQL"):
            raise ValueError("DAIL bundle was generated with a different upstream checkout")
        self.variant = bundle["stage"]
        if manifest:
            for name in ("dev.json", "tables.json", "train_spider.json"):
                if bundle["asset_hashes"].get(name) != manifest["source_hashes"][name]:
                    raise ValueError("DAIL assets differ from the frozen Spider source")
        self.prompts = {r["example_id"]: r for r in bundle["questions"]}
        if len(self.prompts) != len(bundle["questions"]):
            raise ValueError("Duplicate DAIL prompt ID")
        for row in inputs:
            prompt = self.prompts.get(row["example_id"], {})
            if prompt.get("db_id") != row["db_id"] or prompt.get("question") != row["question"]:
                raise ValueError("DAIL prompt/input mismatch")

    def infer(self, row):
        text = self.llm.complete(self.prompts[row["example_id"]]["prompt"], "dail_generation", 200)
        try:
            return parse_mac_sql(text)
        except ValueError:
            pass
        # Upstream SQL representation ends in SELECT and ask_llm adds that prefix if absent.
        text = " ".join(text.split())
        text = text.strip().split("/*")[0]
        return text if text.upper().startswith("SELECT") else "SELECT " + text
