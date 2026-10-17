"""Run all four methods, both DAIL stages, evaluation and reporting sequentially."""

import argparse
import fcntl
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from scripts.common.config import credentials, load_config
from scripts.common.contracts import validate_inputs
from scripts.common.experiment import referenced_path, validate_run
from scripts.common.io import (
    ROOT,
    atomic_text,
    db_path,
    digest,
    file_hash,
    read_json,
    read_jsonl,
    write_json,
)


@dataclass
class Stage:
    name: str
    module: str
    arguments: list
    outputs: list


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


def fingerprints(paths):
    files = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file() and p.name != ".lock")
        else:
            files.append(path)
    if not files:
        raise ValueError("Stage did not produce artifacts")
    return {str(p.resolve()): file_hash(p) for p in files}


def execute(stages, output, identity, manifest, resume=False, invoke=None, finish=None):
    if output.exists() and any(output.iterdir()) and not resume:
        raise ValueError("Benchmark directory exists; use --resume or a new --run-dir")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record_path = output / "benchmark.json"
        if resume:
            record = read_json(record_path)
            if record["identity"] != identity:
                raise ValueError("Benchmark resume identity mismatch")
            for hashes in record["completed_stages"].values():
                for path, expected in hashes.items():
                    if file_hash(path) != expected:
                        raise ValueError("Completed benchmark artifacts changed")
        else:
            record = {"identity": identity, "status": "running", "completed_stages": {}}
        record["status"] = "running"
        write_json(record_path, record)
        invoke = invoke or subprocess.run
        env = {**os.environ, "TOKENIZERS_PARALLELISM": "false"}
        try:
            for stage in stages:
                if stage.name in record["completed_stages"]:
                    print(f"Verified completed stage: {stage.name}", flush=True)
                    continue
                args = list(stage.arguments)
                if stage.module == "scripts.aggregate_dail" and stage.outputs[0].exists():
                    # Rebuild derived output if interrupted before its stage checkpoint.
                    shutil.rmtree(stage.outputs[0])
                if stage.module == "scripts.run_method":
                    args += ["--experiment-manifest", manifest]
                    if (stage.outputs[0] / "run_config.json").exists():
                        args.append("--resume")
                print(f"Running {stage.name}", flush=True)
                invoke(
                    [sys.executable, "-m", stage.module, *map(str, args)],
                    cwd=ROOT,
                    env=env,
                    check=True,
                )
                record["completed_stages"][stage.name] = fingerprints(stage.outputs)
                write_json(record_path, record)
            if finish:
                record["completed_stages"]["report"] = fingerprints(finish())
            record["status"] = "completed"
            write_json(record_path, record)
        except BaseException:
            record["status"] = "interrupted"
            write_json(record_path, record)
            raise


def report(output, inputs, experiment_hash):
    results = []
    for method, folder in [
        ("Vanilla", "vanilla"),
        ("DAIL-SQL", "dail"),
        ("DIN-SQL", "din"),
        ("MAC-SQL", "mac"),
    ]:
        run = output / folder
        metrics = [read_json(run / f"eval-{m}/metrics.json") for m in ("test-suite", "execution")]
        for metric, expected in zip(
            metrics,
            ["test_suite_execution_accuracy", "single_database_execution_accuracy"],
            strict=True,
        ):
            provenance = metric["evaluation_provenance"]
            if (
                metric["metric"] != expected
                or metric["method"] != ("vanilla" if folder == "vanilla" else f"{folder}_sql")
                or metric["n"] != len(inputs)
                or provenance["input_hash"] != digest(inputs)
                or provenance["prediction_hash"] != file_hash(run / "predictions.jsonl")
            ):
                raise ValueError("Benchmark metrics do not match predictions/input/metric")
        results.append(
            {"method": method, "run": str(run), "test_suite": metrics[0], "execution": metrics[1]}
        )
    if len({m["model"] for r in results for m in (r["test_suite"], r["execution"])}) != 1:
        raise ValueError("Benchmark methods use different models")
    write_json(
        output / "comparison.json",
        {"experiment_hash": experiment_hash, "input_hash": digest(inputs), "results": results},
    )
    lines = [
        "# Benchmark",
        "",
        f"Model: `{results[0]['test_suite']['model']}`; N={len(inputs)}.",
        "",
        "| Method | Test Suite | DB gốc | SQL valid | Requests |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in results:
        m, ex = result["test_suite"], result["execution"]
        lines.append(
            f"| {result['method']} | {m['ex']:.1%} | {ex['ex']:.1%} | "
            f"{m['valid_sql']}/{m['n']} | {m['api_calls']['observed_sum']} |"
        )
    lines += [
        "",
        "Inference chạy tuần tự; DAIL cộng hai lượt, chưa gồm retrieval offline. "
        "Mẫu số gồm cả failures. Token usage/coverage, latency và statuses ở "
        "[comparison.json](comparison.json); stage hashes ở [benchmark.json](benchmark.json).",
        "",
        "Đây là adapted reproduction trên subset; smoke nằm trong main và đã dùng "
        "để sửa output handling. Kết quả không phải full Spider dev hoặc điểm paper gốc.",
        "",
    ]
    atomic_text(output / "report.md", "\n".join(lines))


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
    refs = experiment["files"]
    inputs_path = referenced_path(refs["input"], ROOT)
    dataset_manifest = referenced_path(refs["dataset_manifest"], ROOT)
    config = load_config(referenced_path(refs["config"], ROOT))
    creds = credentials()
    validate_run(
        manifest,
        SimpleNamespace(input=inputs_path, manifest=dataset_manifest),
        creds.model,
        config,
    )
    inputs = read_jsonl(inputs_path)
    validate_inputs(inputs)
    for folder in ("DAIL-SQL", "Few-shot-NL2SQL-with-prompting", "MAC-SQL"):
        if not (ROOT / "third_party" / folder / ".venv/bin/python").is_file():
            raise ValueError(f"Install the isolated environment first: {folder}")
    # Validate all selected suites before paid inference, rather than finding missing DBs later.
    expected = read_json(ROOT / "configs/test_suite_source.json")["database_hashes"]
    for dbid in {r["db_id"] for r in inputs}:
        db_path(dataset / "database", dbid)
        db_path(suite, dbid)
        files = list((suite / dbid).glob("*.sqlite"))
        if (
            len(files) < 2
            or {p.relative_to(suite).as_posix() for p in files}
            != {name for name in expected if Path(name).parent.as_posix() == dbid}
            or any(file_hash(p) != expected[p.relative_to(suite).as_posix()] for p in files)
        ):
            raise ValueError(f"Missing or changed test suite: {dbid}")
    identity = {
        "experiment_hash": file_hash(manifest),
        "endpoint_hash": digest(creds.base_url),
        "dataset": str(dataset),
        "suite": str(suite),
        "embedding_config": str(embedding),
        "embedding_config_hash": file_hash(embedding),
    }

    def finish():
        report(output, inputs, identity["experiment_hash"])
        return [output / "report.md", output / "comparison.json"]

    execute(stages, output, identity, manifest, args.resume, finish=finish)
    print(f"Benchmark complete: {output / 'report.md'}")


if __name__ == "__main__":
    main()
