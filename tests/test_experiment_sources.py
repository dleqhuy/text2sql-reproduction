import json
import subprocess
from types import SimpleNamespace

import pytest

from scripts.bootstrap_upstream import bootstrap
from scripts.common.experiment import capture, validate_run, verify
from scripts.common.io import write_json
from scripts.common.sources import git, gitlink, verify_source


def command(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


def init(root):
    root.mkdir(parents=True)
    command(root, "init")
    command(root, "config", "user.name", "Fixture")
    command(root, "config", "user.email", "fixture@example.invalid")


def commit(root, message):
    command(root, "add", "--all")
    command(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "main"
    init(root)
    source = root / "third_party/fixture"
    init(source)
    (source / "original.py").write_text("# baseline\n")
    base = commit(source, "upstream baseline")
    (source / "reproduction").mkdir()
    (source / "reproduction/method.py").write_text("# adapted entry point\n")
    pinned = commit(source, "fork integration")
    (root / ".gitmodules").write_text(
        '[submodule "third_party/fixture"]\n'
        "    path = third_party/fixture\n"
        "    url = https://example.invalid/fixture.git\n"
    )
    (root / ".gitignore").write_text("data/prepared/\n")
    (root / "scripts").mkdir()
    (root / "scripts/run_method.py").write_text("# runner fixture\n")
    write_json(root / "configs/experiment.json", {"temperature": 0})
    write_json(
        root / "configs/upstream_lock.json",
        {
            "fixture": {
                "directory": "fixture",
                "upstream_url": "https://example.invalid/upstream",
                "upstream_base_commit": base,
                "role": "method",
            }
        },
    )
    (root / "uv.lock").write_text("# dependency fixture\n")
    write_json(root / "data/prepared/manifest.json", {"seed": 42})
    (root / "data/prepared/input.jsonl").write_text('{"example_id":"dev_000000"}\n')
    command(root, "remote", "add", "origin", "https://example.invalid/main.git")
    command(root, "update-index", "--add", "--cacheinfo", f"160000,{pinned},third_party/fixture")
    commit(root, "source tree")
    return root, source


def prepared(root):
    return capture(
        "fixture-smoke",
        "fixture-model",
        root / "configs/experiment.json",
        root / "data/prepared/manifest.json",
        root / "data/prepared/input.jsonl",
        root,
    )


def test_manifest_can_be_committed_after_referenced_source(repository):
    root, source = repository
    manifest = prepared(root)
    write_json(root / "experiments/fixture.json", manifest)
    commit(root, "record prepared experiment")
    assert verify(manifest, root) == manifest
    assert gitlink(source, root) == gitlink(source, root, revision=manifest["root"]["commit"])
    assert "commit" not in json.loads((root / "configs/upstream_lock.json").read_text())["fixture"]


def test_manifest_rejects_changed_data_even_when_ignored(repository):
    root, _ = repository
    manifest = prepared(root)
    (root / "data/prepared/input.jsonl").write_text('{"example_id":"other"}\n')
    with pytest.raises(ValueError, match="Experiment file differs"):
        verify(manifest, root)


def test_manifest_rejects_dirty_and_committed_runtime_changes(repository):
    root, _ = repository
    manifest = prepared(root)
    (root / "scripts/run_method.py").write_text("# different executable\n")
    with pytest.raises(ValueError, match="clean main repository"):
        verify(manifest, root)
    commit(root, "change runner")
    with pytest.raises(ValueError, match="runtime differs"):
        verify(manifest, root)


def test_source_pointer_is_authoritative_and_bootstrap_never_resets(repository):
    root, source = repository
    original_pointer = gitlink(source, root)
    (source / "new.py").write_text("# local method change\n")
    commit(source, "unregistered revision")
    with pytest.raises(ValueError, match="gitlink"):
        bootstrap(["fixture"], root)
    assert git(source, "rev-parse", "HEAD") != original_pointer
    assert gitlink(source, root) == original_pointer


def test_strict_source_rejects_untracked_code(repository):
    root, source = repository
    (source / "untracked_adapter.py").write_text("# not committed\n")
    with pytest.raises(ValueError, match="untracked files"):
        verify_source("fixture", root, strict=True)


def test_run_checks_model_config_and_input(repository):
    root, _ = repository
    manifest = prepared(root)
    path = root / "experiments/fixture.json"
    write_json(path, manifest)
    commit(root, "record manifest")
    args = SimpleNamespace(
        input=root / "data/prepared/input.jsonl", manifest=root / "data/prepared/manifest.json"
    )
    assert (
        validate_run(path, args, "fixture-model", {"temperature": 0}, root)["name"]
        == "fixture-smoke"
    )
    with pytest.raises(ValueError, match="model differs"):
        validate_run(path, args, "other-model", {"temperature": 0}, root)
    with pytest.raises(ValueError, match="configuration differs"):
        validate_run(path, args, "fixture-model", {"temperature": 1}, root)


def test_manifest_rejects_path_escape(repository):
    root, _ = repository
    manifest = prepared(root)
    manifest["files"]["input"]["path"] = "../outside.json"
    with pytest.raises(ValueError, match="escapes"):
        verify(manifest, root)
