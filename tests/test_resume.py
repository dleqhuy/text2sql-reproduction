import json

import pytest

from scripts.common.contracts import failure
from scripts.common.run_store import RunStore


def test_resume_and_identity_mismatch(tmp_path):
    inputs = [{"example_id": "dev_000000", "db_id": "mini", "question": "Q"}]
    identity = {"model": "a", "input_hash": "x"}
    run = RunStore(tmp_path, identity, inputs)
    run.save(failure(inputs[0], "vanilla", "a", "timeout", "timeout"))
    run.event({"event": "request_sent"})
    run.finish("interrupted")
    run.close()
    with (tmp_path / "events.jsonl").open("a") as stream:
        stream.write('{"broken":')
    resumed = RunStore(tmp_path, identity, inputs, resume=True)
    assert len(resumed.rows) == 1
    assert resumed.request_count == 1
    with pytest.raises(ValueError, match="overwrite"):
        resumed.save(next(iter(resumed.rows.values())))
    resumed.close()
    with pytest.raises(ValueError, match="mismatch"):
        RunStore(tmp_path, {**identity, "model": "b"}, inputs, resume=True)
    for line in (tmp_path / "events.jsonl").read_text().splitlines():
        json.loads(line)


def test_concurrent_writer_rejected(tmp_path):
    inputs = [{"example_id": "x", "db_id": "mini", "question": "Q"}]
    run = RunStore(tmp_path, {}, inputs)
    try:
        with pytest.raises(ValueError, match="already active"):
            RunStore(tmp_path, {}, inputs, resume=True)
    finally:
        run.close()
