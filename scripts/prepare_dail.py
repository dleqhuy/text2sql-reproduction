"""Use DAIL's original prompt factory on its preprocessed Spider assets (two stages)."""

import argparse
import os
import sys
from pathlib import Path

from scripts.common.contracts import validate_inputs, validate_predictions
from scripts.common.io import ROOT, digest, file_hash, read_json, read_jsonl, write_json
from scripts.common.provenance import git_info


def prepare(args):
    if args.k_shot < 1 or args.context_tokens < 1 or args.scope_factor < 1:
        raise ValueError("DAIL requires positive k-shot, context tokens and scope factor")
    os.environ.setdefault("NLTK_DATA", str(ROOT / "data/nltk_data"))
    os.environ.setdefault("HF_HOME", str(ROOT / ".uv-cache/huggingface"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(ROOT / ".uv-cache/huggingface/transformers"))
    inputs = read_jsonl(args.input)
    validate_inputs(inputs)
    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo))
    from prompt.prompt_builder import prompt_factory
    from utils.data_builder import SpiderDataset

    source = Path(args.dataset).resolve()
    train_path = source / "train_spider_and_others.json"
    dev_path = source / "dev.json"
    # Verify candidate corpus against declared Spider training sources before loading retrieval.
    train = read_json(source / "train_spider.json")
    if (source / "train_others.json").exists():
        train += read_json(source / "train_others.json")
    allowed = {(r["db_id"], r["question"], r["query"]) for r in train}
    if any((r["db_id"], r["question"], r["query"]) not in allowed for r in read_json(train_path)):
        raise ValueError("DAIL candidate corpus contains non-training records")
    if not all(
        (source / "enc" / f"{split}_schema-linking.jsonl").is_file() for split in ("train", "test")
    ):
        raise ValueError("Run original DAIL schema-linking preprocessing before prompt generation")
    selector = "EUCDISQUESTIONMASK" if args.stage == "preliminary" else "EUCDISMASKPRESKLSIMTHR"
    predictions = {}
    if args.stage == "final":
        if not args.preliminary:
            raise ValueError("Final DAIL stage requires --preliminary normalized predictions")
        preliminary = read_jsonl(args.preliminary)
        validate_predictions(preliminary, inputs)
        if any(r["status"] != "ok" for r in preliminary):
            raise ValueError("Preliminary predictions must all succeed before final retrieval")
        predictions = {r["example_id"]: r["predicted_sql"] for r in preliminary}
    data = SpiderDataset(str(source.parent))
    if source.name != "spider":
        raise ValueError("Upstream expects a directory named spider beneath dataset parent")
    data.get_databases()
    embedding = None
    embedding_config = getattr(args, "embedding_config", None)
    if embedding_config:
        embedding = read_json(embedding_config)
        import sentence_transformers

        original_encoder = sentence_transformers.SentenceTransformer

        def pinned_encoder(model, **kwargs):
            if model != embedding["model"]:
                raise ValueError("Upstream requested a different embedding model")
            import numpy as np
            import torch

            torch.set_num_threads(4)
            encoder = original_encoder(embedding["local_path"], **kwargs)
            original_encode = encoder.encode

            def encode(sentences, **options):
                if len(sentences) < 100 or options:
                    return original_encode(sentences, **options)
                key = digest(
                    {"model": model, "revision": embedding["revision"], "texts": sentences}
                )
                cache = ROOT / "data/assets/embeddings" / f"{key}.npy"
                if cache.exists():
                    return np.load(cache, allow_pickle=False)
                vectors = original_encode(sentences)
                cache.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache.with_suffix(".pending")
                with temporary.open("wb") as stream:
                    np.save(stream, vectors, allow_pickle=False)
                temporary.replace(cache)
                return vectors

            encoder.encode = encode
            return encoder

        sentence_transformers.SentenceTransformer = pinned_encoder
    try:
        prompt = prompt_factory("SQL", args.k_shot, "QA", selector)(
            data=data, tokenizer=args.tokenizer
        )
    finally:
        if embedding_config:
            sentence_transformers.SentenceTransformer = original_encoder
    # Ground-truth query-skeleton quality is diagnostic in BasicICLPrompt, not retrieval.
    # Disable it rather than feeding dev gold into target structures.
    selected = []
    prompt.record_example_quality = lambda examples, target: selected.extend(examples)
    dev = read_json(dev_path)
    linking = data.get_test_schema_linking()
    train_keys = {(r["db_id"], r["question"]): i for i, r in enumerate(train)}
    dev_keys = {(r["db_id"], r["question"]) for r in dev}
    if dev_keys & set(train_keys):
        raise ValueError("Training demonstrations overlap dev questions")
    from utils.linking_utils.application import get_question_pattern_with_schema_linking
    from utils.utils import sql2skeleton

    tables = {r["db_id"]: r for r in data.get_table_json()}
    questions = []
    for row in inputs:
        index = int(row["example_id"].removeprefix("dev_"))
        if (dev[index]["db_id"], dev[index]["question"]) != (row["db_id"], row["question"]):
            raise ValueError("DAIL source dev ordering differs from fixed manifest")
        info = linking[index]
        target = {
            "db_id": row["db_id"],
            "question": row["question"],
            "query": "",
            "query_skeleton": "",
            "tables": data.get_tables(row["db_id"]),
            "path_db": data.get_path_db(row["db_id"]),
            "table_names_original": tables[row["db_id"]]["table_names_original"],
        }
        for key in ("sc_link", "cv_link", "question_for_copying", "column_to_table"):
            target[key] = info[key]
        target["question_pattern"] = get_question_pattern_with_schema_linking([target])[0]
        if predictions:
            target["pre_skeleton"] = sql2skeleton(
                predictions[row["example_id"]], tables[row["db_id"]]
            )
        selected.clear()
        formatted = prompt.format(
            target, args.context_tokens, 200, args.scope_factor, cross_domain=False
        )
        questions.append(
            {
                **row,
                "prompt": formatted["prompt"],
                "selected_train_indices": [
                    train_keys[(r["db_id"], r["question"])] for r in selected
                ],
            }
        )
    hashes = {
        name: file_hash(source / name)
        for name in (
            "train_spider_and_others.json",
            "train_spider.json",
            "tables.json",
            "dev.json",
            "enc/train_schema-linking.jsonl",
            "enc/test_schema-linking.jsonl",
        )
    }
    write_json(
        args.output,
        {
            "generator": "upstream-dail-prompt-factory-v1",
            "stage": args.stage,
            "selector": selector,
            "upstream": git_info(repo),
            "input_hash": digest(inputs),
            "asset_hashes": hashes,
            "k_shot": args.k_shot,
            "tokenizer": args.tokenizer,
            "embedding": embedding,
            "preliminary_hash": file_hash(args.preliminary) if args.preliminary else None,
            "questions": questions,
        },
    )
    print(f"Generated {len(questions)} original DAIL prompts ({args.stage}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(ROOT / "third_party/DAIL-SQL"))
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--stage", choices=["preliminary", "final"], required=True)
    parser.add_argument("--preliminary")
    parser.add_argument("--output", required=True)
    parser.add_argument("--k-shot", type=int, default=9)
    parser.add_argument("--tokenizer", default="gpt-3.5-turbo")
    parser.add_argument("--context-tokens", type=int, default=4096)
    parser.add_argument("--scope-factor", type=int, default=100)
    parser.add_argument("--embedding-config", help="Pinned MPNet snapshot config")
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
