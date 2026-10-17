# Phase 2 — OpenAI Compatible, dữ liệu và hạ tầng chạy

**Phụ thuộc:** contract Phase 0; integration details Phase 1 cho từng upstream/evaluator. **Mục tiêu:** dựng đường chạy chung có thể kiểm chứng trước inference quy mô lớn.

## A. Provider và cấu hình

- [ ] **P2-01 — Provider adapter.** Tạo `scripts/common/llm.py`, đọc `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` qua config loader. Truyền base URL/key/model rõ ràng vào client. Không tự nối `/v1` hoặc đổi tên model khi chưa xác minh cấu hình endpoint.
- [ ] **P2-02 — Capability probe.** Tạo `scripts/check_provider.py`: gửi một request nhỏ, kiểm tra shape response và nội dung text; ghi capability profile không chứa secret. Xác minh API route thực sự dùng được, tham số temperature/token limit được hỗ trợ, timeout/error shape, usage có hay không. Listing model chỉ là kiểm tra phụ nếu provider hỗ trợ, không phải điều kiện bắt buộc.
- [ ] **P2-03 — Retry có giới hạn.** Retry lỗi tạm thời/rate limit theo policy, backoff có jitter và tôn trọng retry hint khi có. Không retry vô hạn lỗi auth/model/request không hợp lệ. Chọn một tầng chịu trách nhiệm retry; tính cả SDK và upstream để tránh nhân số lần gọi.
- [ ] **P2-04 — Mapping upstream.** Nếu upstream yêu cầu `OPENAI_API_KEY`, `OPENAI_BASE_URL` hoặc legacy `api_base`, ánh xạ từ `LLM_*` theo code đã audit. Truyền vào process/client theo môi trường riêng; không ghi credential vào repo hoặc command-line args. Không buộc mọi repo import cùng một SDK version.
- [ ] **P2-05 — Capability mismatch.** Tham số không hỗ trợ phải được ghi trong config/profile và đánh giá ảnh hưởng. Không tự đổi sang model khác hoặc bỏ một stage. Nếu endpoint chỉ có chat mà code cần legacy Completion, patch transport tối thiểu và ghi khác biệt prompt/message wrapper.

Test provider adapter bằng client giả cho response hợp lệ, usage thiếu, timeout, 429, auth error và retry budget. Probe thật là bước riêng có thể phát sinh phí; chỉ chạy khi bắt đầu implementation, với request nhỏ, không chạy trong lần lập kế hoạch này.

## B. Spider và subset

- [ ] **P2-06 — Lấy và kiểm kê Spider 1.0.** Theo nguồn/điều kiện truy cập thực tế; không giả định repo đã có DB. Kiểm tra train, dev, tables metadata, DB path và từng `db_id`; ghi source, hash, license/điều kiện sử dụng. Không commit dataset.
- [ ] **P2-07 — Chuẩn bị split.** Tạo `scripts/prepare_spider.py`: validate source, gán ID theo original index, chọn chính xác N đợt chính và smoke 10 theo policy đã chốt, xuất input/gold tách biệt. Nếu dùng difficulty thì lấy nhãn/cách tính được xác minh, không bịa field trong Spider JSON.
- [ ] **P2-08 — Freeze manifest.** Đề xuất stratify theo difficulty và phủ nhiều DB khi khả thi, có seed và tie-break cố định. Lưu thuật toán, ordered IDs, fingerprint; chạy lại phải cho cùng kết quả. Thay N/seed/source sau freeze phải tạo manifest mới.
- [ ] **P2-09 — Schema serializer.** Tạo `scripts/common/schema.py` cho Vanilla, giữ đúng tên bảng/cột/PK/FK từ metadata đã đối chiếu DB. Upstream vẫn dùng cách serialize schema gốc của method nếu có.

## C. Logging, SQL guard và evaluator readiness

- [ ] **P2-10 — Run storage.** Tạo `scripts/common/run_store.py` cho config snapshot, events, raw outputs, final rows, checkpoint và resume theo [contracts](contracts.md). Dừng mới gửi request khi đạt call/time/token budget; nếu thiếu usage thì chỉ thực thi được các giới hạn đo được và phải ghi rõ.
- [ ] **P2-11 — SQL execution guard.** Tạo `scripts/common/sqlite_guard.py`: SQLite URI read-only, query-only, authorizer hạn chế thao tác và không cho attach/write; không dùng kiểm tra prefix `SELECT` làm cơ chế duy nhất. Chạy query trong worker có deadline và cơ chế terminate; chặn ghi file/DB kể cả từ SQL có nhiều statement. Giới hạn tài nguyên/kích thước output cho phần log mà không làm thay đổi semantics của evaluator.
- [ ] **P2-12 — Bao phủ mọi đường execute.** Dùng guard cho validation baseline, MAC refinement và đường evaluator tương ứng đã audit. Đối chiếu với execution gốc; ghi mọi patch safety có ảnh hưởng. Đừng cho MAC execute không giới hạn chỉ vì evaluator được bảo vệ.
- [ ] **P2-13 — Evaluator fixture sớm.** Tạo wrapper `scripts/evaluate_spider.py` quanh implementation official đã pin; dựng fixture nhỏ gồm SQL đúng, SQL chạy được nhưng sai kết quả, SQL lỗi, missing và timeout. Xác minh format/order/options trước khi tốn inference cho cả subset.

## Files và kiểm tra trọng yếu

| Nhóm | Files dự kiến | Kiểm tra |
|---|---|---|
| Provider | `check_provider.py`, `common/llm.py` | Real probe nhỏ + fake-client lỗi/retry/usage |
| Data | `prepare_spider.py`, `common/schema.py`, `data/splits/` | Stable IDs, checksum, input không có gold, thiếu DB thì fail |
| Run | `common/run_store.py` | Ngắt/resume, config mismatch, không duplicate final row |
| SQL | `common/sqlite_guard.py` | SELECT/CTE hợp lệ; chặn write/attach; query dài bị dừng; DB hash không đổi |
| Evaluation | `evaluate_spider.py` | Alignment và denominator trên fixture; lỗi harness được tách riêng |

Các đường dẫn `common/` trong bảng thuộc `scripts/`. Tên CLI/flags chính thức được thiết kế và ghi runbook sau implementation.

## Gate nghiệm thu

- [ ] Endpoint/model hiện có trả response hợp lệ; capability và giới hạn được ghi nhận.
- [ ] Có input smoke/main, train-only demonstrations source, gold riêng và manifest frozen.
- [ ] Retry và run budget hữu hạn; secret không xuất hiện trong config snapshot/log lỗi/probe output.
- [ ] SQL guard vượt kiểm tra read-only/timeout trên mọi code path được sử dụng.
- [ ] Evaluator fixture chạy được và failure rows vẫn ở mẫu số.
- [ ] Root checks đạt; còn blocker upstream nào phải tách theo method trước Phase 3.
