"""Run original DAIL schema/cell linking with its original CoreNLP tokenization methods."""

import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts.common.io import ROOT, file_hash, read_json, write_json
from scripts.common.provenance import git_info
from scripts.common.sources import load_integration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/spider")
    parser.add_argument("--corenlp-endpoint", default="http://localhost:19000")
    parser.add_argument(
        "--indexed-cell-links",
        action="store_true",
        help="Equivalent immutable SQLite LIKE indexes, verified against source",
    )
    args = parser.parse_args()
    os.environ.setdefault("NLTK_DATA", str(ROOT / "data/nltk_data"))
    os.environ.setdefault("HF_HOME", str(ROOT / "data/assets/huggingface"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(ROOT / "data/assets/huggingface/transformers"))
    repo = ROOT / "third_party/DAIL-SQL"
    sys.path.insert(0, str(repo))
    import corenlp
    import data_preprocess
    from utils.linking_utils import corenlp as original_bridge
    from utils.pretrained_embeddings import GloVe

    cell_connection = None
    if args.indexed_cell_links:
        from scripts.common.cell_link_cache import CellLinkConnection

        cell_connection = CellLinkConnection
    load_integration("dail_sql").configure_linking(data_preprocess, GloVe, cell_connection)

    if (args.dataset / "enc").exists():
        raise ValueError("Linking cache already exists; refusing to overwrite")
    train = read_json(args.dataset / "train_spider.json") + read_json(
        args.dataset / "train_others.json"
    )
    write_json(args.dataset / "train_spider_and_others.json", train)
    client = corenlp.CoreNLPClient(
        start_server=False, endpoint=args.corenlp_endpoint, timeout=30000
    )
    original_bridge._singleton = SimpleNamespace(annotate=client.annotate)
    data_preprocess.schema_linking_producer(
        "dev.json", "train_spider_and_others.json", "tables.json", "database", str(args.dataset)
    )
    write_json(
        args.dataset / "enc/provenance.json",
        {
            "upstream": git_info(repo),
            "corenlp": "3.9.2",
            "tokenizer": "original GloVe.tokenize/tokenize_for_copying with lemmatize=True",
            "adaptation": "Skipped unused GloVe vector allocation; original linking algorithms unchanged",
            "indexed_literal_like": args.indexed_cell_links,
            "sources": {
                name: file_hash(args.dataset / name)
                for name in ("dev.json", "train_spider_and_others.json", "tables.json")
            },
            "outputs": {
                name: file_hash(args.dataset / "enc" / name)
                for name in ("train_schema-linking.jsonl", "test_schema-linking.jsonl")
            },
        },
    )
    print("Original DAIL schema/cell linking completed")


if __name__ == "__main__":
    main()
