"""Create or verify immutable experiment references from a clean committed checkout."""

import argparse
import json
from pathlib import Path

from scripts.common.config import credentials
from scripts.common.experiment import capture, verify
from scripts.common.io import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--model", help="Defaults to LLM_MODEL; credentials are never stored")
    create.add_argument("--config", default="configs/experiment.json")
    create.add_argument("--manifest", required=True, help="Prepared dataset manifest")
    create.add_argument("--input", required=True)
    create.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        result = verify(read_json(args.path))
        print(
            f"Verified experiment {result['name']}: source, configuration, and data references match"
        )
        return
    result = capture(
        args.name, args.model or credentials().model, args.config, args.manifest, args.input
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create: never replace an experiment's recorded references.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(f"Created prepared experiment {args.output}; no inference was run")


if __name__ == "__main__":
    main()
