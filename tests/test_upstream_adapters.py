import subprocess

import pytest

from scripts.common.io import ROOT, write_jsonl


@pytest.mark.parametrize("branch", ["EASY", "NON-NESTED", "NESTED"])
def test_original_din_stages(spider_fixture, branch):
    python = ROOT / "third_party/Few-shot-NL2SQL-with-prompting/.venv/bin/python"
    if not python.exists():
        pytest.skip("Install isolated DIN environment first")
    source, _, _ = spider_fixture
    subprocess.run(
        [
            str(python),
            "-m",
            "tests.upstream_probe",
            "--method",
            "din",
            "--branch",
            branch,
            "--tables",
            str(source / "tables.json"),
            "--db-root",
            str(source / "database"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_original_mac_execution_feedback(spider_fixture):
    python = ROOT / "third_party/MAC-SQL/.venv/bin/python"
    if not python.exists():
        pytest.skip("Install isolated MAC environment first")
    source, _, _ = spider_fixture
    subprocess.run(
        [
            str(python),
            "-m",
            "tests.upstream_probe",
            "--method",
            "mac",
            "--tables",
            str(source / "tables.json"),
            "--db-root",
            str(source / "database"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_original_dail_two_stage_selection(spider_fixture, tmp_path):
    python = ROOT / "third_party/DAIL-SQL/.venv/bin/python"
    if not python.exists() or not (ROOT / "data/nltk_data/corpora/stopwords").exists():
        pytest.skip("Install DAIL environment and stopwords first")
    source, _, _ = spider_fixture
    inputs = tmp_path / "inputs.jsonl"
    write_jsonl(
        inputs,
        [{"example_id": "dev_000000", "db_id": "mini", "question": "How many people are there?"}],
    )
    result = subprocess.run(
        [
            str(python),
            "-m",
            "tests.dail_probe",
            "--source",
            str(source),
            "--input",
            str(inputs),
            "--output",
            str(tmp_path / "bundles"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
