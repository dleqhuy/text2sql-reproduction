"""Check or sync the canonical runtime into the three standalone forks."""

import argparse
from pathlib import Path

from scripts.common.io import ROOT, atomic_text, read_json
from scripts.common.sources import git, source_path


def synchronize(source: Path, targets: list[Path], write=False):
    """Validate every destination before writing; never overwrite local runtime edits."""
    files = sorted(p.relative_to(source) for p in source.rglob("*") if p.suffix in {".py", ".json"})
    if not files:
        raise ValueError("Canonical runtime is empty")
    changes = []
    for target in targets:
        for relative in files:
            destination = target / relative
            if destination.is_symlink() or not destination.resolve().is_relative_to(
                target.resolve()
            ):
                raise ValueError(f"Runtime destination escapes the fork: {relative}")
            if (
                not destination.is_file()
                or destination.read_bytes() != (source / relative).read_bytes()
            ):
                if write and git(target, "status", "--porcelain", "--", str(relative)):
                    raise ValueError(
                        f"Commit or preserve local runtime edits first: {target / relative}"
                    )
                changes.append((target, relative))
    if write:
        for target, relative in changes:
            atomic_text(target / relative, (source / relative).read_text(encoding="utf-8"))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Sync files; default only checks drift"
    )
    args = parser.parse_args()
    targets = [
        source_path(key)
        for key, metadata in read_json(ROOT / "configs/upstream_lock.json").items()
        if metadata["role"] == "method"
    ]
    for target in targets:
        if not (target / ".git").exists():
            parser.error(f"Initialize submodules first: {target}")
    changes = synchronize(ROOT / "runtime", targets, args.write)
    if changes and not args.write:
        for target, relative in changes:
            print((target / relative).relative_to(ROOT))
        parser.exit(1, "Runtime drift found; edit runtime/ and run with --write.\n")
    print(
        f"Synced {len(changes)} files." if args.write else "All fork runtime copies match runtime/."
    )


if __name__ == "__main__":
    main()
