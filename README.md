# Text-to-SQL Reproduction

Chạy inference Vanilla, DAIL-SQL, DIN-SQL và MAC-SQL trên Spider 1.0 bằng cùng model OpenAI Compatible; không training. Mỗi method fork tự gọi API và chạy độc lập; repo chính điều phối các CLI và chấm điểm. Ba forks và hai evaluator được ghim bằng Git submodules.

## Bắt đầu

```bash
git clone --recurse-submodules https://github.com/dleqhuy/text2sql-reproduction.git
cd text2sql-reproduction
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python -m scripts.bootstrap_upstream
cp -n .env.example .env
```

Điền `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` trong `.env`. Nếu đã có file này, giữ nguyên cấu hình. Tiếp tục theo [runbook](docs/reproducibility.md) để tải dữ liệu, dựng môi trường từng method và chạy inference/evaluation.

## Tài liệu

| Cần làm gì | Tài liệu |
|---|---|
| Cài đặt và chạy lại | [Runbook](docs/reproducibility.md) |
| Sửa fork, trace diff, tạo experiment manifest | [Repository workflow](docs/repository_workflow.md) |
| Hiểu các method và adaptations | [Method audit](docs/repo_audit.md) |
| Tải Spider và chuẩn bị subset | [Dataset](docs/spider_dataset.md) |
| Hiểu protocol và metrics | [Experiment protocol](docs/experiment_protocol.md) |
| Đọc input/output, checkpoints và metadata | [Contracts](docs/contracts.md) |

## Kết quả

[Benchmark 100 câu](reports/benchmark_native_100_20261017.md) và [comparison JSON](reports/comparison_native_100_20261017.json) ghi kết quả của bốn method trên cùng subset cố định 100 câu/20 DB, cùng model và 695 official test-suite SQLite files. Đây là adapted reproduction; không phải full Spider dev hoặc điểm paper gốc.

[Completed record](experiments/completed/native-main-100-20261017.json) ghi hashes của artifacts; các [prepared manifests](experiments/README.md) chỉ mô tả cấu hình, tự chúng chưa chứng minh inference đã chạy. Phạm vi kiểm chứng và giới hạn ở [experiment protocol](docs/experiment_protocol.md).

## Cấu trúc

- `scripts/`, `tests/`: orchestration, evaluation và kiểm tra chung.
- `third_party/`: ba method forks và hai evaluator submodules.
- `configs/`, `data/splits/`: cấu hình, nguồn/hash dữ liệu và fixed dataset manifest. Dependency locks của methods nằm trong từng fork.
- `experiments/`: prepared manifests và completed records.
- `docs/`, `reports/`: hướng dẫn và kết quả.
- `data/spider/`, `data/assets/`, `data/prepared/`, `data/test-suite/`, `runs/`: dữ liệu/artifacts local, Git ignore.
