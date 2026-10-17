# Phase 1 — Clone, pin và audit upstream

**Phụ thuộc:** Phase 0 về contract và quy tắc Git. **Mục tiêu:** có integration map từ mã nguồn thực tế, giữ pipeline gốc.

## Đầu việc

- [ ] **P1-01 — Clone và pin.** Dùng các source URL trong [README](../../README.md), lưu clone vào đúng `third_party/` đã mô tả. Ghi remote, full commit SHA, ngày clone, license và trạng thái working tree. Không tự pull trong quá trình benchmark.
- [ ] **P1-02 — Dependency audit.** Ghi Python, dependency file, OpenAI SDK, retrieval/embedding dependencies, tài nguyên CPU/GPU cần thiết từ code. Tạo uv environment riêng cho từng repo; lưu dependency snapshot/lock khả dụng cùng lệnh cài thực tế.
- [ ] **P1-03 — Tìm integration points.** Dùng `rg` tìm API client, credential, endpoint/base URL, model, retry, input loader, prompt, SQLite execution, output writer và entrypoint. Ghi `file:line` gắn commit trong [repo_audit.md](../repo_audit.md).
- [ ] **P1-04 — Xác minh đường inference.** Xác định flags bằng parser/source hoặc help không phát sinh inference; nếu chỉ có notebook thì ghi cách chạy/export tối thiểu. Tách rõ lệnh đã chạy, lệnh dự kiến và blocker.
- [ ] **P1-05 — Thiết kế patch.** Chỉ thay phần API/paths/limits/logging/checkpoint/I/O cần thiết. Ghi lý do, phạm vi fidelity và cách apply vào clean commit. Chưa có bằng chứng thì giữ TODO, không điền theo tên gọi quen thuộc của method.
- [ ] **P1-06 — Chốt method settings.** Chọn variant, số demonstrations, retrieval config và agent bounds sau audit. Freeze trước đợt chính; mọi khác biệt với source hoặc protocol phải có ghi chú.

## Checklist theo method

| Method | Phải xác minh trong source |
|---|---|
| DAIL-SQL | Candidate pool từ train; selection/organization; preprocessing và embedding model; cache/index; có artifact/checkpoint pretrained nào cần tải; call phụ có dùng model khác không |
| DIN-SQL | Các stage thực sự được upstream triển khai; prompt/hardcoded demonstrations; classification/decomposition; correction; model ID ở từng stage |
| MAC-SQL | Đường GPT/API inference; Selector/Decomposer/Refiner; mọi chỗ execute SQL; vòng lặp refinement và điều kiện dừng; có hardcoded provider/model không |
| Evaluator Spider | Repo/commit evaluator, dependencies, cách gọi execution metric, options, gold format và order; đường SQLite execution cần timeout/read-only |

Không giả định API Compatible cung cấp embeddings hoặc tương thích legacy Completion. Nếu DAIL cần embeddings khác, ghi model/version và đưa vào setup riêng; không tự thay retrieval bằng random. Nếu một stage bắt buộc endpoint không hỗ trợ, tạo blocker hoặc đề xuất adaptation có mô tả ảnh hưởng.

## Artifacts

- Cập nhật [DAIL_SQL.md](../methods/DAIL_SQL.md), [DIN_SQL.md](../methods/DIN_SQL.md), [MAC_SQL.md](../methods/MAC_SQL.md) bằng code locations, input/output và lệnh có bằng chứng.
- Cập nhật `docs/repo_audit.md`; lưu manifests upstream/evaluator theo cấu trúc metadata đã thống nhất.
- Khi patch thực sự được áp dụng: tạo `patches/<method>.patch`, ghi SHA-256 và kiểm tra apply vào base commit sạch. Không lưu key trong diff/config.

## Gate nghiệm thu

- [ ] Ba upstream và evaluator có commit cụ thể, hoặc từng blocker được ghi rõ.
- [ ] Mỗi method có sơ đồ luồng từ Spider input tới final SQL, vị trí gọi API và dependency requirements.
- [ ] Mỗi method có kế hoạch adapter/patch dựa trên source; entrypoint chưa test được đánh dấu rõ.
- [ ] Có cách dựng lại từng môi trường mà không dựa vào root `.venv`.
- [ ] Chưa đánh dấu method “chạy được” chỉ vì clone/install thành công. Bằng chứng inference thuộc Phase 3.
