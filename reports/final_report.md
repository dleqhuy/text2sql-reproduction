# Báo cáo implementation — 17/10/2026

Đã hoàn thành runtime, bốn adapters, smoke và benchmark 100 câu Spider dev trên endpoint OpenAI Compatible cấu hình sẵn. Xem [báo cáo và tám error case studies](benchmark_100.md), [metrics JSON](comparison.json), [trạng thái các phase](../docs/implementation/status.md) và [lệnh tái lập](../docs/reproducibility.md).

| Method | Test Suite Accuracy | DB gốc | API requests |
|---|---:|---:|---:|
| Vanilla | 69/100 | 81/100 | 100 |
| DAIL-SQL | 76/100 | 87/100 | 200 |
| DIN-SQL | 78/100 | 86/100 | 400 |
| MAC-SQL | 73/100 | 86/100 | 125 |

Primary metric dùng official test-suite evaluator đã pin commit, trên 695 original/generated SQLite files thuộc 20 DB; plug_value=false, keep_distinct=true, seed=42. Gold self-check toàn bộ 100 câu pass. Mọi lỗi vẫn trong mẫu số; bốn output DIN không execute được do format được giữ nguyên trong báo cáo.

## Implementation và kiểm chứng

Transport Chat Completions có bounded retries, usage và checkpoint/resume. Gold tách khỏi inference; SQLite chạy read-only với timeout. DIN giữ bốn stages; MAC giữ agent classes và refinement; DAIL dùng selectors/prompt factory gốc với CoreNLP/MPNet thật, cộng đủ accounting preliminary + final. Source upstream không bị sửa tracked files; adaptations ở [audit](../docs/repo_audit.md).

31 tests pass, gồm official evaluator counterexamples, parser compatibility, SQL guard, resume và DAIL accounting/cell-link cache. Môi trường được pin; predictions, raw stage responses và evaluation provenance lưu local.

## Giới hạn

Đây là code-based adapted reproduction, không tuyên bố tái lập điểm paper hoặc full Spider dev. Smoke thuộc main đã dùng để sửa compatibility handling; main không phải holdout độc lập. Chưa xác nhận cold setup trên máy khác. Latency chịu ảnh hưởng các run chồng lấp, DAIL chưa gồm preprocessing/retrieval offline; token usage chưa quy đổi thành tiền.

Không bổ sung source snapshot/diff theo yêu cầu người dùng; giữ provenance và source pins hiện có.
