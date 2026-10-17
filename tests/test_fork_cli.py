import re
from pathlib import Path
from types import SimpleNamespace

from scripts.common import fork_cli
from scripts.common.io import ROOT


def test_invocation_uses_fork_working_directory_and_absolute_paths(monkeypatch, tmp_path):
    repo = tmp_path / "fork"
    repo.mkdir()
    observed = []
    monkeypatch.setattr(fork_cli, "source_path", lambda name: repo)
    monkeypatch.setenv("PYTHONPATH", "parent-only-path")
    monkeypatch.setattr(
        fork_cli.subprocess, "run", lambda command, **options: observed.append((command, options))
    )
    fork_cli.invoke(
        "din_sql",
        "reproduction.run",
        ["--input", "input.jsonl", "--run-dir", "runs/test", "--dataset=dataset"],
    )
    command, options = observed[0]
    assert options["cwd"] == repo
    assert "PYTHONPATH" not in options["env"]
    assert Path(command[command.index("--input") + 1]).is_absolute()
    assert command[1:3] == ["-m", "reproduction.run"]
    assert any(arg == "--dataset=" + str(Path("dataset").resolve()) for arg in command)


def test_orchestrator_context_has_no_credentials(monkeypatch, tmp_path):
    from scripts.common.io import read_json

    observed = []

    def invoke(name, module, arguments):
        context = read_json(arguments[arguments.index("--context") + 1])
        observed.append((name, module, context, arguments))

    monkeypatch.setattr(fork_cli, "invoke", invoke)
    args = SimpleNamespace(
        method="din_sql",
        input="input.jsonl",
        tables="tables.json",
        db_root="database",
        run_dir=tmp_path / "run",
        manifest="manifest.json",
        config=None,
        resume=True,
    )
    identity = {"code_hash": "fixture", "experiment": {"name": "smoke"}}
    fork_cli.run_method(args, identity, {"root": {"commit": "fixture"}})
    name, module, context, arguments = observed[0]
    assert name == "din_sql" and module == "reproduction.run"
    assert context["identity"] == identity
    assert "--resume" in arguments
    assert "api_key" not in str(context)


def test_standalone_runtimes_are_consistent_and_do_not_import_parent():
    forks = [
        ROOT / "third_party" / name
        for name in ("Few-shot-NL2SQL-with-prompting", "MAC-SQL", "DAIL-SQL")
    ]
    for module in (
        "io",
        "contracts",
        "llm",
        "config",
        "run_store",
        "sqlite_guard",
        "schema",
        "provenance",
        "run",
    ):
        copies = [(fork / "reproduction" / f"{module}.py").read_text() for fork in forks]
        assert len(set(copies)) == 1, f"Shared runtime drift: {module}"
    for fork in forks:
        for path in (fork / "reproduction").rglob("*.py"):
            assert not re.search(
                r"^\s*(?:from|import)\s+scripts(?:\.|\s)", path.read_text(), re.M
            ), path
