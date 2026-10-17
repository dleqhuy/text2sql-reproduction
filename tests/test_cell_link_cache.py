import importlib.util
import sqlite3
from types import SimpleNamespace

import nltk
import pytest

from scripts.common.io import ROOT
from tests.fork_modules import load_fork_module

CellLinkConnection = load_fork_module(
    "DAIL-SQL", "reproduction_cell_link_cache.py"
).CellLinkConnection


@pytest.mark.skipif(
    not (ROOT / "third_party/DAIL-SQL/utils/linking_utils/spider_match_utils.py").exists(),
    reason="Bootstrap DAIL source first",
)
def test_index_matches_original_cell_linking():
    nltk.data.path.insert(0, str(ROOT / "data/nltk_data"))
    spec = importlib.util.spec_from_file_location(
        "original_match", ROOT / "third_party/DAIL-SQL/utils/linking_utils/spider_match_utils.py"
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE things(value, number)")
    values = [
        "Alpha",
        " alpha ",
        "New York",
        "École",
        "école",
        "A_B",
        "ab%cd",
        "O'Reilly",
        "Beta  ",
        " Red Blue ",
        "Tokyo\x00tail",
        None,
        31,
        3.14,
        b"Alpha",
    ]
    connection.executemany(
        "INSERT INTO things VALUES (?,?)", [(v, i) for i, v in enumerate(values)]
    )
    table = SimpleNamespace(orig_name="things")
    columns = [
        SimpleNamespace(orig_name="*"),
        SimpleNamespace(orig_name="value", table=table, type="text"),
        SimpleNamespace(orig_name="number", table=table, type="number"),
    ]
    raw = SimpleNamespace(columns=columns, connection=connection)
    indexed = SimpleNamespace(columns=columns, connection=CellLinkConnection(connection))
    questions = [
        [word]
        for word in [
            "alpha",
            "Alpha",
            "École",
            "école",
            "New",
            "York",
            "Beta",
            "A_B",
            "ab%",
            "O'Reilly",
            "Tokyo",
            "3.14",
            "New York",
            "none",
        ]
    ]
    questions += [["New", "York"], ["Red", "Blue"], ["31", "alpha"], ["Beta", "Alpha"]]
    for tokens in questions:
        assert original.compute_cell_value_linking(
            tokens, raw
        ) == original.compute_cell_value_linking(tokens, indexed), tokens
    connection.execute("INSERT INTO things VALUES (CAST(X'80' AS TEXT), NULL)")
    indexed.connection = CellLinkConnection(connection)
    for tokens in (["alpha"], ["none"], ["Tokyo"]):
        assert original.compute_cell_value_linking(
            tokens, raw
        ) == original.compute_cell_value_linking(tokens, indexed)
    connection.close()
