# Shared runtime: edit runtime/ in text2sql-reproduction, then run scripts.sync_runtime.
"""Load local secrets without persisting provider credentials."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from dotenv import load_dotenv

from reproduction.io import ROOT, read_json


@dataclass(repr=False, frozen=True)
class Credentials:
    base_url: str
    api_key: str
    model: str


def credentials(env_file=None):
    load_dotenv(env_file or ROOT / ".env", override=False)
    values = {}
    for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        value = os.environ.get(key, "").strip()
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        values[key] = value
    url = urlsplit(values["LLM_BASE_URL"])
    if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
        raise ValueError("LLM_BASE_URL must be an HTTP(S) URL without embedded credentials")
    return Credentials(values["LLM_BASE_URL"], values["LLM_API_KEY"], values["LLM_MODEL"])


def load_config(path=None):
    result = read_json(path or ROOT / "reproduction/config.json")
    for name in (
        "request_timeout_s",
        "max_attempts",
        "max_output_tokens",
        "max_run_calls",
        "max_run_seconds",
        "sql_timeout_s",
    ):
        value = result.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{name} must be positive")
    if not isinstance(result["max_attempts"], int):
        raise ValueError("max_attempts must be an integer")
    if result.get("token_parameter") not in {"max_tokens", "max_completion_tokens"}:
        raise ValueError("Unsupported token_parameter")
    if result.get("retry_base_s", -1) < 0:
        raise ValueError("retry_base_s must be nonnegative")
    if set(result) & {"api_key", "base_url", "LLM_API_KEY", "LLM_BASE_URL"}:
        raise ValueError("Keep credentials and endpoint in env, not experiment config")
    return result
