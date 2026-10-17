"""Delegate DAIL prompt preparation to the pinned standalone fork."""

import sys

from scripts.common.fork_cli import invoke


def main():
    invoke("dail_sql", "reproduction.prepare", sys.argv[1:])


if __name__ == "__main__":
    main()
