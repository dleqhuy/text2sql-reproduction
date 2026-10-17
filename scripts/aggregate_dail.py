"""Account for both DAIL inference passes while retaining the final SQL and every selected ID."""

import argparse
from pathlib import Path

from scripts.common.contracts import validate_predictions
from scripts.common.io import digest, read_json, read_jsonl, write_json, write_jsonl


def aggregate(inputs, preliminary, final):
    validate_predictions(preliminary, inputs)
    validate_predictions(final, inputs)
    first = {r["example_id"]: r for r in preliminary}
    last = {r["example_id"]: r for r in final}
    rows = []
    for item in inputs:
        a, b = first[item["example_id"]], last[item["example_id"]]
        if a["method"] != "dail_sql" or b["method"] != "dail_sql" or a["model"] != b["model"]:
            raise ValueError("DAIL stage method/model mismatch")
        if a.get("variant") != "preliminary" or b.get("variant") != "final":
            raise ValueError("Expected distinct preliminary and final DAIL stages")
        row = {**b, "variant": "two-stage"}
        if a["status"] != "ok":
            row.update(status=a["status"], predicted_sql=None, error=a["error"])
        for key in ("api_calls", "latency_ms", "prompt_tokens", "completion_tokens"):
            row[key] = a[key] + b[key] if a[key] is not None and b[key] is not None else None
        rows.append(row)
    validate_predictions(rows, inputs)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--preliminary-run", required=True, type=Path)
    parser.add_argument("--final-run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Aggregate output already exists")
    first_config = read_json(args.preliminary_run / "run_config.json")
    last_config = read_json(args.final_run / "run_config.json")
    for key in ("model", "config", "endpoint_hash", "input_hash", "manifest_hash", "upstream"):
        if first_config["identity"].get(key) != last_config["identity"].get(key):
            raise ValueError(f"DAIL stage config mismatch: {key}")
    inputs = read_jsonl(args.input)
    if digest(inputs) != last_config["identity"]["input_hash"]:
        raise ValueError("Aggregate input differs from the stage manifests")
    rows = aggregate(
        inputs,
        read_jsonl(args.preliminary_run / "predictions.jsonl"),
        read_jsonl(args.final_run / "predictions.jsonl"),
    )
    write_jsonl(args.output / "predictions.jsonl", rows)
    write_json(args.output / "input_manifest.json", inputs)
    write_json(
        args.output / "run_config.json",
        {
            "status": "completed",
            "identity": {**last_config["identity"], "variant": "two-stage"},
            "parents": [str(args.preliminary_run), str(args.final_run)],
            "accounting": "Sum both generation passes; excludes offline linking/retrieval preparation",
        },
    )
    print(f"Aggregated both DAIL stages for {len(rows)} selected examples")


if __name__ == "__main__":
    main()
