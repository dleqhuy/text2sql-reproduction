# Text-to-SQL Reproduction

So sánh Vanilla, DAIL-SQL, DIN-SQL và MAC-SQL trên Spider 1.0 bằng cùng model OpenAI Compatible; không training. Repo chính điều phối ba method forks qua native CLI và chấm bằng official `test-suite-sql-eval`.

```text
repo chính → Vanilla / ba fork → predictions → evaluator chung → báo cáo
```

## Bắt đầu

```bash
git clone --recurse-submodules https://github.com/dleqhuy/text2sql-reproduction.git
cd text2sql-reproduction
uv sync --locked
uv run python -m scripts.bootstrap_upstream
cp -n .env.example .env
```

Điền `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` trong `.env`. Theo [running](docs/running.md) để dựng environments/dữ liệu, rồi chạy với manifest đã chuẩn bị cho revision hiện tại:

```bash
uv run python -m scripts.benchmark --experiment-manifest experiments/manifests/main-v2.json --run-dir runs/my-benchmark
```

## Tài liệu

- [Running](docs/running.md): setup, dữ liệu, benchmark, resume và chấm lại.
- [Methods](docs/methods.md): pipelines, adaptations, protocol và giới hạn.
- [Development](docs/development.md): Git/submodules, trace diff, manifests, contracts và tests.

## Kết quả hiện tại

100 câu/20 DB, model `cx/gpt-6-luna`; 695 official test-suite SQLite files.

| Method | Test Suite Accuracy | Execution Accuracy — DB gốc |
|---|---:|---:|
| Vanilla | 64% | 77% |
| DAIL-SQL | 74% | 85% |
| DIN-SQL | 78% | 87% |
| MAC-SQL | 67% | 83% |

[Báo cáo](reports/benchmark_native_100_20261017.md) · [Metrics JSON](reports/comparison_native_100_20261017.json) · [Completed record](experiments/completed/native-main-100-20261017.json). Đây là adapted reproduction trên subset, không phải full Spider dev hoặc điểm paper gốc.

## Cấu trúc

- `scripts/`, `tests/`: điều phối, chấm điểm và kiểm thử.
- `third_party/`: ba method forks và hai evaluator, ghim bằng Git submodules.
- `configs/`, `data/splits/`, `experiments/`: cấu hình, data hashes và experiment records.
- `docs/`, `reports/`: hướng dẫn và kết quả.
- `data/`, `runs/`, `.venv/`: dữ liệu/assets, artifacts và environments local được Git ignore; `data/splits/` được theo dõi.
