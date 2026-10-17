# Kế hoạch chạy độc lập từng method fork

Mục tiêu: mỗi fork tự đọc `LLM_*`, gọi OpenAI Compatible API và chạy từ checkout riêng. Repo chính giữ dataset/protocol/manifests, điều phối bằng subprocess và chấm bằng `test-suite-sql-eval`. Benchmark cũ không bị sửa hoặc gán phiên bản mới.

| Bước | Công việc | Điều kiện hoàn thành | Trạng thái |
|---|---|---|---|
| 0 | Chốt CLI/input/output, kiểm tra baseline | Một contract JSONL, config/env, logging/usage/retry/resume | Đã xong |
| 1 | DIN: source import an toàn, API client và standalone CLI | Ba nhánh classification + correction; chạy không import repo chính | Đã xong |
| 2 | MAC: native provider, read-only execution, standalone CLI | Giữ agents/refinement; bỏ module injection từ repo chính | Đã xong |
| 3 | DAIL: native API, linking/retrieval CLI và hai lượt inference | Chạy preprocessing/prompts/inference/aggregate từ fork, có assets thật | Đã xong |
| 4 | Repo chính gọi CLI của forks | Không truyền provider hoặc monkey-patch source; output chuẩn và resume giữ nguyên | Đã xong |
| 5 | Kiểm chứng, README, commit/push và manifest mới | Offline tests, local HTTP provider fixture, standalone checkout, source pins sạch | Đã xong |

## Contract

- Mỗi fork có `python -m reproduction.run --input <jsonl> --tables <json> --db-root <dir> --run-dir <new-dir>`; optional `--env-file`, `--config`, `--manifest`, `--resume`.
- DAIL thêm `--dail-prompts`; preprocessing và hai lượt selection được cung cấp bằng CLI trong fork.
- `.env` giữ `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; biến shell ưu tiên. Không đưa key vào arguments, config hoặc logs.
- Config có temperature, token parameter, stage caps, timeout, bounded retry và run budgets. SQL read-only/timeout; output/checkpoints/events cùng contract repo chính.
- Runtime cần để chạy độc lập được version trong từng fork, không import ngược `scripts.*` của parent. Tests kiểm tra bản runtime chung không bị lệch giữa các fork.
- Smoke dùng fake transport và local HTTP server trước; không tự chạy lại benchmark trả phí. DAIL kiểm chứng thêm prompts/retrieval với weights/cache thật.
- Mỗi fork được commit/push trước khi parent cập nhật gitlink. Source changes làm prompt bundles/manifests cũ không còn phù hợp; tạo artifacts và manifest mới.

## Bằng chứng theo bước

1. DIN: native `DIN-SQL.py` import an toàn; original prompt constants/builders không đổi. HTTP fixture kiểm tra ba nhánh, bốn stages, fenced SQL và resume.
2. MAC: sửa trực tiếp `core/llm.py`, `core/agents.py`, `core/utils.py`; HTTP fixture buộc SQL sai → Refiner sửa, không có module injection.
3. DAIL: native `llm/chatgpt.py`, `ask_llm.py`; `reproduction.prepare_assets`, `prepare`, `aggregate`, `fetch_assets` chạy từ fork. CoreNLP jars verify SHA-256, MPNet files hiện có kiểm tra; preliminary và final prompts/selected train indices đều khớp 10/10 trước migration.
4. Parent: 45 pytest tests pass, gồm gọi cả ba native CLIs qua HTTP localhost, resume, config/manifest/source checks và runtime drift check.
5. Ba forks đã push và clone mới độc lập; tổng 7 native unit tests pass bằng environments hiện có. Không gọi provider ngoài, không chạy lại benchmark trả phí; reports/predictions benchmark cũ giữ nguyên. Manifest mới được tạo sau khi commit source/pins sạch; prepared manifests chưa chạy và đã bị thay thế chỉ giữ trong Git history; provenance của benchmark hoàn thành vẫn ở historical.

Fork commits: DIN `8431500`, MAC `cd90965`, DAIL `45c1f09`. Các fork có hướng dẫn cài đặt, env/config, native CLI, input/output và tests ở `REPRODUCTION.md`; README chính của mỗi fork dẫn tới hướng dẫn này. DAIL có thêm asset fetch/verify và commands linking, preliminary/final, aggregate. Cold setup dependencies/assets trên máy khác chưa được xác nhận.
