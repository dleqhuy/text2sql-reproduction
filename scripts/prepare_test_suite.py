"""Extract official generated SQLite suites only for databases in a frozen experiment."""

import argparse
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from scripts.common.io import file_hash, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default=Path("data/test-suite"), type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Test-suite output already exists; refusing to overwrite")
    manifest = read_json(args.manifest)
    databases = set(manifest["database_hashes"])
    files = {}
    with zipfile.ZipFile(args.archive) as zipped:
        for item in zipped.infolist():
            parts = PurePosixPath(item.filename).parts
            if (
                len(parts) != 3
                or parts[0] != "database"
                or parts[1] not in databases
                or not parts[2].endswith(".sqlite")
                or parts[2].startswith("._")
            ):
                continue
            target = args.output / parts[1] / parts[2]
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(item) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            files[str(target.relative_to(args.output))] = file_hash(target)
    counts = {dbid: len(list((args.output / dbid).glob("*.sqlite"))) for dbid in databases}
    if any(n < 2 for n in counts.values()):
        raise ValueError("Missing original/generated SQLite suites for selected databases")
    write_json(
        "configs/test_suite_source.json",
        {
            "url": "https://drive.google.com/file/d/1mkCx2GOFIqNesD4y8TDAO1yX1QZORP5w/view",
            "archive_sha256": file_hash(args.archive),
            "archive_bytes": args.archive.stat().st_size,
            "selected_databases": sorted(databases),
            "sqlite_counts": counts,
            "database_hashes": files,
            "extraction": "Official archive members only, original plus generated SQLite; CRC checked on read",
        },
    )
    print(f"Extracted {len(files)} official suite databases for {len(databases)} Spider schemas")


if __name__ == "__main__":
    main()
