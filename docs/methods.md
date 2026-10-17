# Methods và protocol

Ba method forks tự chạy bằng `reproduction.run`; native source dùng provider/SQL guard của chính fork, không import repo chính. Repo chính chỉ gọi CLI bằng subprocess. Executable commits lấy từ gitlinks. [Upstream metadata](../configs/upstream_lock.json) giữ baseline để so diff; [development](development.md) hướng dẫn trace và cập nhật phiên bản.

| Method | Upstream baseline | Pipeline |
|---|---|---|
| Vanilla | Code của repo chính | Question + schema → một generation; không retrieval hoặc correction |
| DAIL-SQL | `2061f68112222083134a0c9e2877961ff315ff44` | Schema/cell linking → masked-question retrieval → preliminary SQL → skeleton retrieval → final SQL |
| DIN-SQL | `0474801616130413b024fd008b016a190684649e` | Schema linking → EASY/NON-NESTED/NESTED classification → generation → correction |
| MAC-SQL | `31a9df5e0d520be4769be57a4b9022e5e34a14f4` | Selector → Decomposer → Refiner, tối đa 3 rounds, giữ execution feedback |

## DAIL-SQL

Nguồn: [DAIL-SQL](https://github.com/BeachWang/DAIL-SQL); [fork integration](https://github.com/dleqhuy/DAIL-SQL/tree/codex/reproduction-integration). Original entry points: `data_preprocess.py`, `prompt/ExampleSelectorTemplate.py`, `ask_llm.py`.

Variant SQL representation, QA demonstrations, 9-shot, n=1, không self-consistency. Preliminary dùng `EUCDISQUESTIONMASK`; final dùng `EUCDISMASKPRESKLSIMTHR`. Giữ prompt factory/selectors gốc, chỉ train được dùng làm demonstration pool; tắt diagnostic quality cần dev gold.

CoreNLP 3.9.2 và các tokenizer methods gốc với lemma=True tạo linking cho 8.659 train + 1.034 dev. Không cấp phát GloVe vectors vì preprocessing không dùng chúng. `reproduction/cell_link_cache.py` tăng tốc hai mẫu LIKE literal; wildcard/quote/UTF-8 lỗi fallback SQLite. Đối chiếu original functions và 10 smoke questions được ghi ở [cell-link validation](../configs/dail_cell_link_validation.json).

MPNet weights/revision ở [embedding config](../configs/dail_embedding.json). Cache candidate vectors theo model/revision/texts; không đổi selection strategy. `get_tokenizer/count_tokens` gốc trả 0 nên context-budget diagnostics không đáng tin; dùng provider usage và generation cap 200/call. Accounting cộng preliminary + final; latency chưa gồm linking/retrieval offline.

## DIN-SQL

Nguồn: [Few-shot-NL2SQL-with-prompting](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting); [fork integration](https://github.com/dleqhuy/Few-shot-NL2SQL-with-prompting/tree/codex/reproduction-integration). Original prompts và functions nằm trong `DIN-SQL.py`.

`DIN-SQL.py` đã bỏ argv/key/gold side effects khi import, thay API cũ bằng native compatible client và chuyển main sang CLI. Loader import module bình thường, không còn rewrite AST. Test xác nhận original prompt constants/builders không đổi; giữ bốn stages, stop sequences và caps 600/350.

Classification parser tìm label theo các format được hỗ trợ; response trần `EASY` vẫn có thể gây parse error như `dev_000507` trong benchmark hiện tại. Khi NESTED thiếu subquestions, dùng câu hỏi gốc làm subproblem và log fallback; không bỏ generation/correction. Correction hỗ trợ full SELECT, continuation và fenced SQL.

## MAC-SQL

Nguồn: [MAC-SQL](https://github.com/wbbeyourself/MAC-SQL); [fork integration](https://github.com/dleqhuy/MAC-SQL/tree/codex/reproduction-integration). Original agents ở `core/agents.py`, vòng lặp/constants ở `core/chat_manager.py` và `core/const.py`.

Giữ classes/transitions gốc; `core/llm.py` gọi native compatible provider, không inject `sys.modules` và không load Azure config. `core/agents.py` giữ absolute DB path và dùng read-only SQL worker trực tiếp; bỏ Hello-world ping/gold logging trong standalone runner. Schema nhỏ có thể bỏ qua LLM pruning theo heuristic gốc.

Parser nhận plain SQL hoặc SQL fence cuối, từ chối error sentinel. Metadata connection read-only; Refiner gọi worker có timeout và nhận preview/error theo contract gốc. Generation cap mặc định 1024; execution feedback được giữ.

## Evaluation và môi trường

Primary metric dùng upstream `taoyds/test-suite-sql-eval`, baseline `e97acc546ecbee8fa27fa8dbf025ef61493a876c`; gọi comparison function gốc với read-only connection/deadline. Single-original-DB execution là metric riêng. Spider legacy baseline `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c` dùng cho reference/hardness; parser legacy có hạn chế backticks.

Root dùng `uv.lock`; mỗi fork giữ dependency lock riêng. Lệnh setup/chạy nằm trong [running](running.md).

## License đã kiểm tra

DAIL: Apache-2.0; DIN: MIT (header placeholder upstream); Spider evaluator: Apache-2.0. MAC có `training_scripts/LICENSE`, chưa thấy license inference áp dụng toàn root trong baseline đã đọc. Dataset theo nguồn Spider: CC BY-SA 4.0, attribution Yu et al. (2018).

<a id="protocol-va-metrics"></a>

## Protocol và metrics

### Dữ liệu và model

Fixed main 100 câu trên 20 DB, smoke 10 là tập con, DB-balanced round-robin seed 42 và output theo original dev order. [Dataset manifest](../data/splits/spider-v1.json) ghi IDs/hashes; train chỉ làm demonstrations. Dev gold chỉ dùng evaluation/hardness, không vào prompts hoặc retrieval. Mọi method dùng cùng input, schema/DB và model cấu hình.

[Runtime config](../configs/experiment.json): temperature 0, request timeout 90s, tối đa 3 attempts, 1.000 calls/run, 14.400s/run và SQL timeout 5s. Token caps giữ khác biệt stage: Vanilla/MAC 1024, DIN generation 600/correction 350, DAIL 200/call. DAIL là 9-shot QA hai lượt, không self-consistency.

### Metrics

Primary metric là **official Test Suite execution accuracy**, dùng 695 original/generated SQLite files thuộc 20 DB: `plug_value=false`, `keep_distinct=true`, seed 42. Evaluator commit được ghim bằng submodule; không đổi comparison logic gốc. Gold self-check cả 100 câu đã pass.

`--metric execution` chỉ chấm DB gốc bằng cùng engine; `--metric legacy` là reference có hạn chế backtick. Hai metric này không được gọi là Test Suite Accuracy. Mẫu số luôn là toàn bộ IDs, kể cả missing/API/parse/timeout/budget failures. SQL chạy read-only và có deadline; harness/gold errors không tính thành model errors.

Báo valid SQL, API requests, token totals/coverage và mean/median latency. DAIL cộng preliminary + final, chưa gồm offline linking/retrieval; unknown usage là null. Không quy đổi thành tiền nếu chưa có giá provider xác minh.

### Phạm vi kết luận

Smoke nằm trong main và đã dùng để sửa output handling, nên main không phải holdout độc lập. Benchmark hiện tại chạy inference tuần tự; latency chỉ mô tả experiment này, không phải phép đo throughput độc lập. Cùng model/temperature=0 không bảo đảm provider trả cùng output giữa các lượt. Đây là adapted reproduction trên subset, không phải full-dev hoặc điểm paper gốc.

Inference thật và official evaluation đã được kiểm chứng trên Python 3.11.16/macOS arm64. Cold setup toàn bộ dependencies/assets trên máy khác chưa được kiểm chứng; các lần kiểm tra fresh source clone dùng environments hiện có.

