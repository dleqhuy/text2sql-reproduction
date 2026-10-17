"""Subprocess fixture for isolated upstream environments; no provider calls."""

import argparse
from types import SimpleNamespace

from scripts.common.io import ROOT
from scripts.common.methods import DIN, MAC


class FakeLLM:
    def __init__(self, method, branch="EASY"):
        self.creds = SimpleNamespace(model="fixture-model")
        self.method, self.branch = method, branch
        self.stages, self.events = [], []

    def record(self, event):
        self.events.append(event)

    def complete(self, prompt, stage="generation", *args, **kwargs):
        self.stages.append(stage)
        assert "private_dev_gold_marker" not in prompt
        if self.method == "din":
            replies = {
                "schema_linking": "Schema_links: [people.id]",
                "classification": f'Label: "{self.branch}" questions = ["count people"]',
                "generation_easy": "SELECT count(*) FROM people",
                "generation": "SQL: SELECT count(*) FROM people",
                "correction": (
                    "SELECT count(*) FROM people"
                    if self.branch == "NESTED"
                    else "count(*) FROM people"
                ),
            }
            return replies[stage]
        if stage == "Decomposer":
            return "```sql\nSELECT absent FROM people\n```"
        if stage == "Refiner":
            return "```sql\nSELECT count(*) FROM people\n```"
        return '{"people":"keep_all"}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", required=True)
    parser.add_argument("--db-root", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--branch", default="EASY")
    args = parser.parse_args()
    llm = FakeLLM(args.method, args.branch)
    if args.method == "din":
        method = DIN(llm, ROOT / "third_party/Few-shot-NL2SQL-with-prompting", args.tables)
    else:
        method = MAC(llm, ROOT / "third_party/MAC-SQL", args.tables, args.db_root, 2)
    sql = method.infer(
        {"example_id": "dev_000000", "db_id": "mini", "question": "How many people?"}
    )
    assert sql.strip().upper() == "SELECT COUNT(*) FROM PEOPLE", sql
    if args.method == "din":
        assert llm.stages[0:2] == ["schema_linking", "classification"]
        assert llm.stages[-1] == "correction"
        assert len(llm.stages) == 4
    else:
        assert "Decomposer" in llm.stages and "Refiner" in llm.stages
        assert llm.events[-1]["message"]["send_to"] == "System"
    print("Original upstream stages verified with fake transport")


if __name__ == "__main__":
    main()
