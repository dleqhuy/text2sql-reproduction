# Phase 0 — Đóng băng protocol và scaffold

**Phụ thuộc:** nội dung repo hiện tại. **Mục tiêu:** thống nhất cách chạy và so sánh trước khi gọi model hoặc sửa upstream.

## Đầu việc

- [ ] **P0-01 — Chốt protocol.** Mở rộng [experiment_protocol.md](../experiment_protocol.md): số lượng đợt chính trong khoảng 100–200, seed, cách chọn subset, policy tham số model, giới hạn retry/thời gian/chi phí. Model ID lấy từ `LLM_MODEL` hiện có; chỉ được xem là khả dụng sau Phase 2. Nếu có giá token thì ghi nguồn/ngày; không có thì chỉ báo token/call, không suy ra chi phí.
- [ ] **P0-02 — Tạo cấu hình.** Đề xuất `configs/experiment.json` với method settings, dataset paths, generation params, timeout, retry, concurrency, agent limits và run budget. Không lưu API key trong cấu hình. Mọi giá trị mặc định phải hiện rõ, không dựa trên default thay đổi theo SDK.
- [ ] **P0-03 — Tạo scaffold.** `scripts/`, `scripts/common/`, `configs/`, `tests/`, `patches/`; bắt đầu module contract/config. Dùng script wrapper mỏng và common code có thể import nhất quán. Root giữ `tool.uv.package=false` trừ khi có lý do cần package.
- [ ] **P0-04 — Chuẩn hóa môi trường root.** Chọn và ghi Python cụ thể trong `.python-version` sau khi xác nhận uv hỗ trợ; thêm runtime dependencies cần dùng, pin bằng `uv.lock`. Không cài dependencies của cả ba upstream vào root.
- [ ] **P0-05 — Ghi mẫu env.** Tạo `.env.example` chỉ có placeholder cho `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. `.env` hiện có tiếp tục dùng được, không đổi tên hay ghi đè. Tải env từ root path rõ ràng và không ghi đè biến shell đã đặt.
- [ ] **P0-06 — Quy tắc Git/artifact.** Bổ sung ignore cho clone upstream theo lựa chọn plain clone, dữ liệu, DB, cache, runs và `.DS_Store`; giữ track `uv.lock`, cấu hình, split manifest nhỏ, patch, báo cáo đã rà bí mật. Nếu dùng submodule thay plain clone, thay quy tắc ignore tương ứng và ghi quyết định.
- [ ] **P0-07 — Chốt contract.** Triển khai validation theo [contracts.md](contracts.md), quy ước trạng thái lỗi, ID, provenance, phân biệt raw attempts với final predictions.

## Files dự kiến

| File | Vai trò |
|---|---|
| `configs/experiment.json` | Cấu hình được freeze cho benchmark |
| `scripts/common/config.py` | Đọc config/env, kiểm tra thiếu cấu hình, redact thông tin nhạy cảm |
| `scripts/common/contracts.py` | Validation input, prediction, run metadata |
| `.env.example`, `.python-version`, `uv.lock` | Setup có thể tái lập |
| `tests/test_contracts.py` | Các case sai ID, duplicate, trạng thái lỗi, cấu hình thiếu |

Tên module/script ở toàn bộ kế hoạch là thiết kế đề xuất; cập nhật tài liệu nếu implementation chọn cấu trúc khác.

## Gate nghiệm thu

- [ ] `uv sync --locked` dựng được môi trường root sau khi tạo lockfile.
- [ ] Formatter/linter đạt trên code nhóm; không format `third_party/`.
- [ ] Config loader đọc được ba biến `LLM_*`, báo thiếu bằng tên biến và không lộ giá trị.
- [ ] Contract từ chối duplicate ID và record thiếu trường bắt buộc; ví dụ hợp lệ qua được.
- [ ] Protocol ghi rõ lựa chọn đã chốt và lựa chọn còn chờ dữ liệu/capability. Manifest thực tế chỉ freeze sau Phase 2.

**Chưa làm ở phase này:** chạy benchmark, đoán CLI upstream hoặc công bố khả năng của endpoint.
