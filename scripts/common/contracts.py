"""Fail closed on ambiguous identity or prediction status."""

METHODS = {"vanilla", "dail_sql", "din_sql", "mac_sql"}
STATUSES = {
    "ok",
    "api_error",
    "timeout",
    "parse_error",
    "method_error",
    "missing_prediction",
    "budget_exceeded",
}


def validate_inputs(rows):
    seen = set()
    for row in rows:
        if set(row) != {"example_id", "db_id", "question"}:
            raise ValueError("Inference input must contain only example_id, db_id, question")
        if any(not isinstance(v, str) or not v.strip() for v in row.values()):
            raise ValueError("Input fields must be nonempty strings")
        if row["example_id"] in seen:
            raise ValueError("Duplicate input ID")
        seen.add(row["example_id"])
    if not rows:
        raise ValueError("Input manifest is empty")


def failure(row, method, model, status, message, stage="inference"):
    result = {key: row[key] for key in ("example_id", "db_id")}
    result.update(
        method=method,
        model=model,
        status=status,
        predicted_sql=None,
        latency_ms=None,
        api_calls=None,
        prompt_tokens=None,
        completion_tokens=None,
        error={"type": status, "stage": stage, "message": message},
    )
    return result


def validate_predictions(rows, inputs, require_complete=True):
    validate_inputs(inputs)
    expected = {r["example_id"]: r for r in inputs}
    seen = set()
    for row in rows:
        eid = row.get("example_id")
        if eid not in expected or eid in seen:
            raise ValueError("Unknown or duplicate prediction ID")
        seen.add(eid)
        if row.get("db_id") != expected[eid]["db_id"]:
            raise ValueError("Prediction db_id mismatch")
        if row.get("method") not in METHODS or row.get("status") not in STATUSES:
            raise ValueError("Invalid method/status")
        if not isinstance(row.get("model"), str) or not row["model"]:
            raise ValueError("Missing prediction model")
        if row["status"] == "ok":
            if not isinstance(row.get("predicted_sql"), str) or not row["predicted_sql"].strip():
                raise ValueError("Successful prediction needs SQL")
            if row.get("error") is not None:
                raise ValueError("Successful prediction cannot have an error")
        else:
            error = row.get("error")
            if not isinstance(error, dict) or not {"type", "stage", "message"} <= error.keys():
                raise ValueError("Failure needs structured error")
        for name in ("latency_ms", "api_calls", "prompt_tokens", "completion_tokens"):
            if name not in row:
                raise ValueError(f"Missing measurement field: {name}")
            value = row[name]
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
            ):
                raise ValueError(f"Invalid measurement: {name}")
    if require_complete and seen != set(expected):
        raise ValueError("Incomplete predictions")
