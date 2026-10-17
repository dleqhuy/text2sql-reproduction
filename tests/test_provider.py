import httpx
import pytest
from openai import OpenAI

from scripts.common.config import Credentials, credentials, load_config
from scripts.common.llm import LLM, BudgetExceeded, ProviderFailure


def fake_llm(responses, config=None, allowed=None):
    events = []

    def handler(request):
        status, body = responses.pop(0)
        return httpx.Response(status, json=body)

    client = OpenAI(
        api_key="test-secret",
        base_url="https://fixture.invalid/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    llm = LLM(
        Credentials("https://fixture.invalid/v1", "test-secret", "test-model"),
        config or load_config(),
        events.append,
        allowed,
        client,
    )
    return llm, events


def reply(usage=True):
    result = {
        "id": "fixture",
        "model": "test-model",
        "object": "chat.completion",
        "created": 1,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "SELECT 1"},
                "finish_reason": "stop",
            }
        ],
    }
    if usage:
        result["usage"] = {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}
    return result


def test_success_and_unknown_usage():
    llm, events = fake_llm([(200, reply(False))])
    assert llm.complete("Q") == "SELECT 1"
    assert llm.measurements() == {"api_calls": 1, "prompt_tokens": None, "completion_tokens": None}
    assert events[0]["event"] == "request_sent"
    assert "test-secret" not in str(events)


def test_retry_count_and_coverage(monkeypatch):
    monkeypatch.setattr("scripts.common.llm.time.sleep", lambda _: None)
    llm, _ = fake_llm([(429, {"error": {"message": "limited"}}), (200, reply())])
    assert llm.complete("Q") == "SELECT 1"
    assert llm.calls == 2
    assert llm.measurements()["prompt_tokens"] is None


def test_auth_not_retried_or_logged():
    llm, events = fake_llm([(401, {"error": {"message": "secret-key-in-error"}})])
    with pytest.raises(ProviderFailure):
        llm.complete("Q")
    assert llm.calls == 1
    assert "secret-key-in-error" not in str(events)


def test_budget_prevents_requests():
    llm, _ = fake_llm([], allowed=lambda: False)
    with pytest.raises(BudgetExceeded):
        llm.complete("Q")
    assert llm.calls == 0


def test_missing_env_names_only(monkeypatch):
    monkeypatch.setattr("scripts.common.config.load_dotenv", lambda *a, **k: None)
    for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        credentials()
    assert not hasattr(Credentials("a", "b", "c"), "__repr_secret__")
