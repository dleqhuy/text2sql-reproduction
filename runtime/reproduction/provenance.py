# Shared runtime: edit runtime/ in text2sql-reproduction, then run scripts.sync_runtime.
"""Fingerprint code, not local credentials or downloaded databases."""

import subprocess
from importlib.metadata import distributions

from reproduction.io import ROOT, digest, file_hash


def git_info(path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "diff_hash": digest(git("diff", "HEAD")),
    }


def code_provenance():
    names = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "*.py",
        ],
        text=True,
    ).split("\0")
    files = sorted(ROOT / name for name in names if name and (ROOT / name).is_file())
    if (ROOT / "uv.lock").exists():
        files.append(ROOT / "uv.lock")
    return {
        "root": git_info(ROOT),
        "code_hash": digest({str(p.relative_to(ROOT)): file_hash(p) for p in files}),
        "dependencies": {dist.metadata["Name"]: dist.version for dist in distributions()},
    }
