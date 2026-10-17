# Cài đặt và chạy benchmark

Chạy từ root repo. Môi trường đã kiểm chứng: Python 3.11.16/macOS arm64; CLI dùng `fcntl`, chưa hỗ trợ Windows. Mỗi fork có environment và native CLI riêng; repo chính điều phối và chấm điểm.

## Setup một lần

```bash
UV_CACHE_DIR=.uv-cache uv sync --locked
uv run python -m scripts.bootstrap_upstream
cp -n .env.example .env
uv run python -m nltk.downloader -q -d data/nltk_data punkt_tab stopwords wordnet punkt
```

Điền `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` vào `.env`. Giữ nguyên file nếu đã cấu hình. Dependency lock của từng method nằm trong fork; dựng môi trường còn thiếu, ví dụ DIN:

```bash
uv venv third_party/Few-shot-NL2SQL-with-prompting/.venv --python 3.11
uv pip install --python third_party/Few-shot-NL2SQL-with-prompting/.venv/bin/python -r third_party/Few-shot-NL2SQL-with-prompting/requirements-compatible.lock.txt
```

MAC/DAIL làm tương tự, thay đường dẫn. Không tạo lại environment đang dùng. Hướng dẫn chạy trực tiếp: [DIN](../third_party/Few-shot-NL2SQL-with-prompting/REPRODUCTION.md), [MAC](../third_party/MAC-SQL/REPRODUCTION.md), [DAIL](../third_party/DAIL-SQL/REPRODUCTION.md).

## Dữ liệu và assets

Spider 1.0 train/dev lấy từ [nguồn chính thức](https://yale-lily.github.io/spider): 1.034 dev, 7.000 train_spider, 1.659 train_others và 166 DB. License CC BY-SA 4.0; attribution Yu et al. (2018). [Source manifest](../configs/spider_source.json) ghi checksum archive, JSON và từng DB. Importer hỗ trợ mirror đã pin với cùng checksum, từ chối HTML quota pages và overwrite.

Chỉ chạy các bước chưa có output:

```bash
uv run python -m scripts.fetch_spider
# Nếu nguồn chính không tải được: dùng --source mirror hoặc --archive /path/to/spider.zip.
uv run python -m scripts.prepare_spider --source data/spider --output data/prepared/spider-v1 --size 100 --smoke-size 10 --seed 42
uv run python -m scripts.prepare_test_suite --archive data/assets/testsuitedatabases.zip --manifest data/prepared/spider-v1/manifest.json --output data/test-suite
```

Tải [official test-suite archive](https://drive.google.com/file/d/1mkCx2GOFIqNesD4y8TDAO1yX1QZORP5w/view) vào `data/assets/testsuitedatabases.zip` trước lệnh cuối. [Suite manifest](../configs/test_suite_source.json) pin 695 SQLite files cho 20 DB. Dataset, assets và runs được Git ignore; submodules chỉ chứa source.

DAIL cần linking cache `data/spider/enc/`, CoreNLP 3.9.2 và MPNet snapshot theo [embedding config](../configs/dail_embedding.json). Cách tải assets nằm trong [DAIL setup](../third_party/DAIL-SQL/REPRODUCTION.md). Trên máy hiện tại, Java/server đã dùng:

```bash
data/assets/jdk-11.0.32.1+1/Contents/Home/bin/java -Xmx2g -cp 'data/assets/corenlp-3.9.2/*' edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 19000 -timeout 30000 -threads 2 -preload tokenize,ssplit,pos,lemma
```

Trong terminal khác, tạo linking một lần rồi dừng server:

```bash
uv run python -m scripts.prepare_dail_assets --indexed-cell-links
```

CLI benchmark tạo lại prompt bundles và retrieval; không chạy lại linking nếu cache đã có. Máy hiện tại đã có dataset, suites, linking và embedding assets; không cần tải lại.

## Một lệnh chạy cả bốn method

Revision hiện tại có manifest `experiments/manifests/main-v3.json` đã chuẩn bị, chưa chạy inference. Khi đổi source/config/model/data, tạo và commit manifest mới theo [development](development.md#experiment-manifests). Chạy benchmark:

```bash
uv run python -m scripts.benchmark --experiment-manifest experiments/manifests/main-v3.json --run-dir runs/my-benchmark
```

Input/config được đọc từ manifest, không phải nhập lại nhiều flags. Mặc định dùng `data/spider`, `data/test-suite`, `configs/dail_embedding.json`; đổi bằng `--dataset`, `--suite-db-root`, `--embedding-config` khi cần.

Pipeline tạo preliminary prompts, chạy Vanilla → DIN → MAC → DAIL preliminary → tạo final prompts → DAIL final, aggregate hai lượt, chấm cả Test Suite và DB gốc rồi viết `report.md`, `comparison.json`, `benchmark.json` trong run-dir. Inference chạy tuần tự. Gold tách khỏi prompts; preliminary/final DAIL có checkpoint riêng.

```bash
# Chỉ in các bước, không gọi API hoặc ghi artifacts; chưa xác minh production preflight.
uv run python -m scripts.benchmark --experiment-manifest experiments/manifests/main-v3.json --run-dir runs/my-benchmark --dry-run
# Tiếp tục pipeline bị ngắt; kiểm tra identity và hashes trước khi bỏ qua bước đã xong.
uv run python -m scripts.benchmark --experiment-manifest experiments/manifests/main-v3.json --run-dir runs/my-benchmark --resume
```

Production yêu cầu source sạch, model/config/data/source pins khớp manifest và suites đúng hash. Đổi runtime thì tạo manifest/run-dir mới; manifest của benchmark đã hoàn tất chỉ tham chiếu revision lúc chạy. Resume không chạy lại các câu đã terminal, kể cả lỗi. Nếu DAIL preliminary có failures, final retrieval dừng; giữ experiment lỗi và dùng run mới để kiểm tra thay đổi.

## Chạy riêng một method hoặc chấm lại

```bash
uv run python -m scripts.run_method --method vanilla --input data/prepared/spider-v1/main.jsonl --manifest data/prepared/spider-v1/manifest.json --tables data/prepared/spider-v1/tables.json --db-root data/spider/database --run-dir runs/my-vanilla
```

Thay `vanilla` bằng `din_sql` hoặc `mac_sql`. Thêm `--production --experiment-manifest <path>` cho experiment chính thức. Development runs không có manifest không được coi là production benchmark.

DAIL riêng lẻ: dùng `scripts.prepare_dail --dataset data/spider --input <input> --stage preliminary --embedding-config configs/dail_embedding.json --output <bundle>`, rồi `scripts.run_method --method dail_sql` cùng flags chung và `--dail-prompts <bundle>`. Tạo final bundle bằng `--stage final --preliminary <preliminary-run>/predictions.jsonl`, chạy final với run-dir mới, rồi:

```bash
uv run python -m scripts.aggregate_dail --input data/prepared/spider-v1/main.jsonl --preliminary-run <preliminary-run> --final-run <final-run> --output runs/my-dail
```

Chấm predictions có sẵn không gọi LLM:

```bash
uv run python -m scripts.evaluate_spider --metric test-suite --suite-db-root data/test-suite --input data/prepared/spider-v1/main.jsonl --predictions runs/my-vanilla/predictions.jsonl --gold data/prepared/spider-v1/gold.jsonl --tables data/prepared/spider-v1/tables.json --db-root data/spider/database --manifest data/prepared/spider-v1/manifest.json --output runs/my-vanilla/eval-test-suite
uv run python -m scripts.summarize_results --input data/prepared/spider-v1/main.jsonl --predictions runs/my-vanilla/predictions.jsonl --evaluation runs/my-vanilla/eval-test-suite/evaluation.jsonl --output runs/my-vanilla/eval-test-suite
```

Để chấm DB gốc, đổi `--metric execution`, bỏ `--suite-db-root` và dùng output `eval-execution`. Primary metric phải chỉ rõ `--metric test-suite`; mặc định evaluator là execution. Protocol và giới hạn nằm trong [methods](methods.md#protocol-va-metrics).
