# DAIL-SQL — Clone/Configure/Run Guide

**Upstream:** https://github.com/BeachWang/DAIL-SQL  
**Paper:** https://arxiv.org/abs/2308.15363

## Reproduction target
Preserve the original demonstration-selection / prompt-organization strategy, then generate SQL with an OpenAI API model on the fixed Spider dev subset. Train split may supply few-shot examples; no model fine-tuning.

## Clone
```bash
git clone https://github.com/BeachWang/DAIL-SQL third_party/DAIL-SQL
git -C third_party/DAIL-SQL rev-parse HEAD
```

## Audit: fill after reading the cloned code
| Question | Verified answer |
|---|---|
| Upstream commit | TODO |
| Python/dependency requirements | TODO |
| Inference entry script + exact CLI | TODO |
| API key location (`file:line`) | TODO |
| Model name location (`file:line`) | TODO |
| OpenAI SDK/API call (`file:line`) | TODO |
| Spider preprocessing/embedding dependencies | TODO |
| Input and output format | TODO |
| Minimal patch + patch file | TODO |
| Tested 1 / 10 / 100+ examples | TODO |

## Search likely integration points
```bash
grep -RInE 'OPENAI_API_KEY|api_key|ChatCompletion|Completion\.create|chat\.completions|model=|gpt-' third_party/DAIL-SQL --include='*.py' --include='*.sh' | head -100
grep -RInE 'argparse|__main__|spider|dev.json|train_spider|prediction|output' third_party/DAIL-SQL --include='*.py' --include='*.sh' | head -100
```

## Expected run workflow
1. Install upstream dependencies in an isolated environment.
2. Run required Spider preprocessing and demonstration retrieval setup as instructed upstream.
3. Locate and configure OpenAI key/model; migrate SDK calls only if required.
4. Test one dev question; inspect selected examples and final SQL.
5. Run fixed 10 and then fixed 100–200 Spider dev examples.
6. Convert output to common JSONL; evaluate with shared Spider evaluator.

**Exact inference command:** TODO — must be copied from verified upstream README/source, not guessed.

## Reproduction fidelity checklist
- [ ] Few-shot examples do not come from Spider dev gold SQL.
- [ ] Original demonstration selection is preserved or deviations explicitly named.
- [ ] Same model and dev IDs as other methods.
- [ ] API usage, latency and failure rows recorded.

## uv environment and Ruff rules

Use `uv` instead of `pip`/`venv` for this upstream repository. Check its README and supported Python version before choosing `--python`. From the project root:

```bash
uv venv third_party/REPO_NAME/.venv --python 3.10
uv pip install --python third_party/REPO_NAME/.venv/bin/python -r third_party/REPO_NAME/requirements.txt
```

**Replace `REPO_NAME` with the actual clone folder.** The requirements command is applicable only if the file exists; otherwise follow the verified upstream setup. Run upstream inference using that repository's `.venv/bin/python` and verified entry point. Do not run `ruff format` across cloned upstream source. Format team-owned adapters with `uv run ruff format scripts/` and lint with `uv run ruff check scripts/`.
