"""Exercise original two-stage DAIL retrieval with synthetic vectors and cached linking fixtures."""

import argparse
import json
import sys
import types
from pathlib import Path

import numpy as np

from scripts.common.contracts import failure
from scripts.common.io import ROOT, read_json, read_jsonl, write_json, write_jsonl
from scripts.prepare_dail import prepare


class FixtureEncoder:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, questions):
        return np.array([[len(q), 1.0] for q in questions])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    train = [
        {"db_id": "mini", "question": "Give person identifiers", "query": "SELECT id FROM people"},
        {"db_id": "mini", "question": "Give person names", "query": "SELECT name FROM people"},
    ]
    write_json(args.source / "train_spider.json", train)
    write_json(args.source / "train_spider_and_others.json", train)
    dev = read_json(args.source / "dev.json")
    for row in dev:
        row["query"] = "SELECT count(*) AS private_dev_gold_marker FROM people"
    write_json(args.source / "dev.json", dev)

    def links(rows):
        return [
            {
                "sc_link": {"q_col_match": {}, "q_tab_match": {}},
                "cv_link": {"num_date_match": {}, "cell_match": {}},
                "question_for_copying": r["question"].split(),
                "column_to_table": {"1": 0, "2": 0},
            }
            for r in rows
        ]

    write_jsonl(args.source / "enc/train_schema-linking.jsonl", links(train))
    write_jsonl(args.source / "enc/test_schema-linking.jsonl", links(dev))
    bridge = types.ModuleType("sentence_transformers")
    bridge.SentenceTransformer = FixtureEncoder
    sys.modules["sentence_transformers"] = bridge
    options = argparse.Namespace(
        repo=ROOT / "third_party/DAIL-SQL",
        dataset=args.source,
        input=args.input,
        stage="preliminary",
        preliminary=None,
        output=args.output / "preliminary.json",
        k_shot=1,
        tokenizer="gpt-3.5-turbo",
        context_tokens=4096,
        scope_factor=100,
    )
    prepare(options)
    predictions = []
    for row in read_jsonl(args.input):
        prediction = failure(row, "dail_sql", "fixture", "parse_error", "missing")
        prediction.update(status="ok", predicted_sql="SELECT id FROM people", error=None)
        predictions.append(prediction)
    path = args.output / "preliminary_predictions.jsonl"
    write_jsonl(path, predictions)
    options.stage, options.preliminary, options.output = "final", path, args.output / "final.json"
    prepare(options)
    bundle = read_json(options.output)
    assert bundle["selector"] == "EUCDISMASKPRESKLSIMTHR"
    assert all(q["selected_train_indices"] for q in bundle["questions"])
    assert "private_dev_gold_marker" not in json.dumps(bundle)
    print("Original two-stage DAIL selection and gold separation verified with fixture vectors")


if __name__ == "__main__":
    main()
