"""Initialize pinned submodules without resetting an existing checkout."""

import argparse
import subprocess

from scripts.common.io import ROOT, read_json
from scripts.common.sources import gitlink, source_path, verify_source


def bootstrap(methods, root=ROOT):
    for name in methods:
        path = source_path(name, root)
        expected = gitlink(path, root)
        if (path / ".git").exists():
            verify_source(name, root)
        else:
            if path.exists() and any(path.iterdir()):
                raise ValueError(f"Refusing to overwrite nonempty submodule path: {path}")
            relative = path.relative_to(root).as_posix()
            subprocess.run(
                ["git", "-C", str(root), "submodule", "update", "--init", "--", relative],
                check=True,
            )
            verify_source(name, root)
        print(f"{name}: verified gitlink {expected}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    names = list(read_json(ROOT / "configs/upstream_lock.json"))
    parser.add_argument("--methods", nargs="+", choices=names, default=names)
    args = parser.parse_args()
    bootstrap(args.methods)


if __name__ == "__main__":
    main()
