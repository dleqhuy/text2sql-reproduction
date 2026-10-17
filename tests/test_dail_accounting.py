import pytest

from scripts.aggregate_dail import aggregate
from scripts.common.contracts import failure


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
