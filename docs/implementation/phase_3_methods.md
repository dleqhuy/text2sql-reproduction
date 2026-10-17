# Phase 3 — Triển khai và chạy các method

**Phụ thuộc:** gate hạ tầng Phase 2, và audit của method tương ứng. **Mục tiêu:** mỗi method sinh SQL trên cùng manifest bằng pipeline được bảo toàn và có provenance.

## Gate chung: 1 → 10 → 100–200

1. **Một câu thuộc smoke:** lưu prompt/stages/raw response/final SQL, xác nhận config/model/ID, không có dev gold và không có execute với write access. Failure phải thành row có status.
2. **Cùng smoke 10:** chạy hết manifest, normalize, đánh giá bằng shared evaluator; thử resume sau interruption có kiểm soát. EX thấp không tự động là implementation lỗi, nhưng cần xem output/stages để phân biệt lỗi logic với lỗi tích hợp.
3. **Freeze trước đợt chính:** chốt method settings, patch, model, dependency và budgets; ước lượng call/token/time từ smoke. Nếu không có giá hoặc usage thì ghi chưa biết, chỉ đặt giới hạn đo được.
4. **Đợt chính:** chạy cùng manifest chính, thư mục run mới, ghi tất cả failed/skipped rows; kiểm tra completeness và provenance trước khi đánh dấu completed.

Các thay đổi do debug trên smoke phải ghi lịch sử. Không tinh chỉnh prompts theo gold của tập chính rồi giữ nhãn cùng một protocol. Nếu thay config/prompt sau khi xem kết quả chính, tạo experiment mới và công bố điều đó.

## P3-A — Vanilla trước

- [ ] Implement `scripts/run_vanilla.py`: nhận input đã bỏ gold, schema đầy đủ của DB, gọi provider, extract SQL và ghi artifacts.
- [ ] Freeze prompt template có version/hash: question + schema, yêu cầu trả SQL. Không đưa vài-shot examples, schema pruning hoặc self-correction vào baseline một-call ban đầu.
- [ ] Extract response có code fence/whitespace một cách bảo thủ; không sửa ngữ nghĩa SQL hoặc tự chạy nhiều lần để lấy câu đúng. Giữ raw response.
- [ ] Dùng read-only validation để ghi execution status; không đưa feedback trở lại model ở baseline này. Transport retry vẫn được tính call và không phải correction.
- [ ] Cập nhật [VANILLA.md](../methods/VANILLA.md) với lệnh đã test, arguments, prompt version, output và metric smoke.

**Nghiệm thu:** đường end-to-end root config → fixed subset → prediction → evaluator hoạt động; mỗi câu thành công có một generation response, không có correction stage.

## P3-B — DAIL-SQL

- [ ] Chạy preprocessing và tạo candidate pool/index theo variant upstream đã audit; chỉ dùng train cho demonstrations.
- [ ] Pin model/artifact embedding và preprocessing config; lưu fingerprint cache, không tái dùng cache từ dataset/model khác.
- [ ] Giữ demonstration selection và prompt organization. Log selected example IDs và thông tin stage có thể thu được để kiểm tra leakage/fidelity.
- [ ] Patch API Compatible, input subset và output mapping tối thiểu. Tham số model phải tới mọi generation call, không chỉ entrypoint ngoài cùng.
- [ ] Normalize native output theo sidecar ID; giữ nguyên raw upstream artifacts.
- [ ] Lưu patch và cập nhật [DAIL_SQL.md](../methods/DAIL_SQL.md) sau gate 1/10/main.

**Nghiệm thu:** retrieval thật của variant đã chọn chạy được; demonstrations truy xuất về train; không âm thầm thay bằng random hoặc bỏ preprocessing khi dependencies lỗi.

## P3-C — DIN-SQL

- [ ] Dùng entrypoint/script/notebook được xác minh. Nếu chuyển notebook sang script, chỉ thay orchestration và ghi diff, giữ prompt/stages.
- [ ] Bảo toàn schema linking, classification/decomposition, generation và correction theo khả năng thực tế của source đã pin. Stage conditional có thể được bỏ qua theo logic gốc, nhưng không tắt tùy ý để giảm call.
- [ ] Kiểm tra demonstrations hardcoded và nguồn của chúng; lưu mapping stage/model/retry.
- [ ] Log intermediate outputs và final SQL; stage failure có lỗi gắn tên stage, không lấy output trung gian làm final SQL một cách ngầm định.
- [ ] Lưu patch và cập nhật [DIN_SQL.md](../methods/DIN_SQL.md) với lệnh thực tế và deviation.

**Nghiệm thu:** đối chiếu trace với source cho một câu; các nhánh được upstream hỗ trợ được thể hiện trong smoke hoặc fixture riêng khi smoke không bao phủ.

## P3-D — MAC-SQL

- [ ] Chọn đúng đường API inference. Giữ Selector, Decomposer, Refiner và execution feedback theo source.
- [ ] Route mọi lần execute qua SQL guard đã kiểm tra; refinement vẫn nhận được result/error phù hợp để hoạt động.
- [ ] Freeze số vòng/call/time per question. Phân biệt iteration limit của method, transport retry và run-level budget.
- [ ] Log agent transitions, SQL trước/sau refinement, feedback và điều kiện dừng. SQL invalid cuối cùng được giữ để đánh giá, không xóa câu thất bại.
- [ ] Kiểm tra model mapping tại mọi agent; không để hardcoded model đi ra provider khác ngoài config mà không ghi nhận.
- [ ] Lưu patch và cập nhật [MAC_SQL.md](../methods/MAC_SQL.md).

**Nghiệm thu:** trace cho thấy role transitions, execution feedback và điều kiện dừng; kiểm tra case lỗi kích hoạt refinement bằng fixture riêng nếu smoke không có case đó.

## Normalizer dùng chung

- [ ] Implement `scripts/normalize_outputs.py` với parser riêng theo native format đã audit, dùng [contracts](contracts.md).
- [ ] Giữ native output và mapping; từ chối duplicate/unknown ID hoặc order không xác định.
- [ ] Xuất đủ final rows kể cả upstream crash giữa chừng; rows còn thiếu có trạng thái và run vẫn mang trạng thái interrupted/failed phù hợp.
- [ ] Kiểm tra normalizer bằng fixtures nhỏ đại diện từng format; không dùng một regex chung để đoán SQL của cả bốn method.

## Bằng chứng cần ghi cho mỗi method

| Bằng chứng | Nơi lưu |
|---|---|
| CLI, cwd, interpreter, input/output, date và status thực tế | `docs/methods/<METHOD>.md` |
| Base commit, file:line, patch, lý do và fidelity deviation | `docs/repo_audit.md`, `patches/` |
| Frozen config, run metadata, logs, raw/final rows | `runs/<run_id>/` |
| Smoke metrics và blocker nếu có | Runbook và summary tương ứng |

Không tạo CLI upstream giả trong tài liệu. CLI root do nhóm viết phải có help và validation phù hợp; lệnh upstream chỉ điền sau khi xác minh.
