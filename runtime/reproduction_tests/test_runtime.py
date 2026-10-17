"""Offline transport and real standalone-CLI tests; no external provider calls."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import OpenAI
from reproduction.config import Credentials, load_config
from reproduction.io import ROOT, write_json, write_jsonl
from reproduction.llm import LLM, ProviderFailure
from reproduction.method import METHOD
from reproduction.provenance import git_info


def response(text):
    return {
        "id": "fixture",
        "object": "chat.completion",
        "created": 1,
        "model": "custom-alias",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
    }


class RuntimeTests(unittest.TestCase):
    def test_bounded_retry_auth_and_usage(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(
                429 if len(requests) == 1 else 200,
                json={"error": {"message": "retry"}}
                if len(requests) == 1
                else response("SELECT 1"),
            )

        client = OpenAI(
            api_key="fixture-secret",
            base_url="https://fixture.invalid",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handle)),
        )
        events = []
        llm = LLM(
            Credentials("https://fixture.invalid", "fixture-secret", "custom-alias"),
            load_config(),
            events.append,
            client=client,
        )
        with patch("reproduction.llm.time.sleep"):
            self.assertEqual(llm.complete("fixture"), "SELECT 1")
        self.assertEqual(llm.calls, 2)
        self.assertIsNone(llm.measurements()["prompt_tokens"])
        self.assertNotIn("fixture-secret", json.dumps(events))
        client.close()
        requests.clear()

        def denied(request):
            requests.append(request)
            return httpx.Response(401, json={"error": {"message": "denied"}})

        client = OpenAI(
            api_key="fixture-secret",
            base_url="https://fixture.invalid",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(denied)),
        )
        llm = LLM(
            Credentials("https://fixture.invalid", "fixture-secret", "custom-alias"),
            load_config(),
            client=client,
        )
        with self.assertRaises(ProviderFailure):
            llm.complete("fixture")
        self.assertEqual(len(requests), 1)
        client.close()

    def test_standalone_cli_and_resume(self):
        branches = ["EASY", "NON-NESTED", "NESTED"] if METHOD == "din_sql" else [None]
        for branch in branches:
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as folder:
                tmp = Path(folder)
                database = tmp / "database/mini/mini.sqlite"
                database.parent.mkdir(parents=True)
                with sqlite3.connect(database) as conn:
                    conn.executescript(
                        "CREATE TABLE people(id INTEGER PRIMARY KEY,name TEXT); INSERT INTO people VALUES (1,'An'),(2,'Binh');"
                    )
                write_json(
                    tmp / "tables.json",
                    [
                        {
                            "db_id": "mini",
                            "table_names_original": ["people"],
                            "table_names": ["people"],
                            "column_names_original": [[-1, "*"], [0, "id"], [0, "name"]],
                            "column_names": [[-1, "*"], [0, "id"], [0, "name"]],
                            "column_types": ["text", "number", "text"],
                            "primary_keys": [1],
                            "foreign_keys": [],
                        }
                    ],
                )
                inputs = [
                    {"example_id": "dev_000000", "db_id": "mini", "question": "How many people?"}
                ]
                write_jsonl(tmp / "input.jsonl", inputs)
                replies = (
                    [
                        "Schema_links: [people.id]",
                        f'Label: "{branch}" questions = ["count people"]',
                        "SELECT count(*) FROM people"
                        if branch == "EASY"
                        else "SQL: SELECT count(*) FROM people",
                        "```sql\nSELECT count(*) FROM people\n```",
                    ]
                    if METHOD == "din_sql"
                    else ["SELECT absent FROM people", "```sql\nSELECT count(*) FROM people\n```"]
                    if METHOD == "mac_sql"
                    else ["SELECT count(*) FROM people"]
                )
                calls = []

                class Handler(BaseHTTPRequestHandler):
                    def do_POST(self):
                        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                        calls.append(request)
                        body = json.dumps(response(replies.pop(0))).encode()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)

                    def log_message(self, *args):
                        pass

                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    env = {
                        k: v
                        for k, v in os.environ.items()
                        if k not in {"PYTHONPATH", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"}
                    }
                    (tmp / "provider.env").write_text(
                        f"LLM_BASE_URL=http://127.0.0.1:{server.server_port}/v1\nLLM_API_KEY=fixture-secret\nLLM_MODEL=custom-alias\n"
                    )
                    command = [
                        sys.executable,
                        "-m",
                        "reproduction.run",
                        "--input",
                        str(tmp / "input.jsonl"),
                        "--tables",
                        str(tmp / "tables.json"),
                        "--db-root",
                        str(tmp / "database"),
                        "--run-dir",
                        str(tmp / "run"),
                        "--env-file",
                        str(tmp / "provider.env"),
                    ]
                    if METHOD == "dail_sql":
                        write_json(
                            tmp / "prompts.json",
                            {
                                "generator": "upstream-dail-prompt-factory-v1",
                                "stage": "preliminary",
                                "upstream": git_info(ROOT),
                                "questions": [{**inputs[0], "prompt": "fixture prompt"}],
                            },
                        )
                        command += ["--dail-prompts", str(tmp / "prompts.json")]
                    result = subprocess.run(
                        command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=60
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    rows = [
                        json.loads(line)
                        for line in (tmp / "run/predictions.jsonl").read_text().splitlines()
                    ]
                    self.assertEqual(rows[0]["status"], "ok", rows)
                    self.assertEqual(
                        rows[0]["predicted_sql"].strip().upper(), "SELECT COUNT(*) FROM PEOPLE"
                    )
                    self.assertEqual(
                        rows[0]["api_calls"],
                        4 if METHOD == "din_sql" else 2 if METHOD == "mac_sql" else 1,
                    )
                    self.assertTrue(all(c["model"] == "custom-alias" for c in calls))
                    self.assertTrue(
                        all("private_dev_gold_marker" not in json.dumps(c) for c in calls)
                    )
                    before = (tmp / "run/predictions.jsonl").read_bytes()
                    count = len(calls)
                    result = subprocess.run(
                        command + ["--resume"],
                        cwd=ROOT,
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(len(calls), count)
                    self.assertEqual((tmp / "run/predictions.jsonl").read_bytes(), before)
                    for p in (tmp / "run").rglob("*"):
                        if p.is_file():
                            self.assertNotIn("fixture-secret", p.read_text())
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()


if __name__ == "__main__":
    unittest.main()
