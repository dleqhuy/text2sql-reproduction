"""Fingerprint code, not local credentials or downloaded databases."""

import subprocess
from importlib.metadata import distributions

from scripts.common.io import ROOT, digest, file_hash


def git_info(path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "diff_hash": digest(git("diff", "HEAD")),
    }


def code_provenance():
    files = [*sorted((ROOT / "scripts").rglob("*.py")), ROOT / "pyproject.toml"]
    files.extend(sorted((ROOT / "runtime").rglob("*.py")))
    files.extend(sorted((ROOT / "runtime").rglob("*.json")))
    if (ROOT / "uv.lock").exists():
        files.append(ROOT / "uv.lock")
    return {
        "root": git_info(ROOT),
        "code_hash": digest({str(p.relative_to(ROOT)): file_hash(p) for p in files}),
        "dependencies": {dist.metadata["Name"]: dist.version for dist in distributions()},
    }
