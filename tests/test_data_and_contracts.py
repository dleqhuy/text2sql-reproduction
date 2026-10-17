import pytest

from scripts.common.contracts import failure, validate_inputs, validate_predictions
from scripts.common.io import read_jsonl
from scripts.common.normalization import normalize
from scripts.prepare_spider import prepare, select_indices


def test_prepare_determinism_and_gold_separation(spider_fixture, tmp_path):
    source, _, _ = spider_fixture
    a, b = tmp_path / "a", tmp_path / "b"
    assert prepare(source, a, 2, 1) == prepare(source, b, 2, 1)
    rows = read_jsonl(a / "main.jsonl")
    assert {r["example_id"] for r in read_jsonl(a / "smoke.jsonl")} <= {
        r["example_id"] for r in rows
    }
    assert all(set(row) == {"example_id", "db_id", "question"} for row in rows)
    assert len(read_jsonl(a / "gold.jsonl")) == 2
    with pytest.raises(ValueError, match="overwritten"):
        prepare(source, a, 2, 1)


def test_selection_covers_dbs_and_preserves_indices():
    dev = [{"db_id": db} for db in ("a", "a", "b", "b", "c", "c")]
    ids = select_indices(dev, 3, 42)
    assert len({dev[i]["db_id"] for i in ids}) == 3
    assert ids == sorted(ids)
    with pytest.raises(ValueError):
        select_indices(dev, 7, 42)


def test_alignment_and_missing_rows():
    inputs = [{"example_id": str(i), "db_id": "mini", "question": "Q"} for i in range(2)]
    rows = normalize(inputs, [{"example_id": "1", "pred": "SELECT 1"}], "din_sql", "model", "pred")
    assert rows[0]["status"] == "missing_prediction"
    assert rows[1]["status"] == "ok"
    assert rows[1]["api_calls"] is None
    failed = normalize(
        inputs,
        [{"example_id": "1", "pred": "SELECT 1", "status": "api_error"}],
        "din_sql",
        "model",
        "pred",
    )
    assert failed[1]["status"] == "api_error"
    with pytest.raises(ValueError):
        normalize(inputs, [{"example_id": "2"}], "vanilla", "model")
    with pytest.raises(ValueError):
        validate_inputs([inputs[0], inputs[0]])
    with pytest.raises(ValueError):
        validate_inputs([{**inputs[0], "query": "SELECT gold"}])
    row = failure(inputs[0], "vanilla", "model", "timeout", "Timed out")
    validate_predictions([row], [inputs[0]])
    row["api_calls"] = -1
    with pytest.raises(ValueError):
        validate_predictions([row], [inputs[0]])
