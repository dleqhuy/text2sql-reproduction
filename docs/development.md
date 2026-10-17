# Development: source, manifests và artifacts

Repo chính: [dleqhuy/text2sql-reproduction](https://github.com/dleqhuy/text2sql-reproduction), private khi tạo. Ba fork public kế thừa upstream public:

| Source | Repository | Trách nhiệm |
|---|---|---|
| DAIL | [dleqhuy/DAIL-SQL](https://github.com/dleqhuy/DAIL-SQL/tree/codex/reproduction-integration) | Native API/CLI, linking/cache, pinned retrieval và hai lượt inference |
| DIN | [dleqhuy/Few-shot-NL2SQL-with-prompting](https://github.com/dleqhuy/Few-shot-NL2SQL-with-prompting/tree/codex/reproduction-integration) | Native API/CLI, prompt module import an toàn và bốn stages |
| MAC | [dleqhuy/MAC-SQL](https://github.com/dleqhuy/MAC-SQL/tree/codex/reproduction-integration) | Native API/CLI, original agents và SQL guard/refinement |
| Spider | Upstream taoyds/spider | Legacy evaluator/hardness, không fork |
| Test Suite | Upstream taoyds/test-suite-sql-eval | Official execution comparison, không fork |

Cả năm source là submodules trong `third_party/`. Gitlink của repo chính là nguồn duy nhất cho executable commit. `.gitmodules` giữ URL; `configs/upstream_lock.json` chỉ giữ tên thư mục, vai trò, URL upstream và baseline commit để so diff, không lặp lại executable commit.

Mỗi fork sở hữu native API client, CLI, bounded retries/budgets, SQL guard và checkpoints trong `reproduction/`; không import repo chính. Repo chính xác minh dữ liệu/manifests/source pins rồi gọi subprocess, chuẩn hóa và đánh giá outputs. Runtime chung được version ở cả ba fork và có test phát hiện drift; credentials vẫn ở env. Vanilla dùng runtime của repo chính.

Submodule checkout thường detached HEAD. Trước khi sửa, tạo branch trong fork:

```bash
git -C third_party/MAC-SQL switch -c codex/my-method-change
# Sửa và test source trong fork.
git -C third_party/MAC-SQL add reproduction_adapter.py
git -C third_party/MAC-SQL commit -m "Describe the method change"
git -C third_party/MAC-SQL push -u origin codex/my-method-change
git add third_party/MAC-SQL
git commit -m "Pin MAC integration revision"
```

Push fork trước parent để người clone sau tải được commit. Fresh clone chỉ có `origin`; có thể thêm remote `upstream` theo metadata khi cần cập nhật baseline.

## Trace thay đổi

```bash
git diff --submodule=log <parent-old> <parent-new>
git -C third_party/MAC-SQL log --oneline 31a9df5e0d520be4769be57a4b9022e5e34a14f4..HEAD
git -C third_party/MAC-SQL diff 31a9df5e0d520be4769be57a4b9022e5e34a14f4 HEAD
```

Parent diff cho biết method đổi từ commit nào sang commit nào; fork diff chỉ rõ source đã chỉnh. Đây là Git history bình thường, không có source snapshot/diff tạo thêm cho mỗi run.

## Experiment manifests

Commit code/config/submodule pointers trước, rồi tạo manifest:

```bash
uv run python -m scripts.experiment_manifest create \
  --name my-main \
  --manifest data/prepared/spider-v1/manifest.json \
  --input data/prepared/spider-v1/main.jsonl \
  --output experiments/manifests/my-main.json
git add experiments/manifests/my-main.json
git commit -m "Record prepared main experiment"
uv run python -m scripts.experiment_manifest verify experiments/manifests/my-main.json
```

Manifest lưu root commit, fingerprint runtime, năm source commits/URLs/baselines, model, config/input/dataset/lock hashes và evaluator settings. Không lưu secrets hoặc source copies. State `prepared` có nghĩa cấu hình sẵn sàng; không chứng minh inference đã chạy. CLI từ chối overwrite manifest.

Commit thêm manifest/docs sau source commit được phép nếu runtime và source pins không đổi. Sau khi đổi code/config/model/data phải tạo manifest mới; không cập nhật manifest cũ để hợp thức hóa kết quả đã chạy.

Production run phải khai báo manifest và có clean working trees, kể cả untracked source files:

```bash
uv run python -m scripts.run_method --method vanilla \
  --production --experiment-manifest experiments/manifests/my-main.json \
  --input data/prepared/spider-v1/main.jsonl \
  --manifest data/prepared/spider-v1/manifest.json \
  --tables data/prepared/spider-v1/tables.json \
  --db-root data/spider/database --run-dir runs/my-main-vanilla
```

Run metadata ghi manifest hash và root commit, đồng thời giữ config/bundle/usage provenance. Development/fixture runs vẫn chạy được không có `--production`; không dùng chúng làm experiment đã xác nhận manifest. Với DAIL, tạo prompt bundles mới khớp fork commit bằng commands ở [running](running.md), rồi chạy cả hai lượt và aggregate. Bundle cũ bị từ chối khi source commit khác.

## Kết quả experiment

[Benchmark hiện tại](../reports/benchmark_native_100_20261017.md) có [completed record](../experiments/completed/native-main-100-20261017.json) tham chiếu source manifest và hashes của predictions/config/evaluation. Giữ manifest gốc của experiment đã hoàn thành; khi đổi runtime, tạo manifest mới cho lượt chạy tiếp theo.

Raw data, environments, `.env` và runs tiếp tục ignore. Người clone khác cần tải assets theo runbook; submodules chỉ giải quyết source versioning.

Phạm vi kiểm chứng và giới hạn môi trường ở [methods](methods.md#protocol-va-metrics).

## Contracts và checkpoints

Contracts được thực thi trong [contracts.py](../scripts/common/contracts.py). JSON/JSONL dùng UTF-8; mỗi dòng JSONL là một object.

### Input và gold

```json
{"example_id":"dev_000001","db_id":"concert_singer","question":"..."}
```

Input chỉ có ba trường trên. `example_id = dev_<original_index:06d>` theo bản dev đã fingerprint; không đánh lại ID sau sampling. Gold tách riêng cho evaluator, không chuyển vào prompt/retrieval. Dataset manifest giữ ordered IDs, seed/algorithm, source/schema/DB hashes; smoke là tập con main.

### Predictions

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

### Run artifacts

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

### Resume và evaluation

`--resume` yêu cầu khớp code/config/model/data/dependencies/bundle; chỉ bỏ qua rows đã terminal. Recovery chỉ chấp nhận dòng log cuối bị ngắt; lỗi giữa log làm run dừng. Process chết trước checkpoint có thể gửi lại request, nên không đảm bảo exactly-once billing. Dùng run-dir mới khi đổi config hoặc chạy lại lỗi.

Normalizer join theo ID; thiếu output thành `missing_prediction`, thừa/trùng/ambiguous alignment bị từ chối. Evaluator phân biệt lỗi SQL/model với lỗi harness/gold; harness lỗi làm evaluation thất bại. Accuracy và valid SQL rate dùng toàn bộ input làm mẫu số; valid SQL là guard cho phép và SQLite execute thành công, không đồng nghĩa correctness. Metric và options phải được ghi rõ theo [methods](methods.md#protocol-va-metrics).

## Kiểm tra và fixture

```bash
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest -q
# Dataset giả cho kiểm tra thủ công; không phải dữ liệu benchmark:
uv run python -m tests.create_fixture --output data/prepared/fixture
```

Tests dùng fixtures/local HTTP server, không gọi provider thật. Chúng kiểm tra parsers, retry/usage, CLI/resume, evaluator counterexamples, SQL guard, source manifests và pipeline benchmark. `scripts.common.normalization` giữ helper join predictions ngoài theo ID cho developer; pipeline native đã xuất đúng contract nên không cần CLI normalize riêng.
