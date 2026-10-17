# Kế hoạch implementation

Ngày khảo sát: **17/10/2026**. Trạng thái: **chưa triển khai**. Tài liệu này chuyển định hướng clone-first trong [README](../../README.md) thành các đầu việc có thể thực hiện và nghiệm thu. Các đường dẫn mã nguồn, cấu hình và CLI được đề xuất bên dưới chưa tồn tại, trừ khi được ghi rõ là hiện có.

## Hiện trạng đã kiểm tra

| Thành phần | Hiện trạng | Hệ quả |
|---|---|---|
| `README.md` | Có mục tiêu, Phase 0–4 và quy tắc reproduction | Giữ nguyên phạm vi: inference, không training |
| `docs/methods/*.md` | Có bốn runbook; các lệnh thực tế còn TODO | Phải audit upstream trước khi chốt integration |
| `docs/repo_audit.md` | Bảng mẫu, chưa có commit hay kết quả kiểm tra | Chưa thể khẳng định upstream chạy được |
| `docs/experiment_protocol.md` | Có nguyên tắc đánh giá và fairness | Cần cấu hình, dữ liệu và kiểm tra tự động để thực thi |
| `pyproject.toml` | Python >=3.10, Ruff trong dev group, runtime dependencies trống | Chưa có OpenAI client, dotenv loader hoặc runner |
| `.env` | Có giá trị cho `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Dùng endpoint OpenAI Compatible hiện có; chưa kiểm tra kết nối/model |
| `.gitignore` | Đã ignore `.env` và `.venv` | Bổ sung quy tắc cho dữ liệu/artifact khi triển khai |
| Mã, dữ liệu và môi trường | Chưa có `scripts/`, `third_party/`, `data/`, `runs/`, `uv.lock` | Bắt đầu từ scaffold và contract |

Chỉ kiểm tra tên biến và trạng thái có giá trị của env; không sao chép credential, endpoint hoặc model cụ thể vào tài liệu. Không gọi API trong lần lập kế hoạch này. Tài liệu dựa trên nội dung local; code và khả năng tương thích của upstream chưa được xác minh.

## Phạm vi và quyết định

- Tái hiện Vanilla, DAIL-SQL, DIN-SQL, MAC-SQL trên Spider 1.0 theo code gốc và patch tối thiểu. Vanilla là baseline do nhóm viết.
- Dùng một model sinh SQL qua OpenAI Compatible cho phép so sánh; ghi rõ mọi ngoại lệ về tham số hoặc capability. Không giả định endpoint có Responses API, embeddings, tool calling hay usage đầy đủ.
- Dùng `LLM_*` làm cấu hình chuẩn ở root. Biến `OPENAI_*` của upstream chỉ được ánh xạ cục bộ trong adapter khi cần.
- Root dùng uv và Ruff cho code của nhóm; mỗi upstream có môi trường uv riêng. Chỉ chốt Python/dependency của upstream sau audit.
- Smoke test trên 10 ID cố định; đợt chính trên 100–200 ID dev cố định. Chỉ train được cung cấp demonstrations; dev gold tách khỏi đường inference.
- Mọi lỗi vẫn phải có prediction row và được tính vào mẫu số EX. Không công bố subset score như full-dev hoặc điểm paper gốc.

## Các tài liệu thực thi

| Phase | Tài liệu | Đầu ra để qua gate |
|---|---|---|
| 0 | [Đóng băng protocol và scaffold](phase_0_foundation.md) | Contract, cấu hình, skeleton và kế hoạch chọn subset |
| 1 | [Clone, pin và audit upstream](phase_1_upstream_audit.md) | Commit, dependency, integration map và lệnh có bằng chứng |
| 2 | [OpenAI Compatible, dữ liệu và hạ tầng chạy](phase_2_runtime_and_data.md) | Provider probe, frozen subset, run storage, SQL guard và evaluator fixture |
| 3 | [Triển khai và chạy các method](phase_3_methods.md) | 1 → 10 → 100–200 câu/method, raw + normalized outputs |
| 4 | [Đánh giá và bàn giao](phase_4_evaluation.md) | Metrics, phân tích lỗi, báo cáo và hướng dẫn tái lập |
| Chung | [Contracts và artifacts](contracts.md) | Schema input/output, cấu hình, resume, denominator và provenance |

## Thứ tự thực hiện

1. Hoàn thành Phase 0 để thống nhất interface và các lựa chọn cần chốt.
2. Audit Phase 1. Có thể làm scaffold provider/dataset của Phase 2 trong thời gian chờ dữ liệu hoặc dependencies, nhưng chưa viết adapter dựa trên giả định về upstream.
3. Phase 2 phải chứng minh được đường API → output và fixture evaluator trước khi chạy benchmark.
4. Phase 3 theo thứ tự Vanilla → DAIL-SQL → DIN-SQL → MAC-SQL. Mỗi method qua gate riêng; nếu DAIL bị chặn thì tiếp tục method khác và ghi blocker.
5. Chỉ chạy đợt chính của một method sau khi smoke của method đó và shared evaluator đạt yêu cầu; Phase 4 đối chiếu completeness trước khi tổng hợp.

## Ước lượng công việc

Ước lượng là ngày công, chưa gồm thời gian xin dữ liệu, tải artifact, API latency/rate limit hoặc chờ xử lý upstream. Không phải cam kết lịch.

| Hạng mục | Ước lượng |
|---|---:|
| Phase 0 | 0,5–1 ngày |
| Phase 1 | 1–2 ngày |
| Phase 2 | 2–3 ngày |
| Phase 3 | 4–6 ngày, phụ thuộc độ tương thích upstream |
| Phase 4 | 1–2 ngày |

## Theo dõi và definition of done

Các checkbox trong từng phase là backlog, chưa phải kết quả đã xác minh. Khi hoàn thành một việc, ghi lệnh thực tế, artifact, ngày chạy và trạng thái vào runbook/audit tương ứng. Mỗi phase nên thành một thay đổi review được; patch từng upstream lưu riêng.

- [ ] Các method khả thi có commit, patch hash, dependency manifest và lệnh đã chạy.
- [ ] Cùng manifest dev, DB/schema fingerprint và model sinh SQL giữa các method.
- [ ] Không có dev gold trong prompt/retrieval; SQL chỉ chạy read-only, có giới hạn thời gian.
- [ ] Resume không tạo kết quả trùng hoặc trộn cấu hình; lỗi và usage được ghi trung thực.
- [ ] Kết quả đầy đủ trên manifest, metrics tính đúng mẫu số, báo cáo giới hạn rõ ràng.
- [ ] Có thể dựng lại môi trường và chạy smoke theo runbook.

Nếu upstream không chạy được sau các patch tương thích tối thiểu, lưu nguyên nhân và bằng chứng. Báo cáo chỉ gồm các method thực sự hoàn thành; mục tiêu bốn method còn thiếu phải được ghi là chưa đạt, không thay bằng thuật toán tự viết rồi giữ nhãn reproduction.
