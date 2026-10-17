"""Summarize complete evaluation rows; failed examples remain in the denominator."""

import argparse
import statistics
from collections import Counter
from pathlib import Path

from scripts.common.contracts import validate_predictions
from scripts.common.io import atomic_text, digest, file_hash, read_json, read_jsonl, write_json


def summarize(inputs, predictions, evaluations):
    validate_predictions(predictions, inputs)
    byid = {r["example_id"]: r for r in evaluations}
    if len(byid) != len(evaluations) or set(byid) != {r["example_id"] for r in inputs}:
        raise ValueError("Evaluation IDs differ from manifest or contain duplicates")
    for row in predictions:
        result = byid[row["example_id"]]
        if result["db_id"] != row["db_id"] or result["prediction_status"] != row["status"]:
            raise ValueError("Evaluation/prediction mismatch")
    total = len(inputs)
    correct = sum(bool(r["correct"]) for r in evaluations)
    valid = sum(r["execution_status"] == "ok" for r in evaluations)
    methods = {r["method"] for r in predictions}
    models = {r["model"] for r in predictions}
    if len(methods) != 1 or len(models) != 1:
        raise ValueError("Cannot mix methods/models within one run")
    result = {
        "method": next(iter(methods)),
        "model": next(iter(models)),
        "metric": "legacy_spider_execution_accuracy",
        "n": total,
        "correct": correct,
        "ex": correct / total,
        "valid_sql": valid,
        "valid_sql_rate": valid / total,
        "statuses": dict(Counter(r["status"] for r in predictions)),
    }
    metrics = {r.get("metric", "legacy_spider_execution_accuracy") for r in evaluations}
    if len(metrics) != 1:
        raise ValueError("Cannot mix evaluation metrics")
    result["metric"] = next(iter(metrics))
    variants = {r.get("variant", "default") for r in predictions}
    if len(variants) != 1:
        raise ValueError("Cannot mix method variants")
    result["variant"] = next(iter(variants))
    for key in ("latency_ms", "api_calls", "prompt_tokens", "completion_tokens"):
        values = [r[key] for r in predictions if r[key] is not None]
        result[key] = {
            "coverage_n": len(values),
            "total_n": total,
            "cohort": "all terminal rows with observed measurement",
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "observed_sum": sum(values) if values else None,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--evaluation-config", help="Defaults to evaluation file's sibling config")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    evaluation_config = read_json(
        args.evaluation_config or Path(args.evaluation).parent / "evaluation_config.json"
    )
    if evaluation_config["prediction_hash"] != file_hash(args.predictions):
        raise ValueError("Evaluation was produced for different predictions")
    if evaluation_config["input_hash"] != digest(read_jsonl(args.input)):
        raise ValueError("Evaluation input manifest differs")
    result = summarize(
        read_jsonl(args.input), read_jsonl(args.predictions), read_jsonl(args.evaluation)
    )
    result["evaluation_provenance"] = evaluation_config
    write_json(args.output / "metrics.json", result)
    atomic_text(
        args.output / "comparison.md",
        "# Run result\n\n"
        f"Metric: {result['metric']}.\n\n"
        "| Method | N | EX | Valid SQL |\n|---|---:|---:|---:|\n"
        f"| {result['method']} | {result['n']} | {result['correct']}/{result['n']} "
        f"({result['ex']:.1%}) | {result['valid_sql']}/{result['n']} |\n",
    )
    print(f"Summary written to {args.output}")


if __name__ == "__main__":
    main()
