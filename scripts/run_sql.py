"""Run a .sql file against the database in PGDOCTOR_DSN - no psql or Docker needed.

  python scripts/run_sql.py sql/01_schema.sql
  python scripts/run_sql.py sql/02_seed_data.sql --days 7 --devices 100

Statements run one at a time in autocommit mode, because TimescaleDB continuous
aggregates and refresh calls cannot run inside a transaction block.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DSN = os.environ.get("PGDOCTOR_DSN", "postgresql://postgres:pgdoctor@localhost:5432/iot")


def split_statements(sql: str) -> list[str]:
    """Split on ';' while respecting '...' strings, $$...$$ bodies and -- comments."""
    out, buf, i, n = [], [], 0, len(sql)
    in_str = in_dollar = False
    while i < n:
        c = sql[i]
        if in_dollar:
            if sql.startswith("$$", i):
                in_dollar = False
                buf.append("$$"); i += 2; continue
        elif in_str:
            if c == "'":
                in_str = False
        else:
            if sql.startswith("--", i):
                j = sql.find("\n", i)
                j = n if j == -1 else j
                i = j; continue
            if sql.startswith("$$", i):
                in_dollar = True
                buf.append("$$"); i += 2; continue
            if c == "'":
                in_str = True
            elif c == ";":
                stmt = "".join(buf).strip()
                if stmt:
                    out.append(stmt)
                buf = []; i += 1; continue
        buf.append(c); i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--days", default="7")
    ap.add_argument("--devices", default="100")
    a = ap.parse_args()
    sql = Path(a.file).read_text().replace("{{DAYS}}", a.days).replace("{{DEVICES}}", a.devices)
    stmts = split_statements(sql)

    import psycopg2
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    cur = conn.cursor()
    for k, s in enumerate(stmts, 1):
        first = s.splitlines()[0][:70]
        print(f"[{k}/{len(stmts)}] {first}")
        try:
            cur.execute(s)
            if cur.description:
                for row in cur.fetchmany(20):
                    print("   ", row)
        except Exception as e:  # keep going on harmless 'already exists' errors
            msg = str(e).strip().splitlines()[0]
            print(f"    ! {msg}")
            if "already exists" not in msg:
                return 1
    conn.close()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
