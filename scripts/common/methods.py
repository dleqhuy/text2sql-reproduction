"""Thin adapters that load original method prompts/classes from pinned checkouts."""

from scripts.common.schema import extract_sql, serialize
from scripts.common.sources import load_integration

VANILLA_PROMPT = """Write one SQLite query answering the question using this schema.
Return only the SQL query. Do not include explanations.

{schema}

Question: {question}
"""


def parse_din_classification(text, question):
    return load_integration("din_sql").parse_din_classification(text, question)


def parse_mac_sql(text):
    return load_integration("mac_sql").parse_mac_sql(text, extract_sql)


class Vanilla:
    def __init__(self, llm, schemas):
        self.llm, self.schemas = llm, schemas

    def infer(self, row):
        prompt = VANILLA_PROMPT.format(
            schema=serialize(self.schemas[row["db_id"]]), question=row["question"]
        )
        return extract_sql(self.llm.complete(prompt))
