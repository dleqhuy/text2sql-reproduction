"""Clone exact upstream commits; never reset user changes or auto-pull existing checkouts."""

import argparse
import subprocess

from scripts.common.io import ROOT, read_json
from scripts.common.provenance import git_info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["dail_sql", "din_sql", "mac_sql", "spider", "test_suite"],
        default=["dail_sql", "din_sql", "mac_sql", "spider", "test_suite"],
    )
    args = parser.parse_args()
    lock = read_json(ROOT / "configs/upstream_lock.json")
    for method in args.methods:
        source = lock[method]
        path = ROOT / "third_party" / source["directory"]
        if not path.exists():
            subprocess.run(["git", "clone", source["url"], str(path)], check=True)
            subprocess.run(
                ["git", "-C", str(path), "checkout", "--detach", source["commit"]], check=True
            )
        info = git_info(path)
        if info["commit"] != source["commit"] or info["dirty"]:
            raise ValueError(f"{method}: checkout differs from lock; inspect manually")
        print(f"{method}: verified {source['commit']}")


if __name__ == "__main__":
    main()
