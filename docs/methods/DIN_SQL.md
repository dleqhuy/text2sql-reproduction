# DIN-SQL — adapter implemented

Upstream: [Few-shot-NL2SQL-with-prompting](https://github.com/MohammadrezaPourreza/Few-shot-NL2SQL-with-prompting), commit `0474801616130413b024fd008b016a190684649e`. Adapter nạp prompt definitions bằng AST từ `DIN-SQL.py`, không viết lại prompts.

Đã audit argv line 437, credential stub sai cú pháp line 444, prompt makers từ 452, API generation/debug tại 572/587 và pipeline gốc tại 602. Loader thay đúng stub `API_KEY = #key` thành None trong bộ nhớ để parse; bỏ side effects và legacy API functions khỏi AST được chạy.

Giữ schema linking → classification EASY/NON-NESTED/NESTED → generation → self-correction, stop sequences và token caps gốc. Transport dùng model/env `LLM_*`, retry hữu hạn. Debugger có thể trả nguyên SELECT với model mới; adapter chỉ thêm prefix nếu output chưa có, vẫn giữ raw response.

Environment: `third_party/Few-shot-NL2SQL-with-prompting/.venv`, Python 3.11.16; snapshot `configs/environments/din-requirements.txt`. Chỉ cài inference dependencies, không cài stack training đầy đủ. Cả ba nhánh đã test offline; real provider fixture chạy đủ bốn calls, SQL hợp lệ và evaluator đúng 1/1.

CLI: `third_party/Few-shot-NL2SQL-with-prompting/.venv/bin/python -m scripts.run_method --help`, chọn `--method din_sql`. [Runbook](../reproducibility.md) có lệnh đầy đủ và flags. Artifact thành công: `runs/fixture-v3-din`. Đã hoàn thành smoke 10 Spider thật; xem [report](../../reports/spider_smoke.md). Main 100 đã hoàn thành, có kết quả trong benchmark report.

Orchestration đổi sang runner chung để bỏ gold prints và retry vô hạn. Adapter kiểm tra câu đánh giá trùng chuỗi hardcoded demonstrations; chưa có full dev để hoàn tất kiểm tra toàn corpus.

Parser hiện nhận Label quoted/plain hoặc một label Markdown duy nhất. NESTED thiếu subquestions dùng nguyên câu hỏi làm subproblem, vẫn chạy hard generation và correction; fallback được log. Đây là adaptation được công bố, không thêm gold hay bỏ stage. Smoke v3 đã đủ 10/10 SQL outputs, TSA 8/10. Kết quả main tại [benchmark report](../../reports/benchmark_100.md).
