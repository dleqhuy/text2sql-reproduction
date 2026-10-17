# Repo chính, ba fork và experiment manifests

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

## Clone và kiểm tra phiên bản

```bash
git clone --recurse-submodules https://github.com/dleqhuy/text2sql-reproduction.git
cd text2sql-reproduction
uv sync --locked
uv run python -m scripts.bootstrap_upstream
git submodule status
```

Với checkout thiếu submodules: `git submodule update --init --recursive`. Bootstrap tự khởi tạo source thiếu; nếu source hiện có khác gitlink hoặc có tracked changes, lệnh dừng, không reset. Khi chuyển parent commit mà submodule còn trỏ phiên bản cũ, kiểm tra changes trước rồi chủ động update. Không dùng `update --remote` để chạy experiment cố định.

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

Push fork trước parent để người clone sau tải được commit. Remote `upstream` có sẵn trong các checkout đã migration; fresh clone chỉ có `origin`, có thể thêm `upstream` theo metadata khi cần cập nhật baseline.

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
  --name my-smoke \
  --manifest data/prepared/spider-v1/manifest.json \
  --input data/prepared/spider-v1/smoke.jsonl \
  --output experiments/manifests/my-smoke.json
git add experiments/manifests/my-smoke.json
git commit -m "Record prepared smoke experiment"
uv run python -m scripts.experiment_manifest verify experiments/manifests/my-smoke.json
```

Manifest lưu root commit, fingerprint runtime, năm source commits/URLs/baselines, model, config/input/dataset/lock hashes và evaluator settings. Không lưu secrets hoặc source copies. State `prepared` có nghĩa cấu hình sẵn sàng; không chứng minh inference đã chạy. CLI từ chối overwrite manifest.

Commit thêm manifest/docs sau source commit được phép nếu runtime và source pins không đổi. Sau khi đổi code/config/model/data phải tạo manifest mới; không cập nhật manifest cũ để hợp thức hóa kết quả đã chạy.

Production run phải khai báo manifest và có clean working trees, kể cả untracked source files:

```bash
uv run python -m scripts.run_method --method vanilla \
  --production --experiment-manifest experiments/manifests/my-smoke.json \
  --input data/prepared/spider-v1/smoke.jsonl \
  --manifest data/prepared/spider-v1/manifest.json \
  --tables data/prepared/spider-v1/tables.json \
  --db-root data/spider/database --run-dir runs/my-smoke-vanilla
```

Run metadata ghi manifest hash và root commit, đồng thời giữ config/bundle/usage provenance như trước. Development/fixture runs vẫn chạy được không có `--production`; không dùng chúng làm experiment đã xác nhận manifest. Với DAIL, tạo prompt bundles mới khớp fork commit bằng commands ở [runbook](reproducibility.md), rồi chạy cả hai lượt và aggregate như cũ. Bundle cũ bị từ chối khi source commit khác.

## Benchmark trước migration

[Historical manifest](../experiments/historical/spider-v1-main-100.json) tham chiếu đúng artifacts/provenance của benchmark đã hoàn thành. Các run gốc ghi root dirty cùng source hashes; không gán cho chúng commit fork mới hoặc tuyên bố khôi phục được uncommitted code từ hash. Predictions, metrics, reports và accounting cũ được giữ nguyên. Migration được kiểm tra bằng fixtures/offline tests; không tự động chạy lại benchmark có tính phí.

Raw data, environments, `.env` và runs tiếp tục ignore. Người clone khác cần tải assets theo runbook; submodules chỉ giải quyết source versioning.

Phạm vi kiểm chứng migration và giới hạn môi trường ở [verification status](implementation/status.md).
