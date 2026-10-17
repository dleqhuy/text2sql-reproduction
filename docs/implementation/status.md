# Phạm vi đã kiểm chứng

## Implementation hiện tại

Runtime OpenAI Compatible, bốn method adapters, checkpoint/resume, SQL read-only/timeout và official Test Suite evaluation đã hoạt động trên Python 3.11.16/macOS arm64. [Benchmark 100 câu](../../reports/benchmark_100.md) giữ kết quả và giới hạn của experiment trước migration.

39 tests đã pass: contracts, retry/usage, resume, evaluator counterexamples, parsers, DAIL accounting/cell-link cache, gitlink mismatch và manifest source/config/data/model validation. Root tooling và integration files trong forks đạt Ruff/format. Lệnh kiểm tra ở [runbook](../reproducibility.md).

## Fork/submodule migration

Đã clone mới từ GitHub với đủ năm submodules; bootstrap và manifest verification pass sau khi cung cấp dataset manifest/smoke inputs ignored. DAIL tạo lại 10 preliminary prompts bằng weights/cache thật, khớp prompts và selected train indices trước migration. Production preflight pass mà không gọi provider; 846 artifacts cũ được kiểm tra hash trước khi dọn tài liệu.

## Giới hạn

- Cold setup toàn bộ dependencies/assets trên máy khác chưa được kiểm chứng; source-clone test dùng Python environment hiện có.
- Benchmark chỉ gồm 100 câu/20 DB; smoke nằm trong main và đã dùng để sửa compatibility handling.
- Run latency có chồng lấp; DAIL chưa gồm preprocessing/retrieval offline. Không suy ra chi phí tiền từ token usage.
- Prepared manifests không chứng minh experiment mới đã chạy. Xem [workflow](../repository_workflow.md) và [historical manifest](../../experiments/historical/spider-v1-main-100.json).
