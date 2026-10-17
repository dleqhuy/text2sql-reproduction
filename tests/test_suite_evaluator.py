import shutil
import sqlite3

import pytest

from scripts.common.evaluator import suite_match
from scripts.common.io import ROOT

REPO = ROOT / "third_party/test-suite-sql-eval"
pytestmark = pytest.mark.skipif(
    not (REPO / "exec_eval.py").exists(), reason="Bootstrap evaluator first"
)


def test_quoted_identifiers_and_distinct(spider_fixture):
    _, path, _ = spider_fixture
    assert suite_match(REPO, path, "SELECT `name` FROM `people`", "SELECT name FROM people")[
        "correct"
    ]
    assert not suite_match(
        REPO, path, "SELECT name FROM people WHERE id=1", "SELECT name FROM people"
    )["correct"]
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO people VALUES (3, 'An')")
    assert not suite_match(
        REPO, path, "SELECT name FROM people", "SELECT DISTINCT name FROM people"
    )["correct"]


def test_neighbor_database_catches_accidental_equivalence(spider_fixture):
    _, path, _ = spider_fixture
    prediction, gold = "SELECT 2 FROM people LIMIT 1", "SELECT count(*) FROM people"
    assert suite_match(REPO, path, prediction, gold)["correct"]
    neighbor = path.with_name("neighbor.sqlite")
    shutil.copy2(path, neighbor)
    with sqlite3.connect(neighbor) as conn:
        conn.execute("INSERT INTO people VALUES (3, 'C')")
    assert not suite_match(REPO, path, prediction, gold)["correct"]


def test_execution_cannot_write(spider_fixture):
    _, path, _ = spider_fixture
    result = suite_match(REPO, path, "DELETE FROM people", "SELECT name FROM people")
    assert result == {"status": "ok", "correct": False}
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM people").fetchone()[0] == 2
