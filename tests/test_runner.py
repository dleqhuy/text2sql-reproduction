import json
from types import SimpleNamespace

import httpx
from openai import OpenAI

from scripts import run_method
from scripts.common.config import Credentials, load_config
from scripts.common.io import read_json, read_jsonl
from scripts.common.llm import LLM
from scripts.prepare_spider import prepare


def test_runner_budget_resume_and_provenance(spider_fixture, tmp_path, monkeypatch):
    source, _, _ = spider_fixture
    prepared = tmp_path / "prepared"
    prepare(source, prepared, 2, 1)
    config = load_config()
    config["max_run_calls"] = 1
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config))
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(
            200,
            json={
                "id": "test",
                "created": 1,
                "model": "fixture",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "SELECT count(*) FROM people"},
                    }
                ],
            },
        )

    client = OpenAI(
        api_key="do-not-log",
        base_url="https://fixture.invalid",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        run_method,
        "credentials",
        lambda: Credentials("https://fixture.invalid", "do-not-log", "fixture"),
    )
    monkeypatch.setattr(
        run_method,
        "LLM",
        lambda creds, config, record, allowed: LLM(creds, config, record, allowed, client),
    )
    args = SimpleNamespace(
        config=cfg,
        input=prepared / "main.jsonl",
        manifest=prepared / "manifest.json",
        tables=prepared / "tables.json",
        db_root=source / "database",
        method="vanilla",
        run_dir=tmp_path / "run",
        resume=False,
        dail_prompts=None,
    )
    run_method.run(args)
    rows = read_jsonl(args.run_dir / "predictions.jsonl")
    assert [r["status"] for r in rows] == ["ok", "budget_exceeded"]
    assert len(sent) == 1
    assert read_json(args.run_dir / "run_config.json")["status"] == "completed"
    args.resume = True
    run_method.run(args)
    assert len(sent) == 1
    assert read_jsonl(args.run_dir / "predictions.jsonl") == rows
    for path in args.run_dir.rglob("*"):
        if path.is_file():
            assert "do-not-log" not in path.read_text()
