# Shared runtime: edit runtime/ in text2sql-reproduction, then run scripts.sync_runtime.
"""Run this method directly from its fork, with checkpointed JSONL output."""

import argparse
import contextlib
import time
from datetime import datetime
from pathlib import Path

from reproduction.config import credentials, load_config
from reproduction.contracts import failure, validate_inputs, validate_predictions
from reproduction.io import db_path, digest, file_hash, read_json, read_jsonl, write_json
from reproduction.llm import LLM, BudgetExceeded, ProviderFailure, set_default_provider
from reproduction.method import METHOD, create_method
from reproduction.provenance import code_provenance
from reproduction.run_store import RunStore
from reproduction.schema import load_schemas


def run(args):
    config, creds = load_config(args.config), credentials(args.env_file)
    inputs = read_jsonl(args.input)
    load_schemas(args.tables)
    validate_inputs(inputs)
    hashes = {row["db_id"]: file_hash(db_path(args.db_root, row["db_id"])) for row in inputs}
    manifest = read_json(args.manifest) if args.manifest else None
    if manifest:
        if digest(inputs) not in {manifest["input_hash"], manifest["smoke_input_hash"]}:
            raise ValueError("Input differs from frozen manifest")
        if any(hashes[k] != manifest["database_hashes"][k] for k in hashes):
            raise ValueError("Database differs from frozen manifest")
        if file_hash(args.tables) not in {
            manifest["source_hashes"]["tables.json"],
            manifest.get("prepared_tables_hash"),
        }:
            raise ValueError("Tables differ from frozen manifest")
    provenance = code_provenance()
    context = read_json(args.context) if args.context else None
    identity = {
        "method": METHOD,
        "model": creds.model,
        "config": config,
        "endpoint_hash": digest(creds.base_url),
        "input_hash": digest(inputs),
        "tables_hash": file_hash(args.tables),
        "database_hashes": hashes,
        "manifest_hash": digest(manifest) if manifest else None,
        "upstream": provenance["root"],
        "code_hash": provenance["code_hash"],
        "dependencies_hash": digest(provenance["dependencies"]),
        "orchestrator": context,
    }
    if context:
        identity["experiment"] = context.get("experiment")
        provenance["orchestrator"] = context
    if METHOD == "dail_sql":
        if not args.dail_prompts:
            raise ValueError("DAIL requires --dail-prompts from reproduction.prepare")
        identity["dail_bundle_hash"] = file_hash(args.dail_prompts)
    store = RunStore(args.run_dir, identity, inputs, args.resume)
    try:
        write_json(Path(args.run_dir) / "provenance.json", provenance)
        validate_predictions(list(store.rows.values()), inputs, require_complete=False)
        started = datetime.fromisoformat(store.meta["created_at"]).timestamp()

        def allowed():
            return (
                store.request_count < config["max_run_calls"]
                and time.time() - started < config["max_run_seconds"]
            )

        llm = LLM(creds, config, store.event, allowed)
        set_default_provider(llm)
        with (
            (Path(args.run_dir) / "stdout.log").open("a") as stdout,
            (Path(args.run_dir) / "stderr.log").open("a") as stderr,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            method = create_method(llm, args, inputs, manifest)
            for row in inputs:
                if row["example_id"] in store.rows:
                    continue
                store.current_id = row["example_id"]
                llm.reset()
                start = time.monotonic()
                result = failure(row, METHOD, creds.model, "method_error", "Method failed")
                try:
                    if not allowed():
                        raise BudgetExceeded()
                    sql = method.infer(row)
                    if llm.budget_exhausted:
                        raise BudgetExceeded()
                    result.update(predicted_sql=sql, status="ok", error=None)
                except BudgetExceeded:
                    result.update(
                        status="budget_exceeded",
                        error={
                            "type": "budget_exceeded",
                            "stage": "inference",
                            "message": "Run budget exhausted",
                        },
                    )
                except ProviderFailure as exc:
                    result.update(
                        status=exc.kind,
                        error={
                            "type": exc.kind,
                            "stage": "provider",
                            "message": "Provider request failed",
                        },
                    )
                except (ValueError, IndexError, KeyError) as exc:
                    result.update(
                        status="parse_error",
                        error={
                            "type": type(exc).__name__,
                            "stage": "method",
                            "message": "Method output could not be parsed",
                        },
                    )
                except Exception as exc:
                    result["error"]["type"] = type(exc).__name__
                result.update(latency_ms=(time.monotonic() - start) * 1000, **llm.measurements())
                if METHOD == "dail_sql":
                    result["variant"] = method.variant
                validate_predictions([result], [row])
                store.save(result)
        validate_predictions(list(store.rows.values()), inputs)
        store.finish("completed")
    except BaseException:
        store.finish("interrupted")
        raise
    finally:
        store.close()
    print(
        f"Finished {METHOD}: {sum(r['status'] == 'ok' for r in store.rows.values())}/{len(inputs)} SQL outputs; {args.run_dir}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("input", "tables", "db-root", "run-dir"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--context",
        type=Path,
        help="Optional verified orchestrator metadata; contains no credentials",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dail-prompts", type=Path)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
