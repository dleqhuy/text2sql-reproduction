# MAC-SQL — adapter implemented

Upstream: [MAC-SQL](https://github.com/wbbeyourself/MAC-SQL), commit `31a9df5e0d520be4769be57a4b9022e5e34a14f4`. Chọn API inference, không training/SQL-Llama.

Đã audit `core/api_config.py` (Azure/hardcoded model), `core/llm.py` (legacy API/retry), `core/agents.py:42,598,661` (Selector/Decomposer/Refiner), `core/agents.py:672` (execute), `core/const.py:1` (MAX_ROUND=3).

Adapter import chính các class agent gốc và giữ thứ tự/điều kiện dừng của ChatManager.start. Bridge thay transport trước khi import, không load Azure config. Bỏ Hello-world ping/gold metadata; thêm idx cho logger. Khôi phục absolute DB root sau khi Selector strip leading slash.

Metadata connection read-only; Refiner worker chạy SQL có timeout, trả preview/error theo contract gốc. Giữ execution feedback. Model/temp từ config chung; token cap mặc định 1024; MAX_ROUND=3.

Environment `third_party/MAC-SQL/.venv`, Python 3.11.16; snapshot `configs/environments/mac-requirements.txt`. CLI: `third_party/MAC-SQL/.venv/bin/python -m scripts.run_method --help`, chọn `--method mac_sql`. Lệnh đầy đủ ở [runbook](../reproducibility.md).

Real provider fixture `runs/fixture-v2-mac` sinh SQL hợp lệ, evaluator đúng 1/1. Schema nhỏ skip LLM Selector theo heuristic gốc; không phải tắt agent. Test offline có SQL sai để buộc Refiner sửa qua execution feedback. Đã chạy cùng smoke 10 Spider thật, gồm các schema kích hoạt pruning; xem [report](../../reports/spider_smoke.md). Main 100 đã hoàn thành.

Parser hiện nhận SQL thuần hoặc code fence (lấy SQL block cuối như source); sentinel lỗi không được coi là final SQL hợp lệ. Agent classes, transitions và refinement vẫn giữ nguyên. Smoke v2 đủ 10/10 outputs, TSA 7/10. Main 100 đã hoàn thành; xem [benchmark report](../../reports/benchmark_100.md).
