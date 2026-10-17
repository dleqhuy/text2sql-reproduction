"""Normalize ID-tagged native SQL rows or line outputs with an explicit ordered sidecar."""

import argparse
from pathlib import Path

from scripts.common.contracts import STATUSES, failure, validate_inputs, validate_predictions
from scripts.common.io import read_json, read_jsonl, write_jsonl


def normalize(inputs, native, method, model, sql_key="predicted_sql"):
    validate_inputs(inputs)
    expected = {r["example_id"]: r for r in inputs}
    found = {}
    for item in native:
        eid = item.get("example_id")
        if eid not in expected or eid in found:
            raise ValueError("Unknown or duplicate native output ID")
        row = expected[eid]
        if item.get("db_id", row["db_id"]) != row["db_id"]:
            raise ValueError("Native db_id mismatch")
        result = failure(row, method, model, "parse_error", "Native SQL is empty", "normalization")
        sql = item.get(sql_key)
        if isinstance(sql, str) and sql.strip():
            result.update(status="ok", error=None, predicted_sql=sql.strip())
        if item.get("status") in STATUSES - {"ok"}:
            result = failure(
                row, method, model, item["status"], "Upstream reported failure", "normalization"
            )
        if "variant" in item:
            result["variant"] = item["variant"]
        for key in ("latency_ms", "api_calls", "prompt_tokens", "completion_tokens"):
            result[key] = item.get(key)
        found[eid] = result
    result = [
        found.get(row["example_id"])
        or failure(
            row,
            method,
            model,
            "missing_prediction",
            "No native output for selected example",
            "normalization",
        )
        for row in inputs
    ]
    validate_predictions(result, inputs)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--native", required=True)
    parser.add_argument("--format", choices=["jsonl", "lines"], default="jsonl")
    parser.add_argument("--sidecar", help="JSON array of IDs in exact native line order")
    parser.add_argument("--sql-key", default="predicted_sql")
    parser.add_argument(
        "--method", choices=["vanilla", "dail_sql", "din_sql", "mac_sql"], required=True
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.format == "lines":
        if not args.sidecar:
            parser.error("Line outputs require --sidecar; alignment is never guessed")
        ids, lines = read_json(args.sidecar), Path(args.native).read_text().splitlines()
        if len(ids) != len(lines):
            raise ValueError("Native line count differs from sidecar")
        native = [
            {"example_id": eid, args.sql_key: sql} for eid, sql in zip(ids, lines, strict=True)
        ]
    else:
        native = read_jsonl(args.native)
    write_jsonl(
        args.output,
        normalize(read_jsonl(args.input), native, args.method, args.model, args.sql_key),
    )


if __name__ == "__main__":
    main()
