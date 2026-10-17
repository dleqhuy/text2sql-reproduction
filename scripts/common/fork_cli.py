"""Launch a pinned fork's native CLI without importing or patching its pipeline."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.common.io import ROOT
from scripts.common.sources import source_path

PATH_FLAGS = {
    "--repo",
    "--input",
    "--tables",
    "--db-root",
    "--run-dir",
    "--manifest",
    "--config",
    "--env-file",
    "--context",
    "--dail-prompts",
    "--dataset",
    "--preliminary",
    "--output",
    "--embedding-config",
}


def invoke(name, module, arguments):
    repo = source_path(name)
    python = repo / ".venv/bin/python"
    if not python.exists():
        python = Path(sys.executable)
    arguments = list(arguments)
    for index, argument in enumerate(arguments):
        flag, separator, value = argument.partition("=")
        if flag not in PATH_FLAGS:
            continue
        if separator:
            arguments[index] = flag + "=" + str(Path(value).resolve())
        elif index + 1 < len(arguments):
            arguments[index + 1] = str(Path(arguments[index + 1]).resolve())
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.setdefault("NLTK_DATA", str(ROOT / "data/nltk_data"))
    env.setdefault("DAIL_EMBEDDING_CACHE", str(ROOT / "data/assets/embeddings"))
    env.setdefault("HF_HOME", str(ROOT / "data/assets/huggingface"))
    env.setdefault("TRANSFORMERS_CACHE", str(ROOT / "data/assets/huggingface/transformers"))
    subprocess.run([str(python), "-m", module, *arguments], cwd=repo, env=env, check=True)


def run_method(args, identity, provenance):
    arguments = []
    for key in ("input", "tables", "db_root", "run_dir", "manifest"):
        arguments.extend(["--" + key.replace("_", "-"), str(getattr(args, key))])
    arguments.extend(["--config", str(args.config or ROOT / "configs/experiment.json")])
    if (ROOT / ".env").exists():
        arguments.extend(["--env-file", str(ROOT / ".env")])
    if args.resume:
        arguments.append("--resume")
    if args.method == "dail_sql":
        arguments.extend(["--dail-prompts", str(args.dail_prompts)])
    # This carries only validated identity/provenance, never env or API credentials.
    with tempfile.TemporaryDirectory(prefix="text2sql-fork-") as folder:
        context = Path(folder) / "context.json"
        context.write_text(
            json.dumps(
                {
                    "identity": identity,
                    "root": provenance["root"],
                    "experiment": identity.get("experiment"),
                }
            )
        )
        arguments.extend(["--context", str(context)])
        invoke(args.method, "reproduction.run", arguments)
