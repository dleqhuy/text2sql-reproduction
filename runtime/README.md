# Canonical standalone runtime

Edit shared fork infrastructure here, then run from the orchestrator root:

```bash
uv run python -m scripts.sync_runtime --write
uv run python -m scripts.sync_runtime
```

The sync copies Python/JSON files under this directory to the same relative paths in all three method forks. It checks every destination before writing and refuses to overwrite divergent uncommitted runtime edits. Commit and push fork changes before updating parent gitlinks.

- `reproduction/`: provider, config, contracts, I/O, provenance, checkpoint/resume, SQL guard, schema utilities and CLI runner. `run.py` calls the method-owned `create_method(llm, args, inputs, manifest)`.
- `reproduction_tests/test_runtime.py`: standalone transport/CLI/resume tests shared by all forks.

These are source templates, not a new installed package. Each fork owns a committed copy and runs independently. Method implementation, prompts, retrieval, assets and method dependency locks stay in the fork. The orchestrator's own Vanilla/experiment infrastructure stays under `scripts/common/`.
