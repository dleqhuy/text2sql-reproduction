"""Validate benchmark assets and execute checkpointed stages."""

import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from scripts.common.config import credentials, load_config
from scripts.common.contracts import validate_inputs
from scripts.common.experiment import referenced_path, validate_run
from scripts.common.io import ROOT, db_path, digest, file_hash, read_json, read_jsonl, write_json


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


def preflight(experiment, dataset, suite, embedding, manifest):
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

    return inputs, identity
