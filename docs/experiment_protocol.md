# Experiment Protocol — Spider 1.0

- Use Spider **train** only for few-shot demonstrations if the original method needs them.
- Use the same fixed Spider **dev** examples for all methods (10 smoke-test, 100–200 final).
- Keep `db_id`, question and SQLite database version identical.
- Freeze model ID, temperature, token budget, retry policy and timeout where technically possible.
- Record method-specific additional settings (retrieval top-k, agent steps, prompt variants).
- Use official Spider 1.0 execution evaluator, documenting the exact evaluator version and options.
- Count missing predictions, timeouts and API failures as incorrect in overall EX.
- Never execute untrusted generated SQL with write access.
- Save one output row for every selected example, including failures.
- Do not report subset scores as full Spider dev scores or claim reproduction of original paper numbers.

Environment reproducibility: team-owned tooling uses root `uv.lock`; upstream repositories use isolated uv-managed `.venv` environments. Log Python/package versions per method. Ruff formats and lints team-owned scripts only.
