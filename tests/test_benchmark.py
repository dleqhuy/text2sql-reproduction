import subprocess

import pytest

from scripts.common.benchmark_pipeline import execute
from scripts.common.benchmark_plan import Stage, plan
from scripts.common.benchmark_report import report
from scripts.common.contracts import failure
from scripts.common.io import ROOT, digest, file_hash, read_json, write_json, write_jsonl
from scripts.summarize_results import summarize


def test_resume_preserves_completed_requests_and_rejects_changed_artifacts(tmp_path):
    output = tmp_path / "benchmark"
    stages = [
        Stage(name, "scripts.run_method", ["--run-dir", output / name], [output / name])
        for name in ("vanilla", "din")
    ]
    calls = []

    def interrupted(command, **kwargs):
        calls.append(command)
        folder = command[command.index("--run-dir") + 1]
        write_json(f"{folder}/run_config.json", {"status": "running"})
        if str(folder).endswith("din"):
            raise subprocess.CalledProcessError(1, command)
        write_jsonl(f"{folder}/predictions.jsonl", [{"sql": "SELECT 1"}])

    with pytest.raises(subprocess.CalledProcessError):
        execute(stages, output, {"model": "fixture"}, tmp_path / "manifest", invoke=interrupted)
    assert read_json(output / "benchmark.json")["status"] == "interrupted"

    def continued(command, **kwargs):
        assert "--resume" in command
        calls.append(command)
        folder = command[command.index("--run-dir") + 1]
        write_json(f"{folder}/run_config.json", {"status": "completed"})
        write_jsonl(f"{folder}/predictions.jsonl", [{"sql": "SELECT 2"}])

    execute(
        stages, output, {"model": "fixture"}, tmp_path / "manifest", resume=True, invoke=continued
    )
    assert len(calls) == 3  # Completed Vanilla was not called again.
    with pytest.raises(ValueError, match="directory exists"):
        execute(stages, output, {}, tmp_path / "manifest", invoke=continued)
    with pytest.raises(ValueError, match="identity mismatch"):
        execute(
            stages,
            output,
            {"model": "different"},
            tmp_path / "manifest",
            resume=True,
            invoke=continued,
        )
    write_jsonl(output / "vanilla/predictions.jsonl", [{"sql": "tampered"}])
    with pytest.raises(ValueError, match="artifacts changed"):
        execute(
            stages,
            output,
            {"model": "fixture"},
            tmp_path / "manifest",
            resume=True,
            invoke=continued,
        )
    assert len(calls) == 3


def test_plan_orders_dail_dependencies_and_covers_both_metrics(tmp_path):
    experiment = read_json(ROOT / "experiments/manifests/native-main-100-20261017.json")
    stages = plan(
        experiment,
        tmp_path,
        ROOT / "data/spider",
        ROOT / "data/test-suite",
        ROOT / "configs/dail_embedding.json",
    )
    names = [s.name for s in stages]
    assert names.index("prepare-preliminary") < names.index("vanilla")
    assert names.index("dail-preliminary") < names.index("prepare-final")
    assert names.index("prepare-final") < names.index("dail-final") < names.index("dail")
    assert names.index("dail") < names.index("vanilla-test-suite")
    for folder in ("vanilla", "din", "mac", "dail"):
        for metric in ("test-suite", "execution"):
            assert f"{folder}-{metric}-summary" in names


def test_report_uses_full_denominator_and_rejects_stale_predictions(tmp_path):
    inputs = [{"example_id": "dev_000000", "db_id": "mini", "question": "Count people"}]
    for method, folder in [
        ("vanilla", "vanilla"),
        ("dail_sql", "dail"),
        ("din_sql", "din"),
        ("mac_sql", "mac"),
    ]:
        prediction = failure(inputs[0], method, "fixture", "parse_error", "fixture")
        prediction.update(latency_ms=10, api_calls=1, prompt_tokens=3, completion_tokens=1)
        predictions = tmp_path / folder / "predictions.jsonl"
        write_jsonl(predictions, [prediction])
        for metric, name in [
            ("test-suite", "test_suite_execution_accuracy"),
            ("execution", "single_database_execution_accuracy"),
        ]:
            evaluation = {
                "example_id": inputs[0]["example_id"],
                "db_id": "mini",
                "prediction_status": "parse_error",
                "execution_status": "not_run",
                "correct": False,
                "metric": name,
            }
            metrics = summarize(inputs, [prediction], [evaluation])
            metrics["evaluation_provenance"] = {
                "input_hash": digest(inputs),
                "prediction_hash": file_hash(predictions),
            }
            write_json(tmp_path / folder / f"eval-{metric}/metrics.json", metrics)
    report(tmp_path, inputs, "fixture-manifest-hash")
    comparison = read_json(tmp_path / "comparison.json")
    assert len(comparison["results"]) == 4
    assert all(
        r["test_suite"]["n"] == 1 and r["test_suite"]["ex"] == 0 for r in comparison["results"]
    )
    assert "N=1" in (tmp_path / "report.md").read_text()
    write_jsonl(tmp_path / "vanilla/predictions.jsonl", [{"changed": True}])
    with pytest.raises(ValueError, match="do not match"):
        report(tmp_path, inputs, "fixture-manifest-hash")
