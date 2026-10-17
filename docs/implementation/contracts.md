# Contracts dùng chung

Đây là thiết kế cần implement ở Phase 0–2. Không phải định dạng native của các upstream. Encoding UTF-8; JSONL có một object mỗi dòng.

## Dataset và chống leakage

`example_id = dev_<original_index:06d>` lấy từ vị trí trong **bản dev đã fingerprint**; không đánh lại số sau lọc, không deduplicate theo question. Giữ original index và source hash trong manifest.

Input inference chỉ có:

```json
{"example_id":"dev_000001","db_id":"concert_singer","question":"..."}
```

Tên và giá trị trong ví dụ chỉ minh họa. Manifest chứa ordered IDs, split, seed, selection algorithm/version, target size, source file hashes, schema hash và DB fingerprints. Smoke 10 là tập con của manifest chính, giữ thứ tự tương đối. Difficulty labels nếu cần cho sampling được tính trong bước chuẩn bị tin cậy; không chuyển gold SQL/labels đó vào prompts.

Gold lưu artifact riêng cho evaluator, cùng ID và `db_id`; runner/retriever chỉ nhận input đã bỏ gold. Bản dev gốc có thể ở kho dữ liệu local nhưng không được chuyển nguyên record cho method. Kiểm tra cả hardcoded few-shot examples và cache upstream để phát hiện trùng dev; nếu có phải ghi nhận và xử lý trước khi tuyên bố so sánh không leakage.

## Final prediction

```json
{"example_id":"dev_000001","db_id":"concert_singer","method":"vanilla","model":"MODEL_ID","predicted_sql":"SELECT ...","status":"ok","latency_ms":1200,"api_calls":1,"prompt_tokens":null,"completion_tokens":null,"error":null}
```

- `method`: `vanilla`, `dail_sql`, `din_sql`, `mac_sql`.
- `status`: `ok`, `api_error`, `timeout`, `parse_error`, `method_error`, `missing_prediction`, `budget_exceeded`. `ok` chỉ nghĩa là lấy được SQL, chưa khẳng định execute/đúng gold.
- `predicted_sql`: string hoặc `null` nếu thất bại; lỗi phải có `error` gồm `type`, `stage`, `message` đã redact. Không biến output không parse được thành câu SQL giả.
- `latency_ms`: wall time inference của câu, gồm stages và retries; không gồm evaluator sau chạy. `api_calls` đếm request thực sự gửi, kể cả retry thất bại.
- Token usage cộng trên tất cả call đã biết. Nếu một call thiếu usage, tổng liên quan là `null`; có thể lưu subtotal và mức coverage riêng, không dùng số 0 để biểu diễn thiếu dữ liệu.
- Khi upstream không đo được call/latency, cho phép `null` kèm lý do instrumentation; không ước lượng số đẹp để lấp chỗ trống.
- Mỗi run có đúng một final row cho mỗi ID trong manifest, không thừa/trùng. Raw attempts là log riêng; SQL gốc và output model phải được giữ trước extraction.

## Run metadata

Đề xuất `runs/<run_id>/`:

```text
run_config.json
input_manifest.json
provenance.json
events.jsonl
raw/
predictions.jsonl
evaluation.jsonl
metrics.json
stdout.log
stderr.log
```

Metadata tối thiểu: method/variant, model requested/returned nếu có, provider label không nhạy cảm, config hash, ordered-manifest hash, dataset/schema/DB hashes, root/upstream/evaluator commits, upstream patch hash, dirty state/code fingerprint khi chưa commit, dependency versions, timestamp UTC, timezone hiển thị, generation params, retry/timeouts, concurrency, method knobs và trạng thái run (`running`, `completed`, `interrupted`, `failed`). Không lưu API key, authorization headers, raw env hoặc endpoint URL có credential/query nhạy cảm.

`events.jsonl` ghi `example_id`, stage, attempt, duration, request ID nếu có, usage, failure class; không dump HTTP headers. Dùng run UUID/timestamp + suffix để tránh ghi đè.

## Resume và normalization

- Chỉ resume khi config, code/patch, model, manifest và dataset fingerprint khớp; sai thì tạo run mới hoặc báo lỗi.
- Ghi checkpoint an toàn theo từng câu. Khi log bị ngắt ở dòng cuối, không nuốt lỗi ở các dòng giữa; khôi phục từ checkpoint hợp lệ và ghi recovery event.
- Không gọi lại các câu đã terminal trong cùng run. Rerun lỗi là run mới có `parent_run_id` và danh sách ID; không thay kết quả benchmark cũ âm thầm.
- Upstream không hỗ trợ resume thì cần wrapper/checkpoint hoặc ghi rõ giới hạn trước đợt chính; không hứa tránh duplicate API calls khi không quan sát được upstream.
- Normalizer join theo ID; nếu upstream chỉ ghi theo vị trí, cần sidecar ánh xạ theo input order. Thiếu output sinh `missing_prediction`; thừa/trùng/không xác định thứ tự thì dừng normalization.

## Evaluation và metrics

`evaluation.jsonl` giữ ID, prediction status, execution status, EX correctness và thông tin lỗi đã redact. Phân biệt lỗi SQL với lỗi harness/evaluator: harness hỏng hoặc gold không chạy là run evaluation không hợp lệ, cần sửa/chạy lại, không gán thành lỗi model.

- EX = số câu đúng theo evaluator đã pin / **tổng số ID trong manifest**.
- Missing, lỗi API, timeout, parse failure và budget-skipped vẫn ở mẫu số và có correctness bằng 0 khi evaluation hợp lệ.
- Valid SQL rate định nghĩa ở đây là SQL được guard cho phép và SQLite execute thành công trong giới hạn / tổng manifest. Báo thêm nhóm parse/guard/timeout nếu có; không gọi execution success là correctness.
- Báo mean/median latency với số mẫu đo được và quy tắc cohort; call/token mean có coverage tương tự. Ghi riêng tổng request/retries/thất bại và thời gian cả run.
- Official EX là metric chính. Direct result comparison tự viết chỉ dùng fixture/debug, không được gắn nhãn official EX. Nếu có thêm test-suite accuracy phải là cột riêng với evaluator/config riêng.
