# Spider 1.0 — dữ liệu đã tải và kiểm tra

Spider 1.0 train/dev được tải từ nguồn Yale/Google Drive và kiểm tra checksum; raw data được Git ignore.

## Nguồn và tính toàn vẹn

- [Trang Spider chính thức](https://yale-lily.github.io/spider), Google Drive ID `1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J`.
- Archive: 205.800.266 bytes; CRC toàn archive hợp lệ.
- SHA-256: `00636695dabed6b5f4b8328a16b13e069a2f16591d5efcce57660669c85b121b`.
- Checksum khớp bản [mirror HAL-9001/spider-databases](https://huggingface.co/datasets/HAL-9001/spider-databases), revision `4a01bbac6520cd35b216db9e1724e5e1ada60aa4`. Đây là re-host độc lập, không phải nguồn xác thực bổ sung từ Yale.
- License dữ liệu: CC BY-SA 4.0; giữ attribution Spider (Yu et al., 2018).

## Cấu trúc local

```text
data/spider/
├── dev.json                 # 1.034 câu
├── train_spider.json        # 7.000 câu
├── train_others.json        # 1.659 câu
├── tables.json             # 166 schemas
├── database/               # 166 SQLite files
├── dev_gold.sql
├── train_gold.sql
└── README.txt
```

Importer chỉ lấy phần train/dev cần cho experiment; bỏ test set, test databases, Apple metadata và `.DS_Store`. Archive gốc vẫn chứa phần test. Không sửa nội dung JSON/SQLite được trích xuất.

Đã kiểm tra toàn bộ 166 schemas: bảng/cột khớp SQLite. Hash từng DB và bốn JSON nguồn được ghi trong [spider_source.json](../configs/spider_source.json). Dataset lớn được Git ignore.

## Tải hoặc import lại

Import archive local:

```bash
uv run python -m scripts.fetch_spider --archive /path/to/spider.zip
```

Đối với checkout mới chưa có `data/spider`, có thể tải trực tiếp hoặc chọn mirror pin revision; cả hai phải vượt **cùng checksum**, nếu nhận HTML quota page hoặc file khác thì importer từ chối:

```bash
uv run python -m scripts.fetch_spider
uv run python -m scripts.fetch_spider --source mirror
```

Chỉ chọn một lệnh tải. Importer từ chối overwrite thư mục dataset tồn tại, giải nén vào staging rồi publish khi đủ file; bản ghi nguồn mặc định ở `configs/spider_source.json`. Nhánh mirror chưa được tải thử vì lần retry nguồn chính thức đã thành công.

## Subset đã freeze

Đã chạy:

```bash
uv run python -m scripts.prepare_spider \
  --source data/spider --output data/prepared/spider-v1 \
  --size 100 --smoke-size 10 --seed 42
```

Main có 100 câu trên 20 DB; smoke 10 câu là tập con cố định, chọn DB-balanced với seed 42. Inference input tách khỏi gold. Manifest được lưu local ở `data/prepared/spider-v1/manifest.json` và bản theo dõi trong Git ở [data/splits/spider-v1.json](../data/splits/spider-v1.json). Hash nguồn gắn stable IDs theo original dev index; không resample riêng từng method.

DAIL preprocessing, embedding assets và official generated test-suite databases được mô tả trong [runbook](reproducibility.md).
