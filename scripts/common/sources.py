"""Submodule gitlinks are the only authority for executable source revisions."""

import importlib.util
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from scripts.common.io import ROOT, read_json
from scripts.common.provenance import git_info


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def source_path(name, root=ROOT):
    metadata = read_json(root / "configs/upstream_lock.json")[name]
    return root / "third_party" / metadata["directory"]


def gitlink(path, root=ROOT, revision=None):
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    if revision:
        output = git(root, "ls-tree", revision, "--", relative)
    else:
        output = git(root, "ls-files", "--stage", "--", relative)
    rows = output.splitlines()
    if len(rows) != 1 or not rows[0].startswith("160000 "):
        raise ValueError(f"Missing submodule gitlink: {relative}")
    fields = rows[0].split()
    if not revision and fields[2] != "0":
        raise ValueError(f"Unmerged submodule gitlink: {relative}")
    return fields[2] if revision else fields[1]


def source_url(path, root=ROOT):
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    return git(root, "config", "-f", ".gitmodules", "--get", f"submodule.{relative}.url")


def verify_source(name, root=ROOT, path=None, strict=False):
    expected_path = source_path(name, root)
    path = Path(path or expected_path).resolve()
    if not path.exists() or Path(git(path, "rev-parse", "--show-toplevel")) != path:
        raise ValueError(f"Submodule is not initialized: {name}")
    info = git_info(path)
    if info["commit"] != gitlink(expected_path, root) or info["dirty"]:
        raise ValueError(f"{name}: checkout differs from its pinned clean gitlink")
    if strict:
        untracked = git(path, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
        unexpected = [
            p
            for p in untracked
            if p and "__pycache__" not in Path(p).parts and Path(p).suffix not in {".pyc", ".pyo"}
        ]
        if unexpected:
            raise ValueError(f"{name}: uncommitted or untracked files")
    metadata = read_json(root / "configs/upstream_lock.json")[name]
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "merge-base",
            "--is-ancestor",
            metadata["upstream_base_commit"],
            info["commit"],
        ],
        check=True,
        capture_output=True,
    )
    return info


@lru_cache
def load_integration(name, filename="reproduction_adapter.py", repo=None):
    """Load a fork entry point without importing its legacy CLI entry point."""
    path = Path(repo) if repo else source_path(name)
    module_name = f"text2sql_fork_{name}_{Path(filename).stem}"
    spec = importlib.util.spec_from_file_location(module_name, path / filename)
    if spec is None or spec.loader is None:
        raise ImportError(f"No integration entry point for {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module
