"""Immutable experiment references; no source snapshots or credentials."""

import subprocess
from pathlib import Path

from scripts.common.io import ROOT, digest, file_hash, read_json
from scripts.common.sources import git, gitlink, source_path, source_url, verify_source

RUNTIME_PATHS = ("scripts", "runtime", "configs", "pyproject.toml", "uv.lock", ".gitmodules")


def clean_repository(root):
    # Submodule untracked files are checked separately by verify_source.
    if git(
        root, "status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=untracked"
    ):
        raise ValueError("Experiment requires a clean main repository; commit changes first")


def runtime_hash(root, revision=None):
    revision = revision or "HEAD"
    paths = git(root, "ls-tree", "-r", "--name-only", revision, "--", *RUNTIME_PATHS).splitlines()
    if not paths or "scripts/run_method.py" not in paths:
        raise ValueError("Experiment revision does not contain the runner")
    if revision != "HEAD":
        import hashlib

        hashes = {
            p: hashlib.sha256(
                subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{p}"])
            ).hexdigest()
            for p in paths
        }
    else:
        hashes = {p: file_hash(root / p) for p in paths}
    return digest(hashes)


def reference(path, root):
    path = Path(path).resolve()
    relative = path.relative_to(Path(root).resolve()).as_posix()
    if ".env" in path.name or not path.is_file():
        raise ValueError("Experiment references must be existing non-secret files")
    return {"path": relative, "sha256": file_hash(path)}


def referenced_path(ref, root):
    path = (Path(root) / ref["path"]).resolve()
    if not path.is_relative_to(Path(root).resolve()) or Path(ref["path"]).is_absolute():
        raise ValueError("Experiment reference escapes the repository")
    return path


def capture(name, model, config, dataset_manifest, inputs, root=ROOT):
    root = Path(root).resolve()
    clean_repository(root)
    sources = {}
    for key, metadata in read_json(root / "configs/upstream_lock.json").items():
        info = verify_source(key, root, strict=True)
        path = source_path(key, root)
        if info["commit"] != gitlink(path, root, revision="HEAD"):
            raise ValueError("Commit the submodule pointer before capturing an experiment")
        sources[key] = {
            "path": path.relative_to(root).as_posix(),
            "url": source_url(path, root),
            "commit": info["commit"],
            "upstream_url": metadata["upstream_url"],
            "upstream_base_commit": metadata["upstream_base_commit"],
        }
    return {
        "schema_version": 1,
        "name": name,
        "state": "prepared",
        "model": model,
        "root": {
            "repository": git(root, "remote", "get-url", "origin"),
            "commit": git(root, "rev-parse", "HEAD"),
            "runtime_hash": runtime_hash(root),
        },
        "sources": sources,
        "files": {
            "config": reference(config, root),
            "dataset_manifest": reference(dataset_manifest, root),
            "input": reference(inputs, root),
            "dependencies": reference(root / "uv.lock", root),
        },
        "evaluation": {
            "metric": "test_suite_execution_accuracy",
            "plug_value": False,
            "keep_distinct": True,
            "seed": 42,
        },
        "notes": "Prepared configuration, not a claim that inference has run. No source snapshot included.",
    }


def verify(manifest, root=ROOT):
    root = Path(root).resolve()
    if manifest.get("schema_version") != 1 or manifest.get("state") != "prepared":
        raise ValueError("Unsupported experiment manifest")
    if set(manifest.get("files", {})) != {"config", "dataset_manifest", "input", "dependencies"}:
        raise ValueError("Incomplete experiment file references")
    clean_repository(root)
    pinned = manifest["root"]
    if git(root, "remote", "get-url", "origin") != pinned["repository"]:
        raise ValueError("Experiment main repository URL differs")
    subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", pinned["commit"], "HEAD"],
        check=True,
        capture_output=True,
    )
    # A later commit may add the manifest/docs, but executable code/config must match.
    if (
        runtime_hash(root) != pinned["runtime_hash"]
        or runtime_hash(root, pinned["commit"]) != pinned["runtime_hash"]
    ):
        raise ValueError("Experiment runtime differs from its recorded source revision")
    metadata = read_json(root / "configs/upstream_lock.json")
    if set(manifest["sources"]) != set(metadata):
        raise ValueError("Experiment source set differs")
    for key, source in manifest["sources"].items():
        path = source_path(key, root)
        info = verify_source(key, root, strict=True)
        if (
            info["commit"] != source["commit"]
            or gitlink(path, root, revision=pinned["commit"]) != source["commit"]
            or source_url(path, root) != source["url"]
            or path.relative_to(root).as_posix() != source["path"]
            or metadata[key]["upstream_base_commit"] != source["upstream_base_commit"]
            or metadata[key]["upstream_url"] != source["upstream_url"]
        ):
            raise ValueError(f"Experiment source differs: {key}")
    for ref in manifest["files"].values():
        if file_hash(referenced_path(ref, root)) != ref["sha256"]:
            raise ValueError(f"Experiment file differs: {ref['path']}")
    if manifest["evaluation"] != {
        "metric": "test_suite_execution_accuracy",
        "plug_value": False,
        "keep_distinct": True,
        "seed": 42,
    }:
        raise ValueError("Unsupported evaluation configuration")
    return manifest


def validate_run(path, args, model, config, root=ROOT):
    manifest = verify(read_json(path), root)
    if manifest["model"] != model:
        raise ValueError("Experiment model differs from configured provider model")
    for key, actual in (("input", args.input), ("dataset_manifest", args.manifest)):
        if file_hash(actual) != manifest["files"][key]["sha256"]:
            raise ValueError(f"Run differs from experiment: {key}")
    if read_json(referenced_path(manifest["files"]["config"], root)) != config:
        raise ValueError("Run configuration differs from experiment")
    return {
        "sha256": file_hash(path),
        "name": manifest["name"],
        "root_commit": manifest["root"]["commit"],
    }
