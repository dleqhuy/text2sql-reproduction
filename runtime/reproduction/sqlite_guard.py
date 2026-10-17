# Shared runtime: edit runtime/ in text2sql-reproduction, then run scripts.sync_runtime.
"""Read-only authorizer plus killable workers for untrusted SQLite queries."""

import multiprocessing as mp
import sqlite3
import time
from pathlib import Path

_CONNECT = sqlite3.connect


def readonly_connect(path, timeout_s=5):
    conn = _CONNECT(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    allowed = {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }

    def authorize(action, first, second, database, trigger):
        if action == sqlite3.SQLITE_PRAGMA and first.lower() in {"table_info", "table_xinfo"}:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (second or "").lower() == "load_extension":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY

    conn.set_authorizer(authorize)
    deadline = time.monotonic() + timeout_s
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16 * 1024 * 1024)
    return conn


def _query_worker(pipe, path, sql, timeout_s, limit):
    try:
        with readonly_connect(path, timeout_s) as conn:
            cursor = conn.execute(sql)
            # Consume the whole result for execution validity; only retain a small preview.
            preview, count = [], 0
            while True:
                batch = cursor.fetchmany(500)
                if not batch:
                    break
                count += len(batch)
                preview.extend(batch[: max(0, limit - len(preview))])
            pipe.send({"status": "ok", "data": preview, "row_count": count})
    except sqlite3.Error as exc:
        status = "timeout" if str(exc) == "interrupted" else "sql_error"
        pipe.send({"status": status, "error": str(exc)})
    except Exception:
        pipe.send({"status": "harness_error", "error": "Query worker failed"})
    finally:
        pipe.close()


def isolated_call(target, args, timeout_s):
    context = mp.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(send, *args))
    process.start()
    send.close()
    try:
        if receive.poll(timeout_s):
            try:
                result = receive.recv()
            except EOFError:
                result = {"status": "harness_error", "error": "Worker exited without a result"}
        else:
            result = {"status": "timeout", "error": "Worker deadline exceeded"}
    finally:
        if process.is_alive():
            process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
        receive.close()
    return result


def execute(path, sql, timeout_s=5, preview_limit=5):
    if not Path(path).is_file():
        raise FileNotFoundError("Database does not exist")
    return isolated_call(_query_worker, (str(path), sql, timeout_s, preview_limit), timeout_s + 1)
