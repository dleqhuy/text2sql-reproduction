# Experiment protocol — Spider 1.0

## Dữ liệu và model

Fixed main 100 câu trên 20 DB, smoke 10 là tập con, DB-balanced round-robin seed 42 và output theo original dev order. [Dataset manifest](../data/splits/spider-v1.json) ghi IDs/hashes; train chỉ làm demonstrations. Dev gold chỉ dùng evaluation/hardness, không vào prompts hoặc retrieval. Mọi method dùng cùng input, schema/DB và model cấu hình.

[Runtime config](../configs/experiment.json): temperature 0, request timeout 90s, tối đa 3 attempts, 1.000 calls/run, 14.400s/run và SQL timeout 5s. Token caps giữ khác biệt stage: Vanilla/MAC 1024, DIN generation 600/correction 350, DAIL 200/call. DAIL là 9-shot QA hai lượt, không self-consistency.

## Metrics

Primary metric là **official Test Suite execution accuracy**, dùng 695 original/generated SQLite files thuộc 20 DB: `plug_value=false`, `keep_distinct=true`, seed 42. Evaluator commit được ghim bằng submodule; không đổi comparison logic gốc. Gold self-check cả 100 câu đã pass.

`--metric execution` chỉ chấm DB gốc bằng cùng engine; `--metric legacy` là reference có hạn chế backtick. Hai metric này không được gọi là Test Suite Accuracy. Mẫu số luôn là toàn bộ IDs, kể cả missing/API/parse/timeout/budget failures. SQL chạy read-only và có deadline; harness/gold errors không tính thành model errors.

Báo valid SQL, API requests, token totals/coverage và mean/median latency. DAIL cộng preliminary + final, chưa gồm offline linking/retrieval; unknown usage là null. Không quy đổi thành tiền nếu chưa có giá provider xác minh.

## Phạm vi kết luận

Smoke nằm trong main và đã dùng để sửa output handling, nên main không phải holdout độc lập. Các runs có thời gian chồng lấp; latency chỉ mô tả experiment này. Đây là adapted reproduction trên subset, không phải full-dev hoặc điểm paper gốc.

[Báo cáo benchmark](../reports/benchmark_100.md) giữ kết quả trước migration; [workflow](repository_workflow.md) quy định manifests/source pins cho experiment mới. [Verification status](implementation/status.md) ghi phạm vi đã kiểm chứng.
