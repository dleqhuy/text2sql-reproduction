# Runbook — inference và official Test Suite evaluation

Chạy từ root repo, Python 3.11.16/macOS arm64 đã kiểm chứng. Team scripts dùng `python -m scripts.<command>`. `.env` giữ `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; không đổi credential sang source upstream.

Contracts input/output và artifact layout ở [contracts](contracts.md); adaptations từng method ở [audit](repo_audit.md).

## Source versioning và manifests

Repo đã chuyển sang 3 forks + 5 submodules. [Workflow Git và experiment manifests](repository_workflow.md) mô tả clone, trace diff, cập nhật source pins và production runs. Các lệnh bên dưới vẫn dùng cho development; benchmark chính thức thêm `--production --experiment-manifest <path>` cho mỗi inference stage. Không dùng lại prompt bundle DAIL cũ khi fork commit thay đổi.

## Setup

```bash
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python -m scripts.bootstrap_upstream
uv run python -m nltk.downloader -q -d data/nltk_data punkt_tab stopwords wordnet punkt
```

Bootstrap kiểm tra gitlinks của cả ba method, legacy Spider và official test-suite evaluator. `configs/upstream_lock.json` giữ metadata upstream/baseline; executable commit chỉ lấy từ submodules. Môi trường inference riêng được pin trong `configs/environments/*-requirements.txt`. Ví dụ dựng DIN (MAC/DAIL tương tự, thay path và snapshot):

```bash
UV_CACHE_DIR=.uv-cache uv venv third_party/Few-shot-NL2SQL-with-prompting/.venv --python 3.11
UV_CACHE_DIR=.uv-cache uv pip install --python third_party/Few-shot-NL2SQL-with-prompting/.venv/bin/python -r configs/environments/din-requirements.txt
```

Không tạo lại venv đang sử dụng. Root `uv.lock` bao gồm sqlparse cho official execution evaluator. `scripts.check_provider` gửi một request nhỏ thật; probe và benchmark đã chạy với provider hiện có, không cần probe lặp lại mỗi câu.

## Dữ liệu đã freeze

Spider train/dev đầy đủ và 166 SQLite DB ở `data/spider/`; xem [nguồn/checksum](spider_dataset.md). Importer `scripts.fetch_spider` có thể tải/import archive đã pin. Dataset lớn được Git ignore.

Đã chạy lệnh dưới để tạo main 100, smoke 10, DB-balanced seed 42; thư mục đã tồn tại sẽ bị từ chối overwrite:

```bash
uv run python -m scripts.prepare_spider --source data/spider --output data/prepared/spider-v1 --size 100 --smoke-size 10 --seed 42
```

Manifest có bản theo dõi ở `data/splits/spider-v1.json`. Main chứa 100 câu trên 20 DB; smoke là tập con. Input không có gold, evaluator đọc gold riêng.

## DAIL assets và hai lượt retrieval

CoreNLP 3.9.2 jars từ Maven Central cùng dependency/version/checksum ở `configs/dail_corenlp_assets.json`. Java 11 được đặt local dưới `data/assets/`, không cài vào hệ thống. MPNet model/revision/path ở `configs/dail_embedding.json` (`all-mpnet-base-v2`, revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`). Snapshot HF chỉ cần JSON/TXT và `pytorch_model.bin`, không cần ONNX/TF weights.

Ví dụ khởi động server đã dùng:

```bash
data/assets/jdk-11.0.32.1+1/Contents/Home/bin/java -Xmx2g -cp 'data/assets/corenlp-3.9.2/*' edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 19000 -timeout 30000 -threads 2 -preload tokenize,ssplit,pos,lemma
```

Trong terminal khác, chạy linking (đã hoàn thành cho 8.659 train và 1.034 dev):

```bash
third_party/DAIL-SQL/.venv/bin/python -m scripts.prepare_dail_assets --indexed-cell-links
```

Cache `data/spider/enc/` được ghi một lần; importer từ chối overwrite. Dừng server sau khi linking hoàn tất. Adapter giữ nguyên `GloVe.tokenize/tokenize_for_copying` và CoreNLP lemma; không tải vector GloVe vì component này không đọc vectors/dim/lookup. Cache LIKE tương đương chỉ áp dụng hai mẫu truy vấn literal gốc trên DB bất biến; wildcard/quote/cột UTF-8 lỗi fallback về SQLite. Test đối chiếu source và cả 10 câu smoke thật đều khớp; bằng chứng `configs/dail_cell_link_validation.json`.

Tạo preliminary prompts (thay main bằng smoke nếu kiểm tra 10 câu):

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false third_party/DAIL-SQL/.venv/bin/python -m scripts.prepare_dail --dataset data/spider --input data/prepared/spider-v1/main.jsonl --stage preliminary --embedding-config configs/dail_embedding.json --output runs/my-dail-preliminary-prompts.json
```

Generator dùng factory/selector gốc: SQL, QA, 9-shot, `EUCDISQUESTIONMASK`. Chạy inference với bundle đó, sau đó tạo final prompts bằng cùng CLI, đổi `--stage final --preliminary <preliminary-run>/predictions.jsonl --output <new-bundle>`. Final selector là `EUCDISMASKPRESKLSIMTHR`. Candidate embeddings cache theo hash model/revision/texts, dùng lại chính vectors đã encode, không thay selection strategy.

Không cung cấp dev gold cho target/retrieval; train pool được đối chiếu train_spider/train_others, có overlap checks. `get_tokenizer/count_tokens` của pinned upstream vẫn trả 0: context-budget diagnostics gốc không đáng tin; cap server và provider usage được ghi thực tế. Không bật self-consistency.

## Chạy inference

Vanilla root env; DIN/MAC dùng interpreter riêng. Các flags chung đã test với cả main và smoke:

```bash
uv run python -m scripts.run_vanilla --input data/prepared/spider-v1/main.jsonl --manifest data/prepared/spider-v1/manifest.json --tables data/prepared/spider-v1/tables.json --db-root data/spider/database --run-dir runs/my-vanilla
```

DIN/MAC: dùng `<upstream>/.venv/bin/python -m scripts.run_method --method din_sql|mac_sql` cùng các flags trên. DAIL: root `python -m scripts.run_method --method dail_sql`, thêm `--dail-prompts <bundle>`; preliminary/final có run-dir riêng.

Để đo toàn pipeline DAIL, sau hai lượt dùng:

```bash
uv run python -m scripts.aggregate_dail --input data/prepared/spider-v1/main.jsonl --preliminary-run <preliminary-run> --final-run <final-run> --output runs/my-dail
```

Aggregator giữ SQL final, cộng API calls/tokens/latency của cả hai lượt; usage thiếu vẫn null. Latency này chưa gồm linking/retrieval offline. Không so sánh chi phí DAIL chỉ bằng một lượt final.

Model lấy từ `LLM_MODEL`; temperature và generation settings trong `configs/experiment.json`; caps giữ stage settings (Vanilla/MAC 1024; DIN 600/350; DAIL 200). Raw prompts/responses ở events, mỗi ID có final row kể cả lỗi. Resume bỏ qua terminal rows, từ chối mismatch code/config/dependencies/model/data. Process chết trước checkpoint có thể gọi lại câu chưa terminal; không cam kết exactly-once billing. Run-dir chỉ một writer; root CLI dùng fcntl nên chưa hỗ trợ Windows.

## Official Test Suite metric

Code gốc: `third_party/test-suite-sql-eval`, commit pin bằng submodule gitlink. Archive official [testsuitedatabases.zip](https://drive.google.com/file/d/1mkCx2GOFIqNesD4y8TDAO1yX1QZORP5w/view) đã tải; nguồn/hash ở `configs/test_suite_source.json`. Chỉ trích xuất 695 SQLite files cho 20 DB được chọn:

```bash
uv run python -m scripts.prepare_test_suite --archive data/assets/testsuitedatabases.zip --manifest data/prepared/spider-v1/manifest.json --output data/test-suite
```

Output hiện đã có, không chạy lại vào cùng path. Đã preflight gold queries của cả 100 IDs trên các neighbor DBs, không gọi LLM.

```bash
uv run python -m scripts.evaluate_spider --metric test-suite --suite-db-root data/test-suite --input data/prepared/spider-v1/main.jsonl --predictions runs/my-vanilla/predictions.jsonl --gold data/prepared/spider-v1/gold.jsonl --tables data/prepared/spider-v1/tables.json --db-root data/spider/database --manifest data/prepared/spider-v1/manifest.json --output runs/my-vanilla/eval-test-suite
uv run python -m scripts.summarize_results --input data/prepared/spider-v1/main.jsonl --predictions runs/my-vanilla/predictions.jsonl --evaluation runs/my-vanilla/eval-test-suite/evaluation.jsonl --output runs/my-vanilla/eval-test-suite
```

Primary params: plug_value=false, keep_distinct=true, seed=42. Dùng official query postprocessing, bag/ordering/column-permutation comparison; chỉ thay SQLite connections bằng read-only và VM deadline + process deadline. Gold/harness lỗi làm evaluation thất bại, không đổ vào lỗi model.

`--metric execution` là cùng comparison engine nhưng chỉ DB gốc, không gọi là TSA. `--metric legacy` giữ reference metric cũ có hạn chế backtick. Evaluator mặc định hiện là execution; phải chỉ rõ test-suite để chấm primary metric. Mỗi evaluation ghi metric/config/DB hashes; summary kiểm tra input/prediction hashes và không trộn metrics.

## Tạo lại báo cáo main-100

Khi đủ predictions và hai evaluation cho bốn run `spider-v1-main-{vanilla,dail,din,mac}`, tạo lại bảng so sánh và tám case studies mà không gọi LLM:

```bash
uv run python -m scripts.report_benchmark
```

Lệnh kiểm tra hashes inputs/predictions so với metrics, rồi ghi `reports/benchmark_100.md` và `reports/comparison.json`. Tên run cố định cho experiment hiện tại.

## Kiểm tra

```bash
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest -q
```

Tests không gọi provider thật; các original upstream tests chạy subprocess riêng và có prerequisites nguồn/NLTK/env. Suite tests bao phủ backticks, DISTINCT, neighbor database counterexample và write rejection. Parser tests bao phủ DIN thiếu subquestions/Label và MAC plain/fenced SQL. Phạm vi kiểm chứng và các giới hạn ở [verification status](implementation/status.md).
