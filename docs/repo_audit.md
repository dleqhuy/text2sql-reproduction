# Method audit và adaptations

Ba method forks tự chạy bằng `reproduction.run`; native source dùng provider/SQL guard của chính fork, không import repo chính. Repo chính chỉ gọi CLI bằng subprocess. Executable commits lấy từ gitlinks. [Upstream metadata](../configs/upstream_lock.json) giữ baseline để so diff; [workflow](repository_workflow.md) hướng dẫn trace và cập nhật phiên bản.

| Method | Upstream baseline | Pipeline |
|---|---|---|
| Vanilla | Code của repo chính | Question + schema → một generation; không retrieval hoặc correction |
| DAIL-SQL | `2061f68112222083134a0c9e2877961ff315ff44` | Schema/cell linking → masked-question retrieval → preliminary SQL → skeleton retrieval → final SQL |
| DIN-SQL | `0474801616130413b024fd008b016a190684649e` | Schema linking → EASY/NON-NESTED/NESTED classification → generation → correction |
| MAC-SQL | `31a9df5e0d520be4769be57a4b9022e5e34a14f4` | Selector → Decomposer → Refiner, tối đa 3 rounds, giữ execution feedback |

## DAIL-SQL

Nguồn: [DAIL-SQL](https://github.com/BeachWang/DAIL-SQL); [fork integration](https://github.com/dleqhuy/DAIL-SQL/tree/codex/reproduction-integration). Original entry points: `data_preprocess.py`, `prompt/ExampleSelectorTemplate.py`, `ask_llm.py`.

Variant SQL representation, QA demonstrations, 9-shot, n=1, không self-consistency. Preliminary dùng `EUCDISQUESTIONMASK`; final dùng `EUCDISMASKPRESKLSIMTHR`. Giữ prompt factory/selectors gốc, chỉ train được dùng làm demonstration pool; tắt diagnostic quality cần dev gold.

CoreNLP 3.9.2 và các tokenizer methods gốc với lemma=True tạo linking cho 8.659 train + 1.034 dev. Không cấp phát GloVe vectors vì preprocessing không dùng chúng. `reproduction_cell_link_cache.py` tăng tốc hai mẫu LIKE literal; wildcard/quote/UTF-8 lỗi fallback SQLite. Đối chiếu original functions và 10 smoke questions được ghi ở [cell-link validation](../configs/dail_cell_link_validation.json).

MPNet weights/revision ở [embedding config](../configs/dail_embedding.json). Cache candidate vectors theo model/revision/texts; không đổi selection strategy. `get_tokenizer/count_tokens` gốc trả 0 nên context-budget diagnostics không đáng tin; dùng provider usage và generation cap 200/call. Accounting cộng preliminary + final; latency chưa gồm linking/retrieval offline.

## DIN-SQL

Nguồn: [Few-shot-NL2SQL-with-prompting](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting); [fork integration](https://github.com/dleqhuy/Few-shot-NL2SQL-with-prompting/tree/codex/reproduction-integration). Original prompts và functions nằm trong `DIN-SQL.py`.

`DIN-SQL.py` đã bỏ argv/key/gold side effects khi import, thay API cũ bằng native compatible client và chuyển main sang CLI. Loader import module bình thường, không còn rewrite AST. Test xác nhận original prompt constants/builders không đổi; giữ bốn stages, stop sequences và caps 600/350.

Classification parser nhận quoted/plain/Markdown label. Khi NESTED thiếu subquestions, dùng câu hỏi gốc làm subproblem và log fallback; không bỏ generation/correction. Correction hỗ trợ full SELECT, continuation và fenced SQL. Bốn output lỗi fence trong benchmark cũ vẫn giữ nguyên và tính sai; parser mới chưa được dùng để gán lại điểm cho chúng.

## MAC-SQL

Nguồn: [MAC-SQL](https://github.com/wbbeyourself/MAC-SQL); [fork integration](https://github.com/dleqhuy/MAC-SQL/tree/codex/reproduction-integration). Original agents ở `core/agents.py`, vòng lặp/constants ở `core/chat_manager.py` và `core/const.py`.

Giữ classes/transitions gốc; `core/llm.py` gọi native compatible provider, không inject `sys.modules` và không load Azure config. `core/agents.py` giữ absolute DB path và dùng read-only SQL worker trực tiếp; bỏ Hello-world ping/gold logging trong standalone runner. Schema nhỏ có thể bỏ qua LLM pruning theo heuristic gốc.

Parser nhận plain SQL hoặc SQL fence cuối, từ chối error sentinel. Metadata connection read-only; Refiner gọi worker có timeout và nhận preview/error theo contract gốc. Generation cap mặc định 1024; execution feedback được giữ.

## Evaluation và môi trường

Primary metric dùng upstream `taoyds/test-suite-sql-eval`, baseline `e97acc546ecbee8fa27fa8dbf025ef61493a876c`; gọi comparison function gốc với read-only connection/deadline. Single-original-DB execution là metric riêng. Spider legacy baseline `b7b5b8c890cd30e35427348bb9eb8c6d1350ca7c` dùng cho reference/hardness; parser legacy có hạn chế backticks.

Root dùng `uv.lock`; từng fork giữ `requirements-compatible.lock.txt` cho môi trường của mình. DIN/MAC chỉ cần inference dependencies; DAIL lock bao gồm retrieval/preprocessing dependencies. [Runbook](reproducibility.md) chứa commands; [protocol](experiment_protocol.md) định nghĩa so sánh; [benchmark](../reports/benchmark_100.md) ghi kết quả trước migration.

## License đã kiểm tra

DAIL: Apache-2.0; DIN: MIT (header placeholder upstream); Spider evaluator: Apache-2.0. MAC có `training_scripts/LICENSE`, chưa thấy license inference áp dụng toàn root trong baseline đã đọc. Dataset theo nguồn Spider: CC BY-SA 4.0, attribution Yu et al. (2018).
