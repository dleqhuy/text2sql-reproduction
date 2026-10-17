# Shared runtime: edit runtime/ in text2sql-reproduction, then run scripts.sync_runtime.
"""Atomic per-question checkpoints and single-writer run ownership."""

import fcntl
import json
from datetime import datetime, timezone
from pathlib import Path

from reproduction.io import atomic_text, digest, read_json, write_json, write_jsonl


class RunStore:
    def __init__(self, path, identity, inputs, resume=False):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.lock = (self.path / ".lock").open("w")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise ValueError("Run is already active") from None
        try:
            self._initialize(identity, inputs, resume)
        except BaseException:
            self.close()
            raise

    def _initialize(self, identity, inputs, resume):
        self.inputs = inputs
        self.rows = {}
        self.current_id = None
        self.request_count = 0
        self.meta_path = self.path / "run_config.json"
        if self.meta_path.exists():
            if not resume:
                raise ValueError("Run already exists; use --resume or a new directory")
            self.meta = read_json(self.meta_path)
            if self.meta["identity_hash"] != digest(identity):
                raise ValueError("Resume identity mismatch (code/config/model/data)")
            for path in (self.path / "checkpoints").glob("*.json"):
                row = read_json(path)
                if row["example_id"] in self.rows:
                    raise ValueError("Duplicate checkpoint")
                self.rows[row["example_id"]] = row
            self._recover_events()
        else:
            if resume:
                raise ValueError("Cannot resume a run without metadata")
            self.meta = {
                "identity": identity,
                "identity_hash": digest(identity),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "running",
            }
            write_json(self.path / "input_manifest.json", inputs)
        self.meta["status"] = "running"
        write_json(self.meta_path, self.meta)

    def _recover_events(self):
        path = self.path / "events.jsonl"
        if not path.exists():
            return
        lines = path.read_text().splitlines(keepends=True)
        valid = []
        damaged = False
        for index, line in enumerate(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if index != len(lines) - 1:
                    raise ValueError("Corrupt event log before final line") from None
                damaged = True
                break
            self.request_count += event.get("event") == "request_sent"
            valid.append(json.dumps(event) + "\n")
        atomic_text(path, "".join(valid))
        if damaged:
            self.event({"event": "recovered_partial_last_event"})

    def event(self, event):
        event = {
            "at": datetime.now(timezone.utc).isoformat(),
            "example_id": self.current_id,
            **event,
        }
        with (self.path / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()
        self.request_count += event.get("event") == "request_sent"

    def save(self, row):
        eid = row["example_id"]
        if eid in self.rows:
            raise ValueError("Cannot overwrite terminal prediction")
        # Hash filenames so externally supplied IDs cannot escape checkpoints/.
        write_json(self.path / "checkpoints" / f"{digest(eid)}.json", row)
        self.rows[eid] = row
        self.flush()

    def flush(self):
        write_jsonl(
            self.path / "predictions.jsonl",
            [self.rows[r["example_id"]] for r in self.inputs if r["example_id"] in self.rows],
        )

    def finish(self, status):
        self.meta["status"] = status
        self.meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(self.meta_path, self.meta)
        self.flush()

    def close(self):
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()
