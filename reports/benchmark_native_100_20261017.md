# Benchmark native CLI — 100 câu Spider dev, 17/10/2026

Chạy inference cho cả bốn method trên cùng 100 câu/20 DB đã cố định. Model: `cx/gpt-6-luna`, temperature=0. DIN, MAC và hai bước DAIL chạy qua native CLI của fork; Vanilla chạy tại repo chính. Các run inference được chạy tuần tự.

| Method | Test Suite đúng/100 | DB gốc đúng/100 | SQL valid/100 | API requests | Mean inference (s/câu) |
|---|---:|---:|---:|---:|---:|
| Vanilla | 64 | 77 | 99 | 100 | 2.03 |
| DAIL-SQL | 74 | 85 | 100 | 200 | 4.50 |
| DIN-SQL | 78 | 87 | 99 | 400 | 12.31 |
| MAC-SQL | 67 | 83 | 100 | 125 | 3.95 |

## Protocol

- Cùng 100 IDs cố định: DB-balanced round-robin, seed 42; easy 22, medium 41, hard 20, extra 17. Không training. Smoke 10 là tập con đã dùng để sửa compatibility handling, nên đây không phải holdout độc lập hoặc full Spider dev.
- Primary metric: official `taoyds/test-suite-sql-eval`, commit `e97acc546ecbee8fa27fa8dbf025ef61493a876c`, 695 original/generated SQLite files; plug_value=false, keep_distinct=true, seed=42. Cột DB gốc dùng cùng engine trên một DB/schema. Gold self-check pass cho tất cả IDs ở mỗi lần chấm.
- Mẫu số luôn 100, gồm cả API/parse/SQL failures. DAIL cộng cả preliminary và final calls/tokens/latency, n=1, không self-consistency. Mean inference không gồm chuẩn bị linking/retrieval offline; không phải phép đo throughput trên phần cứng độc lập.
- Token caps: Vanilla/MAC 1024; DIN 600 cho linking/classification/generation và 350 cho correction; DAIL 200/call. Retry tối đa 3 attempts, timeout 90 giây/request.
- Source, model, config và data được khóa trong [prepared manifest](../experiments/manifests/native-main-100-20261017.json). Production preflight kiểm tra source sạch và gitlinks đúng trước mỗi run.

## Usage

| Method | Prompt tokens | Completion tokens | Usage coverage |
|---|---:|---:|---:|
| Vanilla | 268458 | 5874 | 100/100 prompt; 100/100 completion |
| DAIL-SQL | 648529 | 14656 | 100/100 prompt; 100/100 completion |
| DIN-SQL | 1828502 | 30761 | 98/100 prompt; 98/100 completion |
| MAC-SQL | 525342 | 10514 | 100/100 prompt; 100/100 completion |

Token sums chỉ cộng các câu có đủ số đo usage. DIN có hai câu thiếu usage do request thất bại/retry, nên số token trên không phải tổng đầy đủ của run. Không suy ra chi phí tiền.

## Lỗi quan sát

DIN kết thúc với 99 outputs thành công và một `parse_error` tại `dev_000507`: classification response là `EASY` dạng trần, parser của revision đã pin từ chối format này trước generation. Câu này vẫn ở mẫu số 100; không sửa parser hoặc chạy chọn lọc lại trong experiment. Hai request DIN thất bại đã được retry; tổng 400 attempts bao gồm retries. Các method còn lại và hai lượt DAIL đều có 100/100 trạng thái inference `ok`; SQL có execute được hay không được kiểm tra riêng khi chấm.

Vanilla có một SQL không execute được tại `dev_001032`: output còn placeholder `:code` chưa được bind, nên evaluator ghi `sql_error`. Đây là lý do inference có 100 trạng thái `ok` nhưng chỉ 99 SQL valid.

## Artifacts và chạy lại

[Comparison JSON](comparison_native_100_20261017.json) chứa metrics. [Completed record](../experiments/completed/native-main-100-20261017.json) ghi hashes của artifacts. Predictions/raw responses/checkpoints được giữ local trong các thư mục sau:

- `runs/spider-v1-native-20261017-vanilla/`: predictions, run config và hai thư mục `eval-test-suite/`, `eval-execution/`.
- `runs/spider-v1-native-20261017-dail/`: predictions, run config và hai thư mục `eval-test-suite/`, `eval-execution/`.
- `runs/spider-v1-native-20261017-din/`: predictions, run config và hai thư mục `eval-test-suite/`, `eval-execution/`.
- `runs/spider-v1-native-20261017-mac/`: predictions, run config và hai thư mục `eval-test-suite/`, `eval-execution/`.
- `runs/spider-v1-native-20261017-dail-preliminary/` và `runs/spider-v1-native-20261017-dail-final/`: hai run native; aggregate giữ SQL cuối và cộng usage.
- Hai bundles `runs/spider-v1-native-20261017-dail-{preliminary,final}-prompts.json` được tạo lại từ source fork hiện tại và MPNet đã pin.

Với runtime hiện tại, tạo manifest mới theo [development](../docs/development.md#experiment-manifests), rồi chạy `python -m scripts.benchmark --experiment-manifest <new-manifest> --run-dir runs/<new-run>`. Pipeline tự tạo hai bundles DAIL, chạy bốn method và chấm hai metrics. Manifest ở trên tham chiếu revision khi benchmark này chạy; giữ nguyên nó để trace kết quả.
