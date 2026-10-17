"""Small real probe, never print credentials, endpoint or HTTP error bodies."""

import argparse

from scripts.common.config import credentials, load_config
from scripts.common.io import write_json
from scripts.common.llm import LLM, ProviderFailure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--output", default="runs/provider_probe.json")
    args = parser.parse_args()
    config, creds = load_config(args.config), credentials()
    llm = LLM(creds, config)
    try:
        text = llm.complete("Return only the word OK.", stage="probe", max_tokens=16)
    except ProviderFailure as exc:
        print(f"Provider probe failed: {exc.kind}; check local configuration.")
        raise SystemExit(1) from None
    result = {
        "api": "chat.completions",
        "model": creds.model,
        "nonempty_text": bool(text),
        "token_parameter": config["token_parameter"],
        "temperature": config.get("temperature"),
        **llm.measurements(),
    }
    write_json(args.output, result)
    print(f"Chat Completions probe passed. Profile saved to {args.output}")


if __name__ == "__main__":
    main()
