# Input, output và artifacts

Contracts được thực thi trong [contracts.py](../scripts/common/contracts.py). JSON/JSONL dùng UTF-8; mỗi dòng JSONL là một object.

## Input và gold

```json
{"example_id":"dev_000001","db_id":"concert_singer","question":"..."}
```

Input chỉ có ba trường trên. `example_id = dev_<original_index:06d>` theo bản dev đã fingerprint; không đánh lại ID sau sampling. Gold tách riêng cho evaluator, không chuyển vào prompt/retrieval. Dataset manifest giữ ordered IDs, seed/algorithm, source/schema/DB hashes; smoke là tập con main.

## Predictions

```json
{"example_id":"dev_000001","db_id":"concert_singer","method":"vanilla","model":"MODEL_ID","predicted_sql":"SELECT ...","status":"ok","latency_ms":1200,"api_calls":1,"prompt_tokens":null,"completion_tokens":null,"error":null}
```

| Trường | Quy tắc |
|---|---|
| `method` | `vanilla`, `dail_sql`, `din_sql`, `mac_sql` |
| `status` | `ok`, `api_error`, `timeout`, `parse_error`, `method_error`, `missing_prediction`, `budget_exceeded` |
| `predicted_sql` | SQL string khi thành công; có thể null khi thất bại. `ok` chưa có nghĩa SQL hợp lệ hoặc đúng gold |
| `error` | Null khi ok; lỗi có `type`, `stage`, `message` đã redact |
| `latency_ms`, `api_calls` | Inference wall time gồm stages/retries; số requests thực sự gửi |
| Token usage | Tổng mọi calls; null nếu một call thiếu usage. Summary báo subtotal và coverage, không dùng 0 thay dữ liệu thiếu |

Mỗi completed run có đúng một final row cho mỗi input ID, không thừa/trùng. Raw responses/stages ở events; DAIL thêm `variant` để phân biệt preliminary/final/two-stage. Aggregator giữ final SQL và cộng accounting hai lượt; không ghép stages khác model/config/experiment.

## Run artifacts

```text
runs/<run-id>/
├── run_config.json
├── input_manifest.json
├── provenance.json
├── events.jsonl
├── checkpoints/
├── predictions.jsonl
├── stdout.log
├── stderr.log
└── eval-test-suite/                 # hoặc eval-execution/
    ├── evaluation_config.json
    ├── evaluation.jsonl
    ├── metrics.json
    └── comparison.md
```

Mỗi standalone fork có RunStore ghi identity/config, checkpoint atomic và một writer lock; native runner ghi code/dependency/source fingerprints. Wrapper repo chính truyền orchestrator identity/provenance qua file context tạm, không truyền credentials trong file đó. Production metadata thêm experiment manifest hash/root commit. DAIL aggregate giữ parent references thay vì tạo lại events/checkpoints. Không lưu key, authorization headers hoặc raw env.

## Resume và evaluation

`--resume` yêu cầu khớp code/config/model/data/dependencies/bundle; chỉ bỏ qua rows đã terminal. Recovery chỉ chấp nhận dòng log cuối bị ngắt; lỗi giữa log làm run dừng. Process chết trước checkpoint có thể gửi lại request, nên không đảm bảo exactly-once billing. Dùng run-dir mới khi đổi config hoặc chạy lại lỗi.

Normalizer join theo ID; thiếu output thành `missing_prediction`, thừa/trùng/ambiguous alignment bị từ chối. Evaluator phân biệt lỗi SQL/model với lỗi harness/gold; harness lỗi làm evaluation thất bại. Accuracy và valid SQL rate dùng toàn bộ input làm mẫu số; valid SQL là guard cho phép và SQLite execute thành công, không đồng nghĩa correctness. Metric và options phải được ghi rõ theo [protocol](experiment_protocol.md).
