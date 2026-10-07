"""Database access. psycopg2 is imported lazily so the parser/rules work without it."""
from __future__ import annotations

import re


def _clean(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("PG Doctor only analyses SELECT/WITH queries (EXPLAIN ANALYZE executes them).")
    return sql


def explain(dsn: str, sql: str, timeout_ms: int = 60_000):
    import psycopg2  # noqa: WPS433

    sql = _clean(sql)
    conn = psycopg2.connect(dsn)
    try:
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL statement_timeout = {int(timeout_ms)}")
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
            return cur.fetchone()[0]
    finally:
        conn.rollback()
        conn.close()
