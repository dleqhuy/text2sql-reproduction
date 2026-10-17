# Experiment references

- `manifests/main-v2.json`: cấu hình chuẩn bị cho CLI benchmark hiện tại, chưa chạy inference. Đây là manifest dùng trong quickstart.
- `manifests/native-main-100-20261017.json`: source, model, config và data references của benchmark đã hoàn tất, ứng với revision lúc chạy; giữ để trace kết quả.
- `completed/native-main-100-20261017.json`: kết quả đã hoàn thành, report/metrics và hashes của local artifacts. Predictions, responses và evaluations nằm trong ignored `runs/` directories.

Tạo và commit manifest từ source sạch theo [repository workflow](../docs/development.md). Source revisions lấy từ gitlinks. Khi đổi runtime/config/model/data, tạo manifest mới; không sửa source references của experiment đã hoàn thành. Không lưu secrets, datasets hoặc source snapshots ở đây.

Benchmark và tài liệu cũ đã được bỏ khỏi working tree; các file từng commit vẫn có trong Git history. Artifacts local đã xoá không được lưu trong Git.
