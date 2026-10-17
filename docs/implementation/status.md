# Phạm vi đã kiểm chứng

## Implementation hiện tại

Ba standalone forks dùng native OpenAI Compatible clients; repo chính gọi CLI bằng subprocess. Checkpoint/resume, SQL read-only/timeout và official Test Suite evaluation đã hoạt động trên Python 3.11.16/macOS arm64. [Benchmark native CLI 100 câu](../../reports/benchmark_native_100_20261017.md) ghi lượt chạy mới sau migration; [benchmark cũ](../../reports/benchmark_100.md) giữ nguyên kết quả trước migration.

45 tests đã pass: contracts, retry/usage, resume, evaluator counterexamples, parsers, DAIL accounting/cell-link cache, gitlink mismatch và manifest source/config/data/model validation. Root tooling và integration files trong forks đạt Ruff/format. Lệnh kiểm tra ở [runbook](../reproducibility.md).

## Fork/submodule migration

Đã clone mới từ GitHub với đủ năm submodules; bootstrap và manifest verification pass sau khi cung cấp dataset manifest/smoke inputs ignored. DAIL tạo lại 10 preliminary prompts bằng weights/cache thật, khớp prompts và selected train indices trước migration. Production preflight pass mà không gọi provider; 846 artifacts cũ được kiểm tra hash trước khi dọn tài liệu.

Lượt benchmark native ngày 17/10/2026 chạy lại 100 IDs bằng API thật, source/config/data khóa trong manifest, inference tuần tự: Vanilla, DIN, MAC, DAIL preliminary và final. DAIL prompts được tạo lại ở cả hai bước; accounting cộng cả hai lượt. [Completed record](../../experiments/completed/native-main-100-20261017.json) giữ hashes của artifacts. DIN có một lỗi classification format tại `dev_000507`, vẫn tính trong mẫu số; không sửa parser hoặc chạy chọn lọc lại giữa experiment.

## Giới hạn

- Cold setup toàn bộ dependencies/assets trên máy khác chưa được kiểm chứng; source-clone test dùng Python environment hiện có.
- Benchmark chỉ gồm 100 câu/20 DB; smoke nằm trong main và đã dùng để sửa compatibility handling.
- Các run benchmark cũ có latency chồng lấp; lượt native mới chạy inference tuần tự. DAIL chưa gồm preprocessing/retrieval offline. Không suy ra chi phí tiền từ token usage.
- Prepared manifests không chứng minh experiment mới đã chạy. Xem [workflow](../repository_workflow.md) và [historical manifest](../../experiments/historical/spider-v1-main-100.json).

Standalone validation: 7 fork unit tests trên fresh GitHub clones, local HTTP provider/CLI/resume, DIN prompt preservation và MAC refinement; không import parent runtime. DAIL asset jars/model files đã verify và preliminary và final prompts/retrieval đều khớp 10/10 trước migration. Chi tiết và trình tự ở [migration plan](../standalone_migration.md). Kiểm tra dùng environments hiện có, chưa phải cold dependency setup trên máy khác.
