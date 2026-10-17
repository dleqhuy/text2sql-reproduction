"""Create a tiny synthetic dataset for integration checks, never a Spider benchmark."""

import argparse
import sqlite3
from pathlib import Path

from scripts.common.io import write_json
from scripts.prepare_spider import prepare


def create_fixture(output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Fixture directory must be empty")
    source = output / "source"
    path = source / "database/fixture_people/fixture_people.sqlite"
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(
            "CREATE TABLE people(id INTEGER PRIMARY KEY, name TEXT);"
            "INSERT INTO people VALUES (1, 'An'), (2, 'Binh');"
        )
    columns = [[-1, "*"], [0, "id"], [0, "name"]]
    table = {
        "db_id": "fixture_people",
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
            "db_id": "fixture_people",
            "question": "How many people are there?",
            "query": "SELECT count(*) FROM people",
        }
    ]
    train = [{"db_id": "training_only", "question": "Training placeholder", "query": "SELECT 1"}]
    for name, value in (("tables.json", [table]), ("dev.json", dev), ("train_spider.json", train)):
        write_json(source / name, value)
    prepare(source, output / "prepared", size=1, smoke_size=1)
    print(f"Synthetic fixture created in {output}; results are not Spider scores.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/prepared/fixture", type=Path)
    create_fixture(parser.parse_args().output)


if __name__ == "__main__":
    main()
