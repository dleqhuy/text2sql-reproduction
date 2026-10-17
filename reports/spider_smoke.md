> Cập nhật: bảng legacy bên dưới giữ lại để thể hiện lỗi evaluator cũ. Primary metric hiện là official Test Suite accuracy: Vanilla 7/10; DIN smoke v3 8/10; MAC smoke v2 7/10; DAIL hai lượt 8/10. Cả bốn có đủ 10 SQL outputs trong các smoke phiên bản mới. Xem [benchmark 100](benchmark_100.md) cho kết quả chính và [runbook](../docs/reproducibility.md) để tái lập.

# Spider dev smoke — 10 câu cố định

Ngày 17/10/2026. Dữ liệu chính thức tải lại thành công; nguồn và checksum tại [dataset](../docs/spider_dataset.md). Manifest: [spider-v1](../data/splits/spider-v1.json), main 100 câu trên 20 DB; smoke 10 câu trên 10 DB, seed 42, cùng ordered IDs cho ba methods.

Cả ba dùng cùng configured model, temperature 0. Không training. Đây là smoke để tìm lỗi integration, không phải full Spider dev score hoặc kết luận chất lượng từ main 100. DAIL chưa có production assets nên chưa chạy, không gán điểm 0.

| Method | N | Có SQL output | SQLite execute thành công | Legacy EX được ghi nhận | API requests |
|---|---:|---:|---:|---:|---:|
| vanilla | 10 | 10/10 | 10/10 | 8/10 | 10 |
| din_sql | 10 | 9/10 | 9/10 | 8/10 | 38 |
| mac_sql | 10 | 10/10 | 9/10 | 1/10 | 14 |

## Hạn chế quan trọng của evaluator legacy

MAC-SQL sinh nhiều SQL dùng backtick quanh identifiers. SQLite execute được, nhưng parser gốc `taoyds/spider/process_sql.py` không chấp nhận các identifiers này. Wrapper giữ empty-parse fallback của official legacy evaluator, nên kết quả EX bị ảnh hưởng bởi parser. Không dùng cột này để kết luận MAC kém hơn các method khác.

Đã xác minh hai câu `dev_000272` và `dev_000305`: SQL raw có backtick bị parser từ chối bằng AssertionError; bỏ backtick chỉ để chẩn đoán thì parse thành công. Các câu này chạy được trong SQLite và có dạng tương đương gold. Không sửa raw predictions hay âm thầm thay điểm đã ghi.

Trước khi chạy/main-report 100 câu, cần thêm evaluator execution hỗ trợ quoted identifiers (ưu tiên official Test Suite implementation), giữ tên metric/config và báo riêng so với legacy EX. Không thay SQL/gold tùy ý để nâng điểm.

## Lỗi integration/method cần tiếp tục xem xét

- DIN: 1 parse failure ở `dev_001010` và 1 câu có SQL chạy được nhưng khác gold logic ở `dev_001033`.
- MAC: 1 output sentinel “No SQL found” của parser upstream ở `dev_000664`; những câu khác cần tách lỗi SQL thật khỏi lỗi parser legacy. Không xem status=ok là query đúng hoặc valid SQL.
- Vanilla: 10 outputs đều có rows để đánh giá; correctness tính trên đủ 10 IDs, không lọc failures.

## Artifacts local

Mỗi `runs/spider-v1-smoke-{vanilla,din,mac}/` có run_config/provenance, events prompt/raw responses, checkpoints, normalized predictions, evaluation.jsonl, evaluation_config.json, metrics.json và comparison.md. Root code và upstream commits/dependencies/model/data fingerprints gắn với từng run. Không overwrite run cũ.

Main 100 inference/evaluation chưa chạy. Blocker download Spider đã giải quyết; DAIL CoreNLP/GloVe/MPNet và evaluator quoted-identifier support vẫn mở.
