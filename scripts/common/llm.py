"""Bounded Chat Completions transport with explicit usage coverage."""

import random
import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


class BudgetExceeded(Exception):
    pass


class ProviderFailure(Exception):
    def __init__(self, kind):
        self.kind = kind
        super().__init__(kind)


class LLM:
    def __init__(self, creds, config, record=None, allowed=None, client=None):
        self.creds, self.config = creds, config
        self.record = record or (lambda event: None)
        self.allowed = allowed or (lambda: True)
        self.client = client or OpenAI(
            api_key=creds.api_key,
            base_url=creds.base_url,
            timeout=config["request_timeout_s"],
            max_retries=0,
        )
        self.reset()

    def reset(self):
        self.calls = 0
        self.usage = []
        self.budget_exhausted = False

    def measurements(self):
        result = {"api_calls": self.calls}
        for key in ("prompt_tokens", "completion_tokens"):
            values = [u.get(key) for u in self.usage]
            result[key] = sum(values) if values and all(v is not None for v in values) else None
        return result

    def complete(self, prompt, stage="generation", max_tokens=None, stop=None):
        params = {
            "model": self.creds.model,
            "messages": [{"role": "user", "content": prompt}],
            self.config["token_parameter"]: max_tokens or self.config["max_output_tokens"],
        }
        if self.config.get("temperature") is not None:
            params["temperature"] = self.config["temperature"]
        if stop:
            params["stop"] = stop
        for attempt in range(1, self.config["max_attempts"] + 1):
            if not self.allowed():
                self.budget_exhausted = True
                raise BudgetExceeded("Run budget exhausted")
            self.calls += 1
            self.record(
                {"event": "request_sent", "stage": stage, "attempt": attempt, "prompt": prompt}
            )
            start = time.monotonic()
            retry_after = None
            try:
                response = self.client.chat.completions.create(**params)
            except (APIConnectionError, APIStatusError) as exc:
                self.usage.append({})
                status = getattr(exc, "status_code", None)
                kind = "timeout" if isinstance(exc, APITimeoutError) else "api_error"
                self.record(
                    {
                        "event": "request_failed",
                        "stage": stage,
                        "attempt": attempt,
                        "status_code": status,
                        "kind": kind,
                        "latency_ms": (time.monotonic() - start) * 1000,
                    }
                )
                transient = status is None or status in {408, 409, 429} or status >= 500
                if not transient or attempt == self.config["max_attempts"]:
                    raise ProviderFailure(kind) from None
                response_obj = getattr(exc, "response", None)
                if response_obj is not None:
                    try:
                        retry_after = float(response_obj.headers.get("retry-after", ""))
                    except ValueError:
                        pass
                delay = self.config["retry_base_s"] * 2 ** (attempt - 1) + random.random()
                time.sleep(min(30, max(delay, retry_after or 0)))
                continue
            usage = response.usage.model_dump() if response.usage else {}
            self.usage.append(usage)
            text = response.choices[0].message.content if response.choices else None
            self.record(
                {
                    "event": "response",
                    "stage": stage,
                    "attempt": attempt,
                    "response": response.model_dump(),
                    "latency_ms": (time.monotonic() - start) * 1000,
                }
            )
            if not isinstance(text, str) or not text.strip():
                raise ProviderFailure("parse_error")
            return text.strip()
        raise ProviderFailure("api_error")
