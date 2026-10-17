"""Parent-owned Vanilla baseline; research methods run through fork CLIs."""

from scripts.common.schema import extract_sql, serialize

VANILLA_PROMPT = """Write one SQLite query answering the question using this schema.
Return only the SQL query. Do not include explanations.

{schema}

Question: {question}
"""


class Vanilla:
    def __init__(self, llm, schemas):
        self.llm, self.schemas = llm, schemas

    def infer(self, row):
        prompt = VANILLA_PROMPT.format(
            schema=serialize(self.schemas[row["db_id"]]), question=row["question"]
        )
        return extract_sql(self.llm.complete(prompt))
