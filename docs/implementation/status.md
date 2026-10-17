# Trạng thái implementation — 17/10/2026

Đã hoàn thành implementation, smoke và benchmark 100 câu cho cả bốn method trên máy hiện tại. Đầu ra: [benchmark](../../reports/benchmark_100.md), [metrics JSON](../../reports/comparison.json), [runbook](../reproducibility.md).

| Phase | Kết quả đã kiểm chứng |
|---|---|
| 0 | Config/env loader LLM_*, contracts, Python 3.11, uv.lock, Ruff và Git ignore |
| 1 | Pin source DAIL/DIN/MAC, Spider và official test-suite evaluator; môi trường upstream riêng và audit adaptations |
| 2 | Provider probe thật; train/dev + 166 DB; main 100/smoke 10 seed 42; gold separation, SQL guard, checkpoint/resume; 695 suite SQLite files cho 20 DB |
| 3 | Bốn method chạy endpoint thật; DAIL dùng CoreNLP + MPNet thật và hai lượt retrieval/inference; DIN/MAC dùng stages/classes gốc qua adapters |
| 4 | Official Test Suite và original-DB evaluation đủ 100 câu/method; DAIL cộng accounting hai lượt; comparison JSON và tám error case studies |

## Benchmark đã hoàn thành

| Method | Test Suite đúng/100 | DB gốc đúng/100 | SQL valid/100 | API requests |
|---|---:|---:|---:|---:|
| Vanilla | 69 | 81 | 100 | 100 |
| DAIL-SQL | 76 | 87 | 100 | 200 |
| DIN-SQL | 78 | 86 | 96 | 400 |
| MAC-SQL | 73 | 86 | 100 | 125 |

Runs: `runs/spider-v1-main-{vanilla,dail,din,mac}/`; DAIL aggregate tham chiếu hai parent runs preliminary/final. Mẫu số luôn 100; bốn output DIN lỗi format được giữ nguyên và tính sai, không sửa predictions sau khi chấm.

31 tests pass, bao phủ contracts, retry/usage, resume, SQL guard, official comparison engine, parsers, DAIL accounting và cache cell-link tương đương source. Lệnh kiểm tra Ruff/format/tests ở runbook.

## Giới hạn nghiệm thu

- Đây là adapted reproduction trên subset 100 câu/20 DB, không phải full-dev hoặc điểm paper. Smoke thuộc main và đã dùng để sửa compatibility handling.
- Chưa chạy cold setup trên máy/platform khác; khả năng tái lập độc lập vẫn cần xác nhận.
- Latency có run chồng lấp; DAIL chưa tính preprocessing/retrieval offline. Không suy ra chi phí tiền từ token usage.
- Không bổ sung per-run source snapshot/diff theo yêu cầu người dùng; giữ source pins, provenance hashes và logs hiện có.

Lịch sử fixture/smoke và hạn chế legacy evaluator ở [smoke report](../../reports/spider_smoke.md). Kết quả chính dùng official engine hỗ trợ backticks.
