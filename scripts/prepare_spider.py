"""Prepare deterministic DB-balanced dev subsets, separating gold from inference."""

import argparse
import random
from collections import defaultdict
from pathlib import Path

from scripts.common.contracts import validate_inputs
from scripts.common.io import db_path, digest, file_hash, read_json, write_json, write_jsonl
from scripts.common.schema import load_schemas
from scripts.common.sqlite_guard import readonly_connect


def select_indices(dev, size, seed):
    if not 0 < size <= len(dev):
        raise ValueError("Subset size exceeds available examples or is not positive")
    rng = random.Random(seed)
    buckets = defaultdict(list)
    for index, row in enumerate(dev):
        buckets[row["db_id"]].append(index)
    keys = sorted(buckets)
    rng.shuffle(keys)
    for indices in buckets.values():
        rng.shuffle(indices)
    selected = []
    while len(selected) < size:
        for key in keys:
            if buckets[key]:
                selected.append(buckets[key].pop())
                if len(selected) == size:
                    break
    return sorted(selected)


def validate_schema(schema, path):
    with readonly_connect(path) as conn:
        actual = {
            r[0].lower() for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for tid, table in enumerate(schema["table_names_original"]):
            if table.lower() not in actual:
                raise ValueError(f"Schema table missing from DB: {schema['db_id']}.{table}")
            quoted = table.replace('"', '""')
            columns = {r[1].lower() for r in conn.execute(f'PRAGMA table_info("{quoted}")')}
            expected = {
                name.lower() for index, name in schema["column_names_original"] if index == tid
            }
            if not expected <= columns:
                raise ValueError(f"Schema columns missing: {schema['db_id']}.{table}")


def prepare(source, output, size=100, smoke_size=10, seed=42):
    source, output = Path(source), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory is not empty; frozen splits cannot be overwritten")
    dev = read_json(source / "dev.json")
    train = read_json(source / "train_spider.json")
    schemas = load_schemas(source / "tables.json")
    if not isinstance(train, list) or not train:
        raise ValueError("Missing nonempty Spider train split")
    selected = select_indices(dev, size, seed)
    if not 0 < smoke_size <= size:
        raise ValueError("Smoke size must be within main subset")
    rows, gold, fingerprints = [], [], {}
    for index in selected:
        row = dev[index]
        dbid = row["db_id"]
        if dbid not in schemas:
            raise ValueError(f"Missing schema for {dbid}")
        if dbid not in fingerprints:
            path = db_path(source / "database", dbid)
            validate_schema(schemas[dbid], path)
            fingerprints[dbid] = file_hash(path)
        eid = f"dev_{index:06d}"
        rows.append({"example_id": eid, "db_id": dbid, "question": row["question"]})
        gold.append({"example_id": eid, "db_id": dbid, "query": row["query"]})
    validate_inputs(rows)
    smoke_indices = select_indices(rows, smoke_size, seed)
    smoke = [rows[i] for i in smoke_indices]
    manifest = {
        "version": 1,
        "split": "dev",
        "seed": seed,
        "algorithm": "db-balanced-round-robin-v1",
        "size": size,
        "ordered_ids": [r["example_id"] for r in rows],
        "original_indices": selected,
        "smoke_ids": [r["example_id"] for r in smoke],
        "source_hashes": {
            name: file_hash(source / name)
            for name in ("dev.json", "train_spider.json", "tables.json")
        },
        "database_hashes": fingerprints,
        "input_hash": digest(rows),
        "smoke_input_hash": digest(smoke),
    }
    write_jsonl(output / "main.jsonl", rows)
    write_jsonl(output / "smoke.jsonl", smoke)
    write_jsonl(output / "gold.jsonl", gold)
    manifest["gold_hash"] = file_hash(output / "gold.jsonl")
    write_json(output / "manifest.json", manifest)
    write_json(output / "tables.json", read_json(source / "tables.json"))
    manifest["prepared_tables_hash"] = file_hash(output / "tables.json")
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--smoke-size", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    manifest = prepare(args.source, args.output, args.size, args.smoke_size, args.seed)
    print(f"Prepared {manifest['size']} main and {len(manifest['smoke_ids'])} smoke IDs.")


if __name__ == "__main__":
    main()
