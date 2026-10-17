# Vanilla Text-to-SQL — Baseline Runbook

**Source:** team-owned baseline; no upstream paper repository.

## Intended pipeline
Spider question + database schema -> OpenAI model -> SQL -> SQLite validation -> normalized JSONL.

## Code to create
- `scripts/run_vanilla.py`: read fixed Spider subset, construct schema prompt, call OpenAI API, extract SQL, log output.
- `scripts/prepare_spider.py`: preserve question, db_id and stable example ID.
- `.env`: `OPENAI_API_KEY` and `OPENAI_MODEL` (never commit).

## Checks
- [ ] Model receives no dev gold SQL.
- [ ] Schema includes actual tables, columns, primary/foreign keys as needed.
- [ ] Generated SQL is logged before execution.
- [ ] SQLite evaluation runs read-only with timeout.
- [ ] Same IDs, model settings and retry policy as other methods.

## Run command
**TODO after implementation:** document exact tested command, args, output path and example logs. Do not treat this plan as executable code.

## uv and Ruff

Implement the baseline in the root `scripts/` directory. Use `uv sync` to install project tooling, `uv run python scripts/run_vanilla.py ...` once the script exists, and `uv run ruff format scripts/` / `uv run ruff check scripts/` before committing.
