# Upstream audit và integration log

Khảo sát và kiểm thử ngày 17/10/2026. Các đường dẫn nguồn dưới đây tương đối với checkout upstream, line numbers thuộc đúng commit đã pin trong `configs/upstream_lock.json`.

| Method | Commit | Source file:line | Hành vi gốc | Adapter và lý do | Bằng chứng |
|---|---|---|---|---|---|
| DAIL-SQL | `2061f68112222083134a0c9e2877961ff315ff44` | `llm/chatgpt.py:8,54`; `ask_llm.py:19` | Legacy OpenAI API, allowlist model, org hardcoded, retry vô hạn; n mặc định 5 | Root LLM bounded chat transport; n=1 cho variant không self-consistency; không truyền key qua CLI | Dependency setup + original imports pass; hai stage retrieval/prompt đã chạy MPNet thật; main 100 hoàn thành |
| DAIL-SQL | cùng commit | `data_preprocess.py:16,106`; `generate_question.py:19`; `prompt/ExampleSelectorTemplate.py:204,321` | CoreNLP/GloVe schema linking, masked-question retrieval rồi pre-skeleton threshold | `scripts.prepare_dail` dùng factory gốc; train-only validation, bỏ target dev gold và diagnostic quality, ghi selected train indices | Original selection preliminary/final đã chạy với production assets |
| DAIL-SQL | cùng commit | `utils/utils.py:170,176` | tokenizer/count_tokens đều trả 0 | Giữ hành vi và công bố giới hạn context-budget; dùng provider usage cho measurement | Đã đọc source; chưa sửa token counting |
| DIN-SQL | `0474801616130413b024fd008b016a190684649e` | `DIN-SQL.py:437,444` | Import có argv side effects; `API_KEY = #key` sai cú pháp | AST loader thay đúng stub thành None trong bộ nhớ, chỉ compile prompt constants/functions; không chạy key/env/main gốc | Import và bốn-stage fixture thật pass |
| DIN-SQL | cùng commit | `DIN-SQL.py:452,572,587,602` | Original prompt makers, ba nhánh classification, generation, debugger, vòng retry vô hạn | Giữ prompt/function và stage flow; thay transport; bounded retry; xử lý debugger trả full SELECT hoặc suffix; không đọc/print gold | Offline tests EASY/NON-NESTED/NESTED; real provider 4 calls, SQL hợp lệ trên fixture |
| MAC-SQL | `31a9df5e0d520be4769be57a4b9022e5e34a14f4` | `core/api_config.py:3`; `core/llm.py:34` | Azure API config, model hardcoded, retry 5 lần + sleep | Bridge module tới root LLM; model/temperature từ frozen config; loại Hello-world ping khỏi per-question calls | Real provider fixture pass; không import Azure config |
| MAC-SQL | cùng commit | `core/agents.py:42,598,661,672`; `core/const.py:1` | Selector/Decomposer/Refiner; SQLite write-capable; MAX_ROUND=3 | Giữ original agent classes và transitions; read-only metadata connection; Refiner worker có deadline; khôi phục leading slash bị Selector strip | Fixture buộc SQL sai → Refiner sửa → System; real fixture schema nhỏ skip prune theo logic gốc |
| Spider legacy evaluator | `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c` | `evaluation.py:478,614`; `process_sql.py:31` | FK/value/distinct rebuild và eval_exec_match; SQLite mặc định | Dùng đúng comparison/rebuild functions, isolated worker, read-only; alignment/failure handling do wrapper quản lý | Correct/wrong/invalid/missing fixture; full CLI cho ba synthetic runs |

## Môi trường và fidelity

- Root và cả ba upstream env: Python 3.11.16, macOS arm64. Root dùng `uv.lock`; upstream snapshot ở `configs/environments/*-requirements.txt`.
- DIN env chỉ cài dependencies inference cần cho adapter (pandas + root runtime), không cài stack training torch/datasets của requirements gốc. MAC tương tự, thêm pandas/tiktoken/func-timeout.
- DAIL requirements gốc kết hợp root runtime và `configs/dail_constraints.txt`: torch 2.2.2, torchtext 0.17.2, numpy 1.26.4, sentence-transformers 2.2.2, transformers 4.30.2, huggingface-hub 0.25.2. Install/import và preprocessing/retrieval với weights thật đã pass.
- Không sửa tracked source upstream, không autoformat upstream. Không có patch file vì thay đổi nằm trong adapter của nhóm ở `scripts/common/methods.py` và `scripts/prepare_dail.py`. Mỗi run ghi root code fingerprint + upstream commit/diff hash, nên adaptation vẫn truy ngược được.
- Temperature chung 0; token cap Vanilla/MAC lấy config (mặc định 1024), DIN giữ cap upstream 600 generation/350 correction, DAIL 200 mỗi generation. Các cap này khác nhau có chủ đích để giữ stage semantics; phải công bố khi so sánh.
- DAIL ở đây là variant hai lượt, 9-shot QA, không self-consistency. Preliminary có run riêng và `variant=preliminary`; chỉ final dùng làm bảng DAIL chính.
- API Compatible adaptation là code-based adapted reproduction, không phải tái lập điểm GPT-4 lịch sử.

## License kiểm tra tại clone

DAIL `LICENSE.txt`: Apache-2.0; DIN `LICENSE.txt`: MIT (header placeholder upstream); Spider evaluator `LICENSE`: Apache-2.0. MAC có `training_scripts/LICENSE` nhưng không thấy license toàn root cho inference trong checkout đã đọc; giữ nguồn riêng, cần làm rõ trước khi phân phối lại source của họ. Dataset theo nguồn Spider là CC BY-SA 4.0, không commit vào repo này.

## Lệnh và artifacts

Lệnh cài/probe/root CLI đã test được ghi trong [runbook](reproducibility.md). `scripts.bootstrap_upstream` xác nhận bốn commit clean tracked source. Các artifacts local: `runs/provider_probe.json`, `runs/fixture-v3-vanilla`, `runs/fixture-v3-din`, `runs/fixture-v2-mac`. Không ghi key/endpoint vào audit.

## Blockers đã ghi nhận trước production (đã giải quyết trong cập nhật dưới)

Các blocker ban đầu gồm Spider download, CoreNLP/Java, linking cache, MPNet revision và legacy parser với backticks. Đã giải quyết bằng nguồn/hash xác minh, production assets và official test-suite engine. Bốn method hoàn thành main 100; xem [benchmark](../reports/benchmark_100.md). Cold setup trên máy khác vẫn chưa được kiểm chứng.

## Hoàn thiện evaluator và production DAIL

- Official test-suite repo `taoyds/test-suite-sql-eval` commit `e97acc546ecbee8fa27fa8dbf025ef61493a876c`. Dùng exec_eval.eval_exec_match với plug_value=false, keep_distinct=true, seed=42; read-only worker, không thay comparison logic. Generated DB sources/hashes ở configs/test_suite_source.json: 695 SQLite files cho 20 DB. Gold self-check cả 100 câu đã pass.
- Legacy EX giữ làm reference. Official single-original-DB execution và generated-suite accuracy được gắn metric riêng; chấm lại predictions không gọi LLM. Backticks không còn bị parser legacy làm sai điểm primary.
- DIN parser: hỗ trợ Markdown label, literal subquestion arrays với single/double quote; NESTED thiếu array fallback về original question, giữ hard generation + correction. MAC parser: nhận plain/fenced SQL và từ chối sentinel lỗi. Không đổi prompt để tối ưu theo gold.
- DAIL CoreNLP jars 3.9.2 từ Maven Central, Java 11 local; original tokenizer methods với lemma=True; loại allocation vector GloVe không được gọi trong linking. Có cache LIKE tương đương trên immutable DB copy, fallback SQLite cho wildcard/quotes/UTF-8 lỗi; đối chiếu source function và real smoke flags pass.
- MPNet weights thật được pin revision e8c3b32edf5434bc2275fc9bab85f82640a19130; candidate vector cache keyed by texts/model/revision. Train + dev schema/cell linking đã chạy đầy đủ. DAIL accounting cộng preliminary + final, không báo một call/câu khi pipeline thực tế có hai lượt.
- Không bổ sung source snapshot/diff theo yêu cầu người dùng. Giữ commit pins, provenance hashes, run logs và audit hiện có.

## Migration sang fork/submodule

Từ migration này, ba method dùng forks dưới tài khoản dleqhuy; hai evaluator trỏ upstream. Gitlinks ghim adapted commits; bảng audit phía trên mô tả baseline của benchmark trước migration. DIN/MAC compatibility classes và DAIL output/linking/embedding hooks đã chuyển vào `reproduction_adapter.py` trong từng fork; DAIL cell-link cache ở `reproduction_cell_link_cache.py`. Repo chính giữ transport/SQL guard và gọi các hooks này. Xem [workflow](repository_workflow.md) và [historical manifest](../experiments/historical/spider-v1-main-100.json).

Migration không sửa predictions/metrics/reports cũ và không gán adapted fork SHA cho benchmark đã hoàn thành. Manifest mới có state prepared; production runner xác minh clean trees, runtime/source/config/data trước khi gọi provider.
