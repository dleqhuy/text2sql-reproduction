import pytest

from scripts.common.contracts import failure
from scripts.common.evaluator import official_match
from scripts.common.io import ROOT, file_hash
from scripts.common.sqlite_guard import execute
from scripts.evaluate_spider import evaluate
from scripts.summarize_results import summarize


def official_available():
    return (ROOT / "third_party/spider/evaluation.py").exists() and (
        ROOT / "data/nltk_data/tokenizers/punkt_tab/english"
    ).exists()


def test_read_only_and_multiple_statement_guard(spider_fixture):
    _, path, _ = spider_fixture
    before = file_hash(path)
    assert execute(path, "WITH x AS (SELECT name FROM people) SELECT * FROM x")["status"] == "ok"
    for sql in (
        "DELETE FROM people",
        "ATTACH DATABASE '/tmp/forbidden.sqlite' AS attack",
        "SELECT 1; DELETE FROM people",
        "PRAGMA writable_schema=ON",
        "SELECT load_extension('evil')",
    ):
        assert execute(path, sql)["status"] == "sql_error"
    assert file_hash(path) == before


def test_query_timeout(spider_fixture):
    _, path, _ = spider_fixture
    sql = "WITH RECURSIVE x(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM x) SELECT sum(n) FROM x"
    assert execute(path, sql, 0.1)["status"] == "timeout"


@pytest.mark.skipif(not official_available(), reason="Bootstrap official evaluator + NLTK first")
def test_official_evaluator_fixture(spider_fixture):
    _, path, table = spider_fixture
    repo = ROOT / "third_party/spider"
    good = "SELECT name FROM people"
    assert official_match(repo, path, good, good, table) == {"status": "ok", "correct": True}
    bad = "SELECT name FROM people WHERE id = 1"
    assert official_match(repo, path, bad, good, table)["correct"] is False


@pytest.mark.skipif(not official_available(), reason="Bootstrap official evaluator + NLTK first")
def test_denominator_includes_failure_and_wrong_sql(spider_fixture):
    source, _, table = spider_fixture
    inputs = [{"example_id": str(i), "db_id": "mini", "question": "Q"} for i in range(4)]
    gold = [
        {"example_id": str(i), "db_id": "mini", "query": "SELECT name FROM people"}
        for i in range(4)
    ]
    predictions = []
    for item, sql in zip(
        inputs,
        (
            "SELECT name FROM people",
            "SELECT name FROM people WHERE id=1",
            "SELECT absent FROM people",
            None,
        ),
        strict=True,
    ):
        row = failure(item, "vanilla", "fixture", "missing_prediction", "missing")
        if sql:
            row.update(status="ok", predicted_sql=sql, error=None)
        predictions.append(row)
    results = evaluate(
        inputs, predictions, gold, {"mini": table}, source / "database", ROOT / "third_party/spider"
    )
    summary = summarize(inputs, predictions, results)
    assert summary["n"] == 4
    assert summary["ex"] == 0.25
    assert summary["valid_sql_rate"] == 0.5
    assert summary["api_calls"]["coverage_n"] == 0
    # Output order cannot change ID-based evaluation.
    assert summarize(inputs, list(reversed(predictions)), results)["ex"] == 0.25
    with pytest.raises(ValueError):
        summarize(inputs, predictions, results[:-1])
