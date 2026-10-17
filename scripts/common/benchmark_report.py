"""Build a report from verified prediction and evaluation artifacts."""

from scripts.common.io import atomic_text, digest, file_hash, read_json, write_json


def report(output, inputs, experiment_hash):
    results = []
    for method, folder in [
        ("Vanilla", "vanilla"),
        ("DAIL-SQL", "dail"),
        ("DIN-SQL", "din"),
        ("MAC-SQL", "mac"),
    ]:
        run = output / folder
        metrics = [read_json(run / f"eval-{m}/metrics.json") for m in ("test-suite", "execution")]
        for metric, expected in zip(
            metrics,
            ["test_suite_execution_accuracy", "single_database_execution_accuracy"],
            strict=True,
        ):
            provenance = metric["evaluation_provenance"]
            if (
                metric["metric"] != expected
                or metric["method"] != ("vanilla" if folder == "vanilla" else f"{folder}_sql")
                or metric["n"] != len(inputs)
                or provenance["input_hash"] != digest(inputs)
                or provenance["prediction_hash"] != file_hash(run / "predictions.jsonl")
            ):
                raise ValueError("Benchmark metrics do not match predictions/input/metric")
        results.append(
            {"method": method, "run": str(run), "test_suite": metrics[0], "execution": metrics[1]}
        )
    if len({m["model"] for r in results for m in (r["test_suite"], r["execution"])}) != 1:
        raise ValueError("Benchmark methods use different models")
    write_json(
        output / "comparison.json",
        {"experiment_hash": experiment_hash, "input_hash": digest(inputs), "results": results},
    )
    lines = [
        "# Benchmark",
        "",
        f"Model: `{results[0]['test_suite']['model']}`; N={len(inputs)}.",
        "",
        "| Method | Test Suite | DB gốc | SQL valid | Requests |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        m, ex = result["test_suite"], result["execution"]
        lines.append(
            f"| {result['method']} | {m['ex']:.1%} | {ex['ex']:.1%} | "
            f"{m['valid_sql']}/{m['n']} | {m['api_calls']['observed_sum']} |"
        )
    lines += [
        "",
        "Inference chạy tuần tự; DAIL cộng hai lượt, chưa gồm retrieval offline. "
        "Mẫu số gồm cả failures. Token usage/coverage, latency và statuses ở "
        "[comparison.json](comparison.json); stage hashes ở [benchmark.json](benchmark.json).",
        "",
        "Đây là adapted reproduction trên subset; smoke nằm trong main và đã dùng "
        "để sửa output handling. Kết quả không phải full Spider dev hoặc điểm paper gốc.",
        "",
    ]
    atomic_text(output / "report.md", "\n".join(lines))
