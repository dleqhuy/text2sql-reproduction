# DIN-SQL — Clone/Configure/Run Guide

**Upstream:** https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting  
**Paper:** https://arxiv.org/abs/2304.11015

## Reproduction target
Run the authors' decomposed prompting pipeline on the fixed Spider dev subset: schema linking, question classification/decomposition, SQL generation, and self-correction as supported by the repository. No training.

## Clone
```bash
git clone https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting third_party/Few-shot-NL2SQL-with-prompting
git -C third_party/Few-shot-NL2SQL-with-prompting rev-parse HEAD
```

## Audit: fill after reading the cloned code
| Question | Verified answer |
|---|---|
| Upstream commit | TODO |
| Python/dependency requirements | TODO |
| Inference entry script / notebook + exact command | TODO |
| API key location (`file:line`) | TODO |
| Model name location (`file:line`) | TODO |
| OpenAI SDK/API call (`file:line`) | TODO |
| Prompt templates and pipeline stages (`file:line`) | TODO |
| Spider input and prediction output format | TODO |
| Minimal patch + patch file | TODO |
| Tested 1 / 10 / 100+ examples | TODO |

## Search likely integration points
```bash
grep -RInE 'OPENAI_API_KEY|api_key|ChatCompletion|Completion\.create|chat\.completions|model=|gpt-' third_party/Few-shot-NL2SQL-with-prompting --include='*.py' --include='*.ipynb' | head -100
grep -RInE 'schema.link|classif|decompos|self.correct|correction|prediction' third_party/Few-shot-NL2SQL-with-prompting --include='*.py' --include='*.ipynb' | head -100
```

## Expected run workflow
1. Identify whether entry point is script or notebook; preserve original prompts/stages.
2. Configure Spider file paths, model, API key and SDK compatibility.
3. Run one question and record each intermediate stage plus final SQL.
4. Run fixed 10, then 100–200 dev IDs; collect final SQL and failures.
5. Normalize and evaluate with the shared Spider evaluator.

**Exact inference command:** TODO — verify in cloned repo first.

## Reproduction fidelity checklist
- [ ] No stage silently skipped for convenience.
- [ ] Intermediate outputs are logged where possible.
- [ ] Any changed model/prompt is documented.
- [ ] Same model and dev IDs as other methods.

## uv environment and Ruff rules

Use `uv` instead of `pip`/`venv` for this upstream repository. Check its README and supported Python version before choosing `--python`. From the project root:

```bash
uv venv third_party/REPO_NAME/.venv --python 3.10
uv pip install --python third_party/REPO_NAME/.venv/bin/python -r third_party/REPO_NAME/requirements.txt
```

**Replace `REPO_NAME` with the actual clone folder.** The requirements command is applicable only if the file exists; otherwise follow the verified upstream setup. Run upstream inference using that repository's `.venv/bin/python` and verified entry point. Do not run `ruff format` across cloned upstream source. Format team-owned adapters with `uv run ruff format scripts/` and lint with `uv run ruff check scripts/`.
