"""Normalize ID-tagged native SQL rows or line outputs with an explicit ordered sidecar."""

from scripts.common.contracts import STATUSES, failure, validate_inputs, validate_predictions


def normalize(inputs, native, method, model, sql_key="predicted_sql"):
    validate_inputs(inputs)
    expected = {r["example_id"]: r for r in inputs}
    found = {}
    for item in native:
        eid = item.get("example_id")
        if eid not in expected or eid in found:
            raise ValueError("Unknown or duplicate native output ID")
        row = expected[eid]
        if item.get("db_id", row["db_id"]) != row["db_id"]:
            raise ValueError("Native db_id mismatch")
        result = failure(row, method, model, "parse_error", "Native SQL is empty", "normalization")
        sql = item.get(sql_key)
        if isinstance(sql, str) and sql.strip():
            result.update(status="ok", error=None, predicted_sql=sql.strip())
        if item.get("status") in STATUSES - {"ok"}:
            result = failure(
                row, method, model, item["status"], "Upstream reported failure", "normalization"
            )
        if "variant" in item:
            result["variant"] = item["variant"]
        for key in ("latency_ms", "api_calls", "prompt_tokens", "completion_tokens"):
            result[key] = item.get(key)
        found[eid] = result
    result = [
        found.get(row["example_id"])
        or failure(
            row,
            method,
            model,
            "missing_prediction",
            "No native output for selected example",
            "normalization",
        )
        for row in inputs
    ]
    validate_predictions(result, inputs)
    return result
