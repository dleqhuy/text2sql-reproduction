"""Run all four methods, both DAIL stages, evaluation and reporting sequentially."""

import argparse
import shlex
import sys
from pathlib import Path

from scripts.common.benchmark_pipeline import execute, preflight
from scripts.common.benchmark_plan import plan
from scripts.common.benchmark_report import report
from scripts.common.io import ROOT, read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-manifest", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path, help="New directory beneath runs/")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/spider")
    parser.add_argument("--suite-db-root", type=Path, default=ROOT / "data/test-suite")
    parser.add_argument(
        "--embedding-config", type=Path, default=ROOT / "configs/dail_embedding.json"
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without API calls/writes"
    )
    args = parser.parse_args()
    output, dataset, suite, embedding, manifest = [
        p.resolve()
        for p in (
            args.run_dir,
            args.dataset,
            args.suite_db_root,
            args.embedding_config,
            args.experiment_manifest,
        )
    ]
    if not output.is_relative_to(ROOT / "runs") or output == ROOT / "runs":
        parser.error("--run-dir must be a child directory of runs/")
    experiment = read_json(manifest)
    stages = plan(experiment, output, dataset, suite, embedding)
    if args.dry_run:
        for stage in stages:
            extra = (
                ["--experiment-manifest", manifest] if stage.module == "scripts.run_method" else []
            )
            print(
                shlex.join(map(str, [sys.executable, "-m", stage.module, *stage.arguments, *extra]))
            )
        print(f"Finally write {output / 'report.md'} and {output / 'comparison.json'}")
        return
    inputs, identity = preflight(experiment, dataset, suite, embedding, manifest)

    def finish():
        report(output, inputs, identity["experiment_hash"])
        return [output / "report.md", output / "comparison.json"]

    execute(stages, output, identity, manifest, args.resume, finish=finish)
    print(f"Benchmark complete: {output / 'report.md'}")


if __name__ == "__main__":
    main()
