"""Run the pinned legacy Spider evaluator without changing its comparison logic."""

import importlib.util
import sqlite3
import sys
from pathlib import Path

from scripts.common.io import ROOT
from scripts.common.sqlite_guard import isolated_call, readonly_connect


def _official_worker(pipe, repo, path, prediction, gold, table, timeout_s):
    try:
        import nltk

        nltk.data.path.insert(0, str(ROOT / "data/nltk_data"))
        nltk.data.find("tokenizers/punkt_tab/english/")
        sys.path.insert(0, repo)
        spec = importlib.util.spec_from_file_location(
            "spider_evaluation", Path(repo) / "evaluation.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The module and process_sql both reference sqlite3. Patch only in this disposable worker.
        sqlite3.connect = lambda db, *a, **kw: readonly_connect(db, timeout_s)
        schema = module.Schema(module.get_schema(path))
        gold_sql = module.get_sql(schema, gold)
        with readonly_connect(path, timeout_s) as conn:
            conn.execute(gold).fetchall()
        try:
            pred_sql = module.get_sql(schema, prediction)
        except (AssertionError, KeyError, ValueError, IndexError):
            # Same empty parse fallback used by upstream evaluate().
            pred_sql = {
                "except": None,
                "from": {"conds": [], "table_units": []},
                "groupBy": [],
                "having": [],
                "intersect": None,
                "limit": None,
                "orderBy": [],
                "select": [False, []],
                "union": None,
                "where": [],
            }
        kmap = module.build_foreign_key_map(table)

        def rebuild(parsed):
            valid = module.build_valid_col_units(parsed["from"]["table_units"], schema)
            return module.rebuild_sql_col(valid, module.rebuild_sql_val(parsed), kmap)

        correct = module.eval_exec_match(
            path, prediction, gold, rebuild(pred_sql), rebuild(gold_sql)
        )
        pipe.send({"status": "ok", "correct": bool(correct)})
    except LookupError:
        pipe.send({"status": "harness_error", "error": "NLTK punkt_tab is missing"})
    except Exception as exc:
        pipe.send(
            {"status": "harness_error", "error": f"Official evaluator failed: {type(exc).__name__}"}
        )
    finally:
        pipe.close()


def official_match(repo, path, prediction, gold, table, timeout_s=5):
    for name in ("evaluation.py", "process_sql.py"):
        if not (Path(repo) / name).is_file():
            raise FileNotFoundError(f"Missing official evaluator file: {name}")
    return isolated_call(
        _official_worker,
        (str(Path(repo).resolve()), str(path), prediction, gold, table, timeout_s),
        timeout_s + 5,
    )


def _suite_worker(pipe, repo, path, prediction, gold, timeout_s):
    try:
        import random

        random.seed(42)
        sys.path.insert(0, repo)
        spec = importlib.util.spec_from_file_location(
            "official_exec_eval", Path(repo) / "exec_eval.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sqlite3.connect = lambda db, *a, **kw: readonly_connect(db, timeout_s)
        # Keep the official query postprocessing, bag/column permutation and ordering semantics.
        correct = module.eval_exec_match(
            path,
            prediction,
            gold,
            plug_value=False,
            keep_distinct=True,
            progress_bar_for_each_datapoint=False,
        )
        pipe.send({"status": "ok", "correct": bool(correct)})
    except Exception as exc:
        pipe.send(
            {
                "status": "harness_error",
                "error": f"Test-suite evaluator failed: {type(exc).__name__}",
            }
        )
    finally:
        pipe.close()


def suite_match(repo, path, prediction, gold, timeout_s=5):
    for name in ("exec_eval.py", "parse.py"):
        if not (Path(repo) / name).is_file():
            raise FileNotFoundError(f"Missing test-suite evaluator file: {name}")
    count = len(list(Path(path).parent.glob("*.sqlite")))
    if not count:
        raise ValueError("Execution evaluation cannot use an empty database set")
    return isolated_call(
        _suite_worker,
        (str(Path(repo).resolve()), str(path), prediction, gold, timeout_s),
        timeout_s * count * 2 + 5,
    )
