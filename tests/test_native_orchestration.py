import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from scripts.common.io import ROOT, read_json, read_jsonl, write_json
from scripts.common.provenance import git_info
from scripts.prepare_spider import prepare


@pytest.mark.parametrize(
    "method,folder,count",
    [
        ("din_sql", "Few-shot-NL2SQL-with-prompting", 4),
        ("mac_sql", "MAC-SQL", 2),
        ("dail_sql", "DAIL-SQL", 1),
    ],
)
def test_parent_launches_native_cli_with_real_http_fixture(
    spider_fixture, tmp_path, method, folder, count
):
    repo = ROOT / "third_party" / folder
    if not (repo / ".venv/bin/python").exists():
        pytest.skip("Install isolated fork environment first")
    source, _, _ = spider_fixture
    prepared = tmp_path / "prepared"
    prepare(source, prepared, 1, 1)
    replies = {
        "din_sql": [
            "Schema_links: [people.id]",
            'Label: "EASY"',
            "SELECT count(*) FROM people",
            "```sql\nSELECT count(*) FROM people\n```",
        ],
        "mac_sql": ["SELECT absent FROM people", "SELECT count(*) FROM people"],
        "dail_sql": ["SELECT count(*) FROM people"],
    }[method]
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            data = json.dumps(
                {
                    "id": "fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "custom-alias",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": replies.pop(0)},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = {
            **os.environ,
            "LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1",
            "LLM_API_KEY": "fixture-secret",
            "LLM_MODEL": "custom-alias",
        }
        command = [
            sys.executable,
            "-m",
            "scripts.run_method",
            "--method",
            method,
            "--input",
            str(prepared / "main.jsonl"),
            "--manifest",
            str(prepared / "manifest.json"),
            "--tables",
            str(prepared / "tables.json"),
            "--db-root",
            str(source / "database"),
            "--run-dir",
            str(tmp_path / "run"),
        ]
        if method == "dail_sql":
            bundle = tmp_path / "prompts.json"
            rows = read_jsonl(prepared / "main.jsonl")
            manifest = read_json(prepared / "manifest.json")
            write_json(
                bundle,
                {
                    "generator": "upstream-dail-prompt-factory-v1",
                    "stage": "preliminary",
                    "upstream": git_info(repo),
                    "asset_hashes": manifest["source_hashes"],
                    "questions": [{**r, "prompt": "fixture prompt"} for r in rows],
                },
            )
            command.extend(["--dail-prompts", str(bundle)])
        result = subprocess.run(
            command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=60
        )
        assert result.returncode == 0, result.stdout + result.stderr
        output = read_jsonl(tmp_path / "run/predictions.jsonl")
        assert output[0]["status"] == "ok", output
        assert output[0]["api_calls"] == count == len(calls)
        assert (
            read_json(tmp_path / "run/run_config.json")["identity"]["orchestrator"]["identity"][
                "method"
            ]
            == method
        )
        result = subprocess.run(
            [*command, "--resume"], cwd=ROOT, env=env, text=True, capture_output=True, timeout=60
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(calls) == count
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
