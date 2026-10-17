# Vanilla baseline — implemented

Team-owned, không phải paper reproduction. `scripts/common/methods.py:Vanilla` tạo prompt từ question + tên bảng/cột/types/PK/FK. Một generation response mỗi câu; transport retries được đếm riêng. Không retrieval hoặc correction bằng execution feedback. SQL guard/evaluator chạy sau generation.

CLI từ root: `uv run python -m scripts.run_vanilla --help`. Required flags: `--input`, `--manifest`, `--tables`, `--db-root`, `--run-dir`. Optional `--config`, `--resume`. Đọc `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, ưu tiên biến shell.

Lệnh đầy đủ ở [runbook](../reproducibility.md). Đã chạy real provider fixture vào `runs/fixture-v3-vanilla`; SQL hợp lệ và legacy evaluator chấm đúng 1/1 câu tổng hợp. Sau đó đã chạy smoke 10 Spider thật; kết quả tại [smoke report](../../reports/spider_smoke.md). Main 100 đã hoàn thành; xem [benchmark report](../../reports/benchmark_100.md).

Artifacts gồm prompt/raw response trong events, checkpoint, normalized predictions, code/data/config fingerprints, usage và lỗi. Output không parse được thành failure row; không tự sửa SQL. Cùng manifest/model với các method khác khi benchmark.
