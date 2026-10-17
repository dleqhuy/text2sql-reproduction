import json
import sqlite3

import pytest


@pytest.fixture
def spider_fixture(tmp_path):
    source = tmp_path / "spider"
    path = source / "database" / "mini" / "mini.sqlite"
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(
            "CREATE TABLE people(id INTEGER PRIMARY KEY, name TEXT);"
            "INSERT INTO people VALUES (1, 'An'), (2, 'Binh');"
        )
    columns = [[-1, "*"], [0, "id"], [0, "name"]]
    table = {
        "db_id": "mini",
        "table_names_original": ["people"],
        "table_names": ["people"],
        "column_names_original": columns,
        "column_names": columns,
        "column_types": ["text", "number", "text"],
        "primary_keys": [1],
        "foreign_keys": [],
    }
    dev = [
        {
            "db_id": "mini",
            "question": "How many people are there?",
            "query": "SELECT count(*) FROM people",
        },
        {"db_id": "mini", "question": "List all names.", "query": "SELECT name FROM people"},
    ]
    train = [{"db_id": "training_only", "question": "A training question", "query": "SELECT 1"}]
    for name, value in (("tables.json", [table]), ("dev.json", dev), ("train_spider.json", train)):
        (source / name).write_text(json.dumps(value))
    return source, path, table
