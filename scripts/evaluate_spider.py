"""Evaluate all selected IDs with the legacy official Spider EX implementation."""

import argparse
from pathlib import Path

from scripts.common.contracts import validate_predictions
from scripts.common.evaluator import official_match, suite_match
from scripts.common.io import (
    ROOT,
    db_path,
    digest,
    file_hash,
    read_json,
    read_jsonl,
    write_json,
    write_jsonl,
)
from scripts.common.provenance import git_info
from scripts.common.schema import load_schemas
from scripts.common.sqlite_guard import execute

METRICS = {
    "legacy": "legacy_spider_execution_accuracy",
    "execution": "single_database_execution_accuracy",
    "test-suite": "test_suite_execution_accuracy",
}


def evaluate(
    inputs,
    predictions,
    gold_rows,
    tables,
    db_root,
    evaluator,
    timeout_s=5,
    metric="legacy",
    suite_root=None,
):
    validate_predictions(predictions, inputs)
    gold = {}
    for row in gold_rows:
        if row["example_id"] in gold:
            raise ValueError("Duplicate gold ID")
        gold[row["example_id"]] = row
    pred = {r["example_id"]: r for r in predictions}
    results = []
    for item in inputs:
        eid, dbid = item["example_id"], item["db_id"]
        if eid not in gold or gold[eid]["db_id"] != dbid:
            raise ValueError("Gold ID/db_id mismatch")
        row = pred[eid]
        path = db_path(db_root, dbid)
        evaluation_path = db_path(suite_root, dbid) if metric == "test-suite" else path
        if metric == "test-suite" and len(list(evaluation_path.parent.glob("*.sqlite"))) < 2:
            raise ValueError(f"Test suite for {dbid} needs generated neighbor databases")

        def match(prediction):
            if metric == "legacy":
                return official_match(
                    evaluator, path, prediction, gold[eid]["query"], tables[dbid], timeout_s
                )
            return suite_match(
                evaluator, evaluation_path, prediction, gold[eid]["query"], timeout_s
            )

        # Gold/harness validation applies even when the prediction is absent.
        gold_check = execute(path, gold[eid]["query"], timeout_s)
        if gold_check["status"] != "ok":
            raise ValueError(f"Gold execution failed for {eid}: {gold_check['status']}")
        baseline = match(gold[eid]["query"])
        if baseline["status"] != "ok" or not baseline["correct"]:
            raise ValueError(f"Evaluator self-check failed for {eid}: {baseline}")
        result = {
            "example_id": eid,
            "db_id": dbid,
            "prediction_status": row["status"],
            "execution_status": "not_run",
            "correct": False,
            "metric": METRICS[metric],
        }
        if row.get("predicted_sql") and row["status"] == "ok":
            execution = execute(path, row["predicted_sql"], timeout_s)
            if execution["status"] == "harness_error":
                raise ValueError(f"Query harness failed for {eid}")
            result["execution_status"] = execution["status"]
            if execution["status"] == "ok":
                official = match(row["predicted_sql"])
                if official["status"] != "ok":
                    raise ValueError(f"Official evaluation failed for {eid}: {official}")
                result["correct"] = official["correct"]
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--tables", required=True)
    parser.add_argument("--db-root", required=True)
    parser.add_argument("--evaluator")
    parser.add_argument("--metric", choices=list(METRICS), default="execution")
    parser.add_argument("--suite-db-root", help="Required for the generated test-suite metric")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    if args.metric == "test-suite" and not args.suite_db_root:
        parser.error("--metric test-suite requires --suite-db-root")
    evaluator_key = "spider" if args.metric == "legacy" else "test_suite"
    expected_evaluator = read_json(ROOT / "configs/upstream_lock.json")[evaluator_key]
    args.evaluator = args.evaluator or str(ROOT / "third_party" / expected_evaluator["directory"])
    inputs, manifest = read_jsonl(args.input), read_json(args.manifest)
    if file_hash(args.gold) != manifest["gold_hash"]:
        raise ValueError("Gold fingerprint mismatch")
    info = git_info(args.evaluator)
    if info["commit"] != expected_evaluator["commit"] or info["dirty"]:
        raise ValueError("Evaluator differs from pinned clean commit")
    if digest(inputs) not in {manifest["input_hash"], manifest["smoke_input_hash"]}:
        raise ValueError("Input does not match frozen manifest")
    if file_hash(args.tables) != manifest["source_hashes"]["tables.json"]:
        # Prepared tables.json may differ in whitespace; its content is checked via source hash
        # in prepare_spider's explicit prepared_tables_hash field.
        if file_hash(args.tables) != manifest.get("prepared_tables_hash"):
            raise ValueError("Tables fingerprint mismatch")
    for dbid in {r["db_id"] for r in inputs}:
        if file_hash(db_path(args.db_root, dbid)) != manifest["database_hashes"][dbid]:
            raise ValueError("DB fingerprint mismatch")
    results = evaluate(
        inputs,
        read_jsonl(args.predictions),
        read_jsonl(args.gold),
        load_schemas(args.tables),
        args.db_root,
        args.evaluator,
        args.timeout,
        args.metric,
        args.suite_db_root,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output / "evaluation.jsonl", results)
    write_json(
        args.output / "evaluation_config.json",
        {
            "metric": METRICS[args.metric],
            "evaluator": git_info(args.evaluator),
            "input_hash": digest(inputs),
            "prediction_hash": file_hash(args.predictions),
            "gold_hash": file_hash(args.gold),
            "manifest_hash": digest(manifest),
            "timeout_s": args.timeout,
            "read_only": True,
            "plug_value": False,
            "keep_distinct": True,
            "suite_database_hashes": (
                {
                    str(p.relative_to(args.suite_db_root)): file_hash(p)
                    for dbid in {r["db_id"] for r in inputs}
                    for p in (Path(args.suite_db_root) / dbid).glob("*.sqlite")
                }
                if args.metric == "test-suite"
                else None
            ),
            "note": "Official comparison logic unchanged; metric identifies database coverage.",
        },
    )
    print(f"{METRICS[args.metric]}: {sum(r['correct'] for r in results)}/{len(results)}")


if __name__ == "__main__":
    main()
