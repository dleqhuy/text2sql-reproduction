"""Build the ordered commands and artifacts of a benchmark."""

from dataclasses import dataclass
from pathlib import Path

from scripts.common.config import load_config
from scripts.common.experiment import referenced_path
from scripts.common.io import ROOT


@dataclass
class Stage:
    name: str
    module: str
    arguments: list[str | Path]
    outputs: list[Path]


def plan(experiment, output, dataset, suite, embedding):
    refs = experiment["files"]
    inputs = referenced_path(refs["input"], ROOT)
    manifest = referenced_path(refs["dataset_manifest"], ROOT)
    config = referenced_path(refs["config"], ROOT)
    tables, gold = manifest.parent / "tables.json", manifest.parent / "gold.jsonl"
    common = [
        "--input",
        inputs,
        "--manifest",
        manifest,
        "--tables",
        tables,
        "--db-root",
        dataset / "database",
    ]
    stages = []

    def prepare(stage):
        bundle = output / f"dail-{stage}-prompts.json"
        args = [
            "--dataset",
            dataset,
            "--input",
            inputs,
            "--stage",
            stage,
            "--embedding-config",
            embedding,
            "--output",
            bundle,
        ]
        if stage == "final":
            args += ["--preliminary", output / "dail-preliminary/predictions.jsonl"]
        stages.append(Stage(f"prepare-{stage}", "scripts.prepare_dail", args, [bundle]))

    def infer(method, folder, stage=None):
        args = [
            "--method",
            method,
            *common,
            "--config",
            config,
            "--run-dir",
            output / folder,
            "--production",
        ]
        if stage:
            args += ["--dail-prompts", output / f"dail-{stage}-prompts.json"]
        stages.append(Stage(folder, "scripts.run_method", args, [output / folder]))

    # Discover missing retrieval assets before sending any paid requests.
    prepare("preliminary")
    for method, folder in [("vanilla", "vanilla"), ("din_sql", "din"), ("mac_sql", "mac")]:
        infer(method, folder)
    infer("dail_sql", "dail-preliminary", "preliminary")
    prepare("final")
    infer("dail_sql", "dail-final", "final")
    stages.append(
        Stage(
            "dail",
            "scripts.aggregate_dail",
            [
                "--input",
                inputs,
                "--preliminary-run",
                output / "dail-preliminary",
                "--final-run",
                output / "dail-final",
                "--output",
                output / "dail",
            ],
            [output / "dail"],
        )
    )
    for folder in ("vanilla", "dail", "din", "mac"):
        predictions = output / folder / "predictions.jsonl"
        for metric in ("test-suite", "execution"):
            destination = output / folder / f"eval-{metric}"
            args = [
                *common,
                "--predictions",
                predictions,
                "--gold",
                gold,
                "--metric",
                metric,
                "--timeout",
                str(load_config(config)["sql_timeout_s"]),
                "--output",
                destination,
            ]
            if metric == "test-suite":
                args += ["--suite-db-root", suite]
            stages.append(
                Stage(
                    f"{folder}-{metric}",
                    "scripts.evaluate_spider",
                    args,
                    [destination / "evaluation.jsonl", destination / "evaluation_config.json"],
                )
            )
            stages.append(
                Stage(
                    f"{folder}-{metric}-summary",
                    "scripts.summarize_results",
                    [
                        "--input",
                        inputs,
                        "--predictions",
                        predictions,
                        "--evaluation",
                        destination / "evaluation.jsonl",
                        "--output",
                        destination,
                    ],
                    [destination / "metrics.json", destination / "comparison.md"],
                )
            )
    return stages
