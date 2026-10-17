import pytest

from scripts.common.schema import extract_sql
from tests.fork_modules import load_fork_module

parse_din_classification = load_fork_module(
    "Few-shot-NL2SQL-with-prompting"
).parse_din_classification


def parse_mac_sql(text):
    return load_fork_module("MAC-SQL").parse_mac_sql(text, extract_sql)


def test_nested_classification_without_subquestions():
    label, sub, fallback = parse_din_classification(
        'Classified as **NESTED**.\nLabel: "NESTED"', "Q"
    )
    assert (label, sub, fallback) == ("NESTED", "Q", True)


def test_nested_classification_single_quotes():
    assert (
        parse_din_classification("The query joins two tables. **NON-NESTED**", "Q")[0]
        == "NON-NESTED"
    )
    assert parse_din_classification("Label: 'NESTED' questions = ['one', 'two']", "Q") == (
        "NESTED",
        "one two",
        False,
    )
    assert parse_din_classification("Label: NON-NESTED", "Q")[0] == "NON-NESTED"
    with pytest.raises(ValueError):
        parse_din_classification("unknown classification", "Q")


def test_mac_accepts_plain_and_fenced_queries():
    sql = "SELECT p.`Name` FROM people AS p ORDER BY p.`Name`;"
    assert parse_mac_sql(sql) == sql
    assert parse_mac_sql("reason\n```SQL\n" + sql + "\n```") == sql
    with pytest.raises(ValueError):
        parse_mac_sql("error: No SQL found in the input string")
