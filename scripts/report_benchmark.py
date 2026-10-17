"""Generate comparison and error cases for the frozen spider-v1 main-100 runs."""


def main():
    import argparse
    import sys
    from collections import Counter
    from pathlib import Path

    from scripts.common.io import digest, file_hash, read_json, read_jsonl, write_json

    argparse.ArgumentParser(description=__doc__).parse_args()

    run_map = {
        "Vanilla": "spider-v1-main-vanilla",
        "DAIL-SQL": "spider-v1-main-dail",
        "DIN-SQL": "spider-v1-main-din",
        "MAC-SQL": "spider-v1-main-mac",
    }
    inputs = read_jsonl("data/prepared/spider-v1/main.jsonl")
    manifest = read_json("data/prepared/spider-v1/manifest.json")
    gold = {r["example_id"]: r for r in read_jsonl("data/prepared/spider-v1/gold.jsonl")}
    data = {}
    for name, folder in run_map.items():
        root = Path("runs") / folder
        tsa = read_json(root / "eval-test-suite/metrics.json")
        ex = read_json(root / "eval-execution/metrics.json")
        if (
            tsa["metric"] != "test_suite_execution_accuracy"
            or ex["metric"] != "single_database_execution_accuracy"
        ):
            raise ValueError("Benchmark report received mixed evaluation metrics")
        for metric in (tsa, ex):
            provenance = metric["evaluation_provenance"]
            if provenance["input_hash"] != digest(inputs) or provenance[
                "prediction_hash"
            ] != file_hash(root / "predictions.jsonl"):
                raise ValueError("Benchmark metric artifacts do not match inputs/predictions")
        assert tsa["n"] == ex["n"] == len(inputs) == 100
        assert tsa["evaluation_provenance"]["input_hash"] == digest(inputs)
        data[name] = {
            "folder": folder,
            "tsa": tsa,
            "ex": ex,
            "pred": {r["example_id"]: r for r in read_jsonl(root / "predictions.jsonl")},
            "evaluation": {
                r["example_id"]: r for r in read_jsonl(root / "eval-test-suite/evaluation.jsonl")
            },
            "base": {
                r["example_id"]: r for r in read_jsonl(root / "eval-execution/evaluation.jsonl")
            },
        }
    assert len({d["tsa"]["model"] for d in data.values()}) == 1
    model = next(iter(data.values()))["tsa"]["model"]
    sys.path.insert(0, "third_party/spider")
    from evaluation import Evaluator

    evaluator = Evaluator()
    dev = read_json("data/spider/dev.json")
    hardness = {
        r["example_id"]: evaluator.eval_hardness(dev[int(r["example_id"].split("_")[1])]["sql"])
        for r in inputs
    }
    summary = []
    for name, d in data.items():
        m = d["tsa"]
        summary.append(
            {
                "method": name,
                "run": d["folder"],
                "model": model,
                "n": 100,
                "test_suite_correct": m["correct"],
                "original_db_correct": d["ex"]["correct"],
                "valid_sql": m["valid_sql"],
                "api_requests": m["api_calls"]["observed_sum"],
                "prompt_tokens_observed": m["prompt_tokens"]["observed_sum"],
                "completion_tokens_observed": m["completion_tokens"]["observed_sum"],
                "prompt_token_coverage_n": m["prompt_tokens"]["coverage_n"],
                "completion_token_coverage_n": m["completion_tokens"]["coverage_n"],
                "mean_inference_s": m["latency_ms"]["mean"] / 1000,
                "median_inference_s": m["latency_ms"]["median"] / 1000,
                "statuses": m["statuses"],
            }
        )
    write_json(
        "reports/comparison.json",
        {
            "model": model,
            "input_hash": digest(inputs),
            "n": 100,
            "dbs": 20,
            "suite_files": 695,
            "metric": "test_suite_execution_accuracy",
            "plug_value": False,
            "keep_distinct": True,
            "sampling": manifest["algorithm"],
            "seed": 42,
            "difficulty_counts": dict(Counter(hardness.values())),
            "results": summary,
        },
    )
    lines = [
        "# Benchmark 100 câu Spider dev — 17/10/2026",
        "",
        f"Đã hoàn thành cả bốn method trên cùng 100 IDs của manifest [spider-v1](../data/splits/spider-v1.json). Model cấu hình: `{model}`; không training. Đây là subset 20 DB, không phải full Spider dev hoặc tái lập điểm paper gốc.",
        "",
        "## Kết quả",
        "",
        "| Method | Test Suite đúng/100 | DB gốc đúng/100 | SQL valid/100 | API requests | Mean inference (s/câu) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        lines.append(
            f"| {r['method']} | {r['test_suite_correct']} | {r['original_db_correct']} | {r['valid_sql']} | {r['api_requests']} | {r['mean_inference_s']:.2f} |"
        )
    lines += [
        "",
        "Primary metric dùng comparison engine official `taoyds/test-suite-sql-eval`, commit `e97acc546ecbee8fa27fa8dbf025ef61493a876c`, trên 695 original/generated SQLite files: plug_value=false, keep_distinct=true, seed=42. Cột DB gốc dùng cùng engine nhưng chỉ một DB/schema. Không dùng parser legacy bị lỗi backtick để kết luận quality.",
        "",
        "Mẫu số luôn 100, kể cả API/parse/SQL failures. DAIL cộng cả preliminary + final calls/tokens/latency; không bật self-consistency. Latency DAIL chưa gồm linking/retrieval offline. Các run có thời gian chồng lấp nên latency chỉ mô tả run này, không phải benchmark throughput độc lập.",
        "",
        "## Protocol và nguồn",
        "",
        f"- Sampling DB-balanced round-robin, seed 42; difficulty theo official legacy hardness function trên gold AST: {dict(Counter(hardness.values()))}. Không dùng hardness/gold trong prompts.",
        "- Smoke 10 là tập con của main 100 và đã dùng để sửa output-format handling; main không phải holdout độc lập. Không tinh chỉnh prompt theo gold main.",
        "- Cùng model/temperature=0/retry policy. Token caps giữ stage settings: Vanilla/MAC 1024; DIN 600 generation, 350 correction; DAIL 200/call.",
        "- Dữ liệu gốc và generated suites được pin hash: [Spider](../configs/spider_source.json), [test suite](../configs/test_suite_source.json). Gold self-check toàn bộ 100 IDs trên suites đã pass.",
        "- DAIL dùng CoreNLP tokenizer gốc, cache LIKE tương đương đã kiểm chứng, MPNet revision pin; không allocate GloVe vectors không được code sử dụng. DIN có fallback original question khi NESTED thiếu subquestions; MAC nhận plain/fenced SQL. Xem [audit](../docs/repo_audit.md).",
        "- Root/upstream envs được pin. Chưa kiểm chứng cold setup trên máy/platform khác. Không thêm per-run snapshot/diff source theo yêu cầu người dùng.",
        "",
        "## Usage ghi nhận",
        "",
        "| Method | Prompt tokens | Completion tokens | Usage coverage |",
        "|---|---:|---:|---:|",
    ]
    for r in summary:
        lines.append(
            f"| {r['method']} | {r['prompt_tokens_observed']} | {r['completion_tokens_observed']} | {r['prompt_token_coverage_n']}/100 prompt, {r['completion_token_coverage_n']}/100 completion |"
        )
    lines += [
        "",
        "Token sums là usage provider, chưa trừ cache discount; không suy ra chi phí tiền khi chưa có giá provider được xác minh.",
        "",
        "## Phân tích 8 trường hợp lỗi",
        "",
        "Chọn có quy tắc: ưu tiên lỗi pipeline hoặc câu đúng trên DB gốc nhưng không qua neighbor suites, rồi phủ DB khác nhau. Đây là case studies, không phải ước lượng tỷ trọng nguyên nhân trên toàn Spider.",
    ]
    candidates = []
    for row in inputs:
        eid = row["example_id"]
        if not any(not d["evaluation"][eid]["correct"] for d in data.values()):
            continue
        failure = any(
            d["pred"][eid]["status"] != "ok" or d["evaluation"][eid]["execution_status"] != "ok"
            for d in data.values()
        )
        accidental = any(
            d["base"][eid]["correct"] and not d["evaluation"][eid]["correct"] for d in data.values()
        )
        candidates.append((0 if failure else 1 if accidental else 2, eid, row))
    selected = []
    dbs = set()
    for _, eid, row in sorted(candidates):
        if row["db_id"] not in dbs:
            selected.append(row)
            dbs.add(row["db_id"])
        if len(selected) == 8:
            break
    case_notes = {
        "dev_000062": "DIN có prefix SELECT trước Markdown fence, khiến SQL không hợp lệ. Đây là lỗi format adapter/output, chưa phải bằng chứng sai logic NOT EXISTS bên trong.",
        "dev_000226": "DIN có lỗi SELECT trước fence. Ba method còn lại dùng UNION ALL để đếm hai đầu chuyến bay; gold dùng JOIN với OR, có thể khác multiplicity khi hai đầu trùng nhau. Đây là khác biệt cấu trúc cần kiểm tra ở DB counterexample, chưa xác nhận nguyên nhân duy nhất.",
        "dev_000410": "DIN có SELECT trước fence nên không execute được; không thể kết luận LEFT JOIN anti-join bên trong sai ngữ nghĩa chỉ từ score này.",
        "dev_000857": "DIN có SELECT trước fence; SQL lỗi format trước khi evaluator có thể kiểm tra aggregation/HAVING bên trong.",
        "dev_000012": "DIN thêm DISTINCT trong khi gold giữ duplicates. Với keep_distinct=true, khác biệt multiplicity có thể hiện trên generated DB dù DB gốc trả cùng kết quả.",
        "dev_000105": "Các prediction khác gold ở grouping theo ID so với tên Continent; Vanilla còn đổi JOIN thành LEFT JOIN và COUNT(*) thành COUNT(DISTINCT Id). Cần xét cả nhóm trùng tên và số dòng join, không chỉ tên cột output.",
        "dev_000283": "DAIL dùng COUNT(Employee_ID), gold dùng COUNT(*). COUNT(column) bỏ NULL; đây là khác biệt ngữ nghĩa có thể làm đổi thứ tự. Chưa cô lập nguyên nhân từ counterexample, kể cả tie ở LIMIT 1.",
        "dev_000373": "Vanilla/MAC dùng COUNT(Paragraph_ID) thay COUNT(*); Vanilla còn dùng LEFT JOIN. DAIL gần cấu trúc gold nhưng thêm tên vào GROUP BY. Các sai khác và tie khi LIMIT 1 cần được kiểm tra riêng, không suy ra nguyên nhân duy nhất từ score.",
    }
    for row in selected:
        eid = row["example_id"]
        lines += [
            "",
            f"### {eid} — {row['db_id']} ({hardness[eid]})",
            "",
            row["question"],
            "",
            "Gold:",
            "```sql",
            gold[eid]["query"],
            "```",
            "",
            "| Method | DB gốc | Test Suite | Status |",
            "|---|---|---|---|",
        ]
        for name, d in data.items():
            lines.append(
                f"| {name} | {'đúng' if d['base'][eid]['correct'] else 'sai'} | {'đúng' if d['evaluation'][eid]['correct'] else 'sai'} | {d['pred'][eid]['status']}/{d['evaluation'][eid]['execution_status']} |"
            )
        if any(
            d["base"][eid]["correct"] and not d["evaluation"][eid]["correct"] for d in data.values()
        ):
            lines += [
                "",
                "Quan sát: có lời giải đúng trên dữ liệu gốc nhưng không tương đương trên ít nhất một generated DB. Đây là lý do cần metric test-suite thay vì chỉ execution trên một DB.",
            ]
        elif any(d["evaluation"][eid]["execution_status"] != "ok" for d in data.values()):
            lines += [
                "",
                "Quan sát: có output không execute được hoặc lỗi pipeline; case vẫn ở mẫu số, không loại khỏi score.",
            ]
        else:
            lines += [
                "",
                "Quan sát: SQL execute được nhưng ít nhất một method trả denotation khác gold. Đối chiếu điều kiện, join, aggregation và giới hạn trong SQL dưới đây; không quy nguyên nhân cho agent chỉ từ accuracy.",
            ]
        lines += ["", "Đối chiếu SQL: " + case_notes[eid]]
        for name, d in data.items():
            if not d["evaluation"][eid]["correct"]:
                pred = d["pred"][eid]
                sql = pred["predicted_sql"] or str(pred["error"])
                lines += ["", name + " — prediction chưa qua test suite:", "````sql", sql, "````"]
    lines += [
        "",
        "## Artifacts và tái lập",
        "",
        "Mỗi run dưới có predictions, events/raw responses, checkpoints, config/provenance và hai thư mục evaluation với hashes/config/metrics:",
        "",
    ]
    for name, d in data.items():
        lines.append(f"- {name}: `runs/{d['folder']}/`.")
    lines += [
        "- DAIL parent runs: `runs/spider-v1-main-dail-preliminary/`, `runs/spider-v1-main-dail-final/`; aggregate chỉ giữ final SQL và cộng accounting, không rewrite outputs gốc.",
        "- [Machine-readable comparison](comparison.json), [commands](../docs/reproducibility.md), [implementation status](../docs/implementation/status.md).",
        "",
        "Inference/evaluation/report trên máy hiện tại đã hoàn tất. Việc đọc thêm các raw stages để phân tích sâu hoặc mở rộng full-dev là experiment tiếp theo, không nằm trong các score ở đây.",
    ]
    Path("reports/benchmark_100.md").write_text("\n".join(lines) + "\n")
    print("Wrote benchmark report and comparison JSON for all four methods")
    for r in summary:
        print(r["method"], r["test_suite_correct"], r["original_db_correct"], r["api_requests"])


if __name__ == "__main__":
    main()
