"""Equivalent indexes for the two literal LIKE templates in original DAIL cell linking.

Only use on immutable preprocessing copies. Wildcards/quotes/other SQL go to SQLite unchanged.
The original helper consumes result rows only as a truth value.
"""

import re
import sqlite3

ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


class CellLinkConnection:
    def __init__(self, connection):
        self.connection = connection
        self.indexes = {}
        self.ignore_case = bool(connection.execute("SELECT 'A' LIKE 'a'").fetchone()[0])
        self.blob_matches = bool(connection.execute("SELECT X'61' LIKE 'a'").fetchone()[0])

    def cursor(self):
        return CellLinkCursor(self)

    def index(self, table, column):
        key = (table, column)
        if key not in self.indexes:
            # Preserve errors from the unquoted identifier syntax used by upstream.
            self.connection.execute(f"SELECT {column} FROM {table} LIMIT 0")
            cursor = self.connection.execute(
                f'SELECT CAST("{column}" AS TEXT), typeof("{column}") FROM "{table}"'
            )
            partial, exact = set(), set()
            for value, kind in cursor:
                if value is None or (kind == "blob" and not self.blob_matches):
                    continue
                value = value.split("\x00", 1)[0]  # SQLite LIKE terminates text at NUL.
                normalized = value.translate(ASCII_LOWER) if self.ignore_case else value
                tokens = [
                    token for token in normalized.split(" ") if token and not is_number(token)
                ]
                # Numeric question tokens take the original numeric-link branch, never these LIKEs.
                if tokens:
                    partial.update(tokens)
                    exact.add(normalized)
            self.indexes[key] = partial, exact
        return self.indexes[key]


class CellLinkCursor:
    def __init__(self, owner):
        self.owner = owner
        self.real = owner.connection.cursor()
        self.cached = None

    def execute(self, sql):
        self.cached = None
        match = re.fullmatch(r"select (\w+) from (\w+) where .*?like '([^']*)'.*", sql)
        if match:
            column, table, first = match.groups()
            word = first[:-2] if first.endswith(" %") else first
            if word and not any(c in word for c in ("%", "_", "'", "\x00")):
                prefix = f"select {column} from {table} where "
                partial_sql = prefix + (
                    f"{column} like '{word} %' or {column} like '% {word}' or "
                    f"{column} like '% {word} %' or {column} like '{word}'"
                )
                exact_sql = prefix + (
                    f"{column} like '{word}' or {column} like ' {word}' or "
                    f"{column} like '{word} ' or {column} like ' {word} '"
                )
                if sql == exact_sql or (sql == partial_sql and " " not in word):
                    try:
                        indexed = self.owner.index(table, column)
                    except (sqlite3.Error, UnicodeError):
                        # Dirty UTF-8 in unrelated rows must not suppress healthy matches.
                        self.owner.indexes[(table, column)] = None
                        indexed = None
                    if indexed is not None:
                        partial, exact = indexed
                        normalized = word.translate(ASCII_LOWER) if self.owner.ignore_case else word
                        found = (
                            normalized in partial
                            if sql == partial_sql
                            else any(
                                v in exact
                                for v in (
                                    normalized,
                                    " " + normalized,
                                    normalized + " ",
                                    " " + normalized + " ",
                                )
                            )
                        )
                        self.cached = [(1,)] if found else []
                        return self
        self.real.execute(sql)
        return self

    def fetchall(self):
        return self.cached if self.cached is not None else self.real.fetchall()
