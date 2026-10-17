"""Delegate DAIL linking to its standalone fork."""

import sys

from scripts.common.fork_cli import invoke
from scripts.common.io import ROOT


def main():
    arguments = sys.argv[1:]
    if not any(arg.split("=", 1)[0] == "--dataset" for arg in arguments) and not any(
        arg in {"--help", "-h"} for arg in arguments
    ):
        arguments = ["--dataset", str(ROOT / "data/spider"), *arguments]
    invoke("dail_sql", "reproduction.prepare_assets", arguments)


if __name__ == "__main__":
    main()
