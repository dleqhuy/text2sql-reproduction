import pytest

from scripts import aggregate_dail
from scripts.aggregate_dail import aggregate
from scripts.common.contracts import failure
from scripts.common.io import write_json


def test_two_stage_usage_and_failure_denominator():
    inputs = [{"example_id": "x", "db_id": "mini", "question": "Q"}]
    a = failure(inputs[0], "dail_sql", "model", "api_error", "transport")
    a.update(api_calls=2, latency_ms=100, prompt_tokens=None, completion_tokens=None)
    a["variant"] = "preliminary"
    b = {
        **a,
        "status": "ok",
        "predicted_sql": "SELECT 1",
        "error": None,
        "api_calls": 1,
        "latency_ms": 50,
        "prompt_tokens": 20,
        "completion_tokens": 3,
    }
    b["variant"] = "final"
    result = aggregate(inputs, [a], [b])[0]
    assert result["status"] == "api_error" and result["predicted_sql"] is None
    assert result["api_calls"] == 3 and result["latency_ms"] == 150
    assert result["prompt_tokens"] is None
    with pytest.raises(ValueError):
        aggregate(inputs, [a], [{**b, "model": "other"}])


def test_aggregate_rejects_mixed_experiment_manifests(tmp_path, monkeypatch):
    first, final = tmp_path / "first", tmp_path / "final"
    write_json(first / "run_config.json", {"identity": {"experiment": {"sha256": "a"}}})
    write_json(final / "run_config.json", {"identity": {"experiment": {"sha256": "b"}}})
    monkeypatch.setattr(
        "sys.argv",
        [
            "aggregate_dail",
            "--input",
            "unused.jsonl",
            "--preliminary-run",
            str(first),
            "--final-run",
            str(final),
            "--output",
            str(tmp_path / "aggregate"),
        ],
    )
    with pytest.raises(ValueError, match="config mismatch: experiment"):
        aggregate_dail.main()
