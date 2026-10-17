# Experiment Protocol — Spider 1.0

Implementation defaults (2026-10-17): main N=100, smoke N=10, seed=42, DB-balanced round-robin sampling with original-order output. No difficulty labels are fabricated. Runtime config: `configs/experiment.json`. A real manifest is frozen only after data preparation.

Provider config: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; Chat Completions probe passed. Temperature=0, request timeout=90s, max attempts=3, run call cap=1000, wall-time cap=14400s, SQL timeout=5s. Stage output caps: Vanilla/MAC=1024 default, DIN generation=600/correction=350, DAIL=200. Disclose these method differences in comparisons.

Primary metric: **official Test Suite execution accuracy**, using 695 original/generated SQLite files across the 20 selected DBs, plug_value=false, keep_distinct=true, seed=42. `execution` on original DBs and `legacy` are separate reference metrics. Synthetic scores are not benchmark scores. See [current status](implementation/status.md).

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

Protocol note: main-100 includes the smoke 10 used to harden output parsing; it is not an independent holdout. Runs overlapped in time, so recorded latency is descriptive, not an isolated throughput benchmark. DAIL totals include preliminary + final generation, exclude offline linking/retrieval setup, and use no self-consistency. No token prices were assumed.
