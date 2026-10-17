# DAIL-SQL — hai lượt inference bằng code gốc

Upstream commit `2061f68112222083134a0c9e2877961ff315ff44`, source [DAIL-SQL](https://github.com/BeachWang/DAIL-SQL). Variant SQL representation, QA demonstrations, 9-shot, preliminary EUCDISQUESTIONMASK → final EUCDISMASKPRESKLSIMTHR, n=1, không self-consistency.

Đã hoàn thành preprocessing cho 8.659 train + 1.034 dev bằng CoreNLP 3.9.2, dùng chính GloVe.tokenize/tokenize_for_copying (lemma=True) của source. Không cấp phát vectors GloVe không được component dùng. Cache hai mẫu LIKE literal giữ nguyên flags; SQL wildcard/quote và UTF-8 lỗi fallback SQLite. Đối chiếu cả 10 câu smoke thật với function SQLite gốc đều khớp.

MPNet thật: all-mpnet-base-v2 revision `e8c3b32edf5434bc2275fc9bab85f82640a19130`, CPU inference, không training. Candidate vectors cache theo hash model/revision/texts, không đổi thuật toán retrieval. Factory/selectors và prompts gốc được giữ; source target không có dev gold, diagnostic gold-based quality bị tắt, train corpus/overlap/assets được kiểm tra.

Đã chạy smoke đầy đủ hai lượt: 10/10 outputs, TSA 8/10 với official generated databases. Runs `spider-v1-smoke-dail-preliminary`, `...-final`, aggregate `spider-v1-smoke-dail`. Main-100 đã hoàn thành cả hai lượt: TSA 76/100, DB gốc 87/100, tổng 200 API requests. Kết quả toàn bộ tại [benchmark report](../../reports/benchmark_100.md).

`prepare_dail_assets` tạo linking; `prepare_dail` tạo prompts từ pinned embedding config; `run_method --method dail_sql --dail-prompts <bundle>` inference; `aggregate_dail` cộng calls/usage/latency của cả hai lượt, giữ SQL final. [Runbook](../reproducibility.md) có commands và asset sources. Snapshot environment ở configs/environments/dail-requirements.txt, Maven jars/checksums ở configs/dail_corenlp_assets.json.

Giới hạn giữ nguyên: get_tokenizer/count_tokens của upstream trả 0 nên không dùng diagnostics đó làm token measurement/context enforcement. Generation cap 200 mỗi call, usage lấy provider. Latency aggregate chưa gồm offline linking/retrieval setup. Đây là adapted reproduction, không phải điểm GPT-4 lịch sử.
