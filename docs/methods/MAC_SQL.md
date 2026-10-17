# MAC-SQL — Clone/Configure/Run Guide

**Upstream:** https://github.com/wbbeyourself/MAC-SQL  
**Paper:** https://arxiv.org/abs/2312.11242

## Reproduction target
Run the GPT/API-based multi-agent inference path on the fixed Spider dev subset, retaining Selector, Decomposer and Refiner roles and execution-feedback correction. **Do not choose a fine-tuning workflow.**

## Clone
```bash
git clone https://github.com/wbbeyourself/MAC-SQL third_party/MAC-SQL
git -C third_party/MAC-SQL rev-parse HEAD
```

## Audit: fill after reading the cloned code
| Question | Verified answer |
|---|---|
| Upstream commit | TODO |
| Python/dependency requirements | TODO |
| GPT/API-based inference entry script + exact CLI | TODO |
| API key location (`file:line`) | TODO |
| Model name location (`file:line`) | TODO |
| OpenAI SDK/API call (`file:line`) | TODO |
| Selector/Decomposer/Refiner definitions (`file:line`) | TODO |
| SQLite execution/refinement and loop limits (`file:line`) | TODO |
| Spider input and prediction output format | TODO |
| Minimal patch + patch file | TODO |
| Tested 1 / 10 / 100+ examples | TODO |

## Search likely integration points
```bash
grep -RInE 'OPENAI_API_KEY|api_key|ChatCompletion|Completion\.create|chat\.completions|model=|gpt-' third_party/MAC-SQL --include='*.py' --include='*.sh' | head -100
grep -RInE 'Selector|Decomposer|Refiner|sqlite|execute|retry|spider|prediction' third_party/MAC-SQL --include='*.py' | head -100
```

## Expected run workflow
1. Identify the official GPT inference path, not optional fine-tuning scripts.
2. Set up a separate Python environment; check SDK version compatibility.
3. Configure Spider paths, API key, model, retry/agent iteration limits.
4. Test one question with **read-only** SQLite and log agent steps.
5. Run fixed 10, then 100–200 dev IDs; normalize final SQL and errors.
6. Evaluate on shared Spider evaluator; record latency and API calls.

**Exact inference command:** TODO — verify in cloned repo first.

## Reproduction fidelity checklist
- [ ] Selector, Decomposer, Refiner remain present.
- [ ] Execution feedback/refinement is preserved or deviations documented.
- [ ] Generated SQL executes only on read-only DB copies.
- [ ] Same model and dev IDs as other methods.

## uv environment and Ruff rules

Use `uv` instead of `pip`/`venv` for this upstream repository. Check its README and supported Python version before choosing `--python`. From the project root:

```bash
uv venv third_party/REPO_NAME/.venv --python 3.10
uv pip install --python third_party/REPO_NAME/.venv/bin/python -r third_party/REPO_NAME/requirements.txt
```

**Replace `REPO_NAME` with the actual clone folder.** The requirements command is applicable only if the file exists; otherwise follow the verified upstream setup. Run upstream inference using that repository's `.venv/bin/python` and verified entry point. Do not run `ruff format` across cloned upstream source. Format team-owned adapters with `uv run ruff format scripts/` and lint with `uv run ruff check scripts/`.
