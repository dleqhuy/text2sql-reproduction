"""Fetch or import the checksum-pinned official Spider archive, keeping train/dev assets."""

import argparse
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from scripts.common.io import ROOT, file_hash, write_json

ARCHIVE_SHA256 = "00636695dabed6b5f4b8328a16b13e069a2f16591d5efcce57660669c85b121b"
OFFICIAL_URL = (
    "https://drive.usercontent.google.com/download?"
    "id=1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J&export=download&confirm=t"
)
MIRROR_REVISION = "4a01bbac6520cd35b216db9e1724e5e1ada60aa4"
MIRROR_URL = (
    "https://huggingface.co/datasets/HAL-9001/spider-databases/resolve/"
    f"{MIRROR_REVISION}/spider_data.zip"
)
REQUIRED = {"dev.json", "train_spider.json", "train_others.json", "tables.json"}
OPTIONAL = {"README.txt", "dev_gold.sql", "train_gold.sql"}


def import_archive(archive, output, provenance_path, source_url=OFFICIAL_URL):
    archive, output = Path(archive), Path(output)
    if output.exists():
        raise ValueError("Dataset output already exists; refusing to overwrite")
    actual = file_hash(archive)
    if actual != ARCHIVE_SHA256:
        raise ValueError("Spider archive SHA256 mismatch; HTML/quota pages are not datasets")
    output.parent.mkdir(parents=True, exist_ok=True)
    extracted, db_count = [], 0
    with tempfile.TemporaryDirectory(prefix=".spider-import-", dir=output.parent) as temporary:
        staging = Path(temporary) / "spider"
        staging.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            bad = zipped.testzip()
            if bad:
                raise ValueError("Spider archive CRC check failed")
            for item in zipped.infolist():
                parts = PurePosixPath(item.filename).parts
                if not parts or parts[0] != "spider_data" or item.is_dir():
                    continue
                relative = PurePosixPath(*parts[1:])
                if not relative.parts or any(
                    p in {"..", ".DS_Store"} or p.startswith("._") for p in relative.parts
                ):
                    continue
                if relative.parts[0] != "database" and str(relative) not in REQUIRED | OPTIONAL:
                    continue
                if stat.S_ISLNK(item.external_attr >> 16) or relative.is_absolute():
                    raise ValueError("Archive contains an unsafe member")
                target = staging.joinpath(*relative.parts)
                if not target.resolve().is_relative_to(staging.resolve()):
                    raise ValueError("Archive member escapes dataset directory")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(item) as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(str(relative))
                db_count += target.suffix == ".sqlite"
        if not REQUIRED <= set(extracted) or not db_count:
            raise ValueError("Archive does not contain required Spider train/dev assets")
        staging.rename(output)
    metadata = {
        "dataset": "Spider 1.0",
        "source": "official Yale Google Drive distribution",
        "source_url": source_url,
        "archive_sha256": actual,
        "archive_bytes": archive.stat().st_size,
        "checksum_reference": "https://huggingface.co/datasets/HAL-9001/spider-databases",
        "fallback_mirror_revision": MIRROR_REVISION,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "license": "CC-BY-SA-4.0",
        "extraction_scope": "train/dev JSON, schemas, database, gold SQL, README",
        "sqlite_files": db_count,
        "file_count": len(extracted),
        "source_hashes": {name: file_hash(output / name) for name in sorted(REQUIRED)},
    }
    write_json(provenance_path, metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use an already downloaded archive")
    parser.add_argument("--source", choices=["official", "mirror"], default="official")
    parser.add_argument("--output", type=Path, default=ROOT / "data/spider")
    parser.add_argument("--provenance", type=Path, default=ROOT / "configs/spider_source.json")
    args = parser.parse_args()
    url = OFFICIAL_URL if args.source == "official" else MIRROR_URL
    if args.output.exists():
        parser.error("Dataset output already exists; choose a new directory")
    if args.archive:
        result = import_archive(args.archive, args.output, args.provenance, url)
    else:
        with tempfile.TemporaryDirectory(prefix="spider-download-") as temporary:
            path = Path(temporary) / "spider_data.zip"
            with urllib.request.urlopen(url, timeout=60) as response, path.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            result = import_archive(path, args.output, args.provenance, url)
    print(
        f"Imported checksum-verified Spider train/dev with {result['sqlite_files']} SQLite files."
    )


if __name__ == "__main__":
    main()
