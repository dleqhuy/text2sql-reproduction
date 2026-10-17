"""Vanilla schema serialization; upstreams retain their original templates."""

from scripts.common.io import read_json


def load_schemas(path):
    result = {}
    for schema in read_json(path):
        if schema["db_id"] in result:
            raise ValueError("Duplicate schema db_id")
        result[schema["db_id"]] = schema
    return result


def serialize(schema):
    tables = schema["table_names_original"]
    columns = schema["column_names_original"]
    lines = []
    primary = set(schema["primary_keys"])
    for index, table in enumerate(tables):
        fields = []
        for cid, ((tid, name), dtype) in enumerate(
            zip(columns, schema["column_types"], strict=True)
        ):
            if tid == index:
                fields.append(f"{name} {dtype}" + (" PRIMARY KEY" if cid in primary else ""))
        lines.append(f"Table {table} ({', '.join(fields)})")
    for first, second in schema["foreign_keys"]:
        a, b = columns[first], columns[second]
        lines.append(f"Foreign key: {tables[a[0]]}.{a[1]} = {tables[b[0]]}.{b[1]}")
    return "\n".join(lines)


def extract_sql(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].lower() not in {"```", "```sql", "```sqlite"} or lines[-1] != "```":
            raise ValueError("Unrecognized SQL fence")
        text = "\n".join(lines[1:-1]).strip()
    if not text or not text.lower().startswith(("select", "with")):
        raise ValueError("Response does not contain a SQL query")
    return text
