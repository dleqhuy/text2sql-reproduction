# Phase 4 — Evaluation, phân tích và bàn giao

**Phụ thuộc:** evaluator fixture Phase 2 và outputs Phase 3 cho các method đã hoàn thành. **Mục tiêu:** so sánh có thể kiểm tra lại, không bỏ các câu lỗi khỏi mẫu số.

## Đầu việc

- [ ] **P4-01 — Preflight.** Kiểm tra mỗi run có đúng ordered ID set, `db_id`, manifest/schema/DB fingerprints và model sinh SQL đã freeze. Config mismatch phải được giải thích hoặc tách bảng, không gộp thành cùng điều kiện.
- [ ] **P4-02 — Evaluation đầy đủ.** Hoàn thiện wrapper official evaluator đã pin, lưu command/options/env/commit. Bảo đảm predict/gold alignment; lưu kết quả theo câu và execution/evaluator failure. Gold/schema hỏng hoặc evaluator crash là lỗi harness phải giải quyết trước khi công bố.
- [ ] **P4-03 — Metrics.** Implement `scripts/summarize_results.py` từ artifacts, không nhập tay điểm. EX và valid SQL rate tính trên toàn manifest; báo counts, API errors/timeouts, call/token/latency coverage và run completion state theo [contracts](contracts.md).
- [ ] **P4-04 — So sánh.** Xuất `reports/comparison.md` và machine-readable summary. Ghi N, subset fingerprint, model/provider label, variant, EX count/N, valid count/N, mean/median latency, calls/question, usage availability và deviation. Không điền số 0 cho method chưa chạy.
- [ ] **P4-05 — Error analysis.** Chọn 5–10 câu đại diện, giữ ID và so sánh cùng câu giữa các method: bảng/cột, join, aggregation, nesting, logic, parse, timeout, API failure. Tách lỗi transport/setup khỏi lỗi reasoning. Ghi nguyên tắc chọn case để tránh chỉ lấy ví dụ có lợi cho một method.
- [ ] **P4-06 — Final report.** Tạo `reports/final_report.md`: mục tiêu, pipeline và variant, setup/model, protocol, metrics, sai khác với upstream, lỗi điển hình, blockers, giới hạn. Dùng nhãn code-based adapted reproduction; không suy diễn đạt điểm paper gốc.
- [ ] **P4-07 — Reproducibility runbook.** Tạo `docs/reproducibility.md`: lấy dữ liệu hợp lệ, checkout commit, apply patch, dựng uv env từng repo, cấu hình `LLM_*`, prepare manifest, probe, smoke, normalize, evaluate, summarize. Chỉ ghi lệnh đã test, kèm cwd và đường dẫn artifact.
- [ ] **P4-08 — Rerun kiểm chứng.** Dựng lại trong checkout/environment sạch nếu khả thi, replay preparation + normalization + evaluation từ raw artifact, rồi một smoke inference nhỏ. Ghi phần chưa xác minh; không yêu cầu model remote sinh lại SQL giống từng byte dù temperature thấp.
- [ ] **P4-09 — Bàn giao.** Cập nhật README, protocol, audit và bốn runbook. Rà artifact/diff không chứa secret trước khi chia sẻ hoặc commit; lưu dataset lớn/runs ở nơi phù hợp thay vì đưa vào Git mặc định.

## Kiểm tra có giá trị

- Fixture official evaluator: correct, executable-but-wrong, invalid, missing, timeout; đối chiếu count và mẫu số.
- Summary: thêm một failed row phải làm thay đổi denominator đúng, không lọc theo `status=ok`.
- Alignment: đảo output order không đổi kết quả nếu ID mapping đúng; duplicate/unknown ID phải bị phát hiện.
- Replay offline từ raw outputs phải tạo cùng normalized predictions và metrics với cùng evaluator/config.
- Ruff/test suite cho code nhóm chạy đạt. Không mở rộng test lại toàn upstream nếu không có thay đổi hoặc nghi vấn mới.

## Gate bàn giao

- [ ] Bảng kết quả truy ngược được từng run/config/manifest/commit/patch.
- [ ] Mọi failed/missing row có mặt; EX không bị nâng bởi việc bỏ câu lỗi.
- [ ] Usage và latency có cohort/coverage, cost chỉ có khi giá và usage đủ căn cứ.
- [ ] Có error analysis, cách dựng lại và phần chưa hoàn thành được ghi rõ.
- [ ] Mục tiêu bốn method chỉ được đánh dấu hoàn tất khi cả bốn có kết quả hợp lệ. Nếu một method bị chặn, bàn giao phần đã làm kèm blocker và không tuyên bố hoàn thành toàn bộ mục tiêu.
