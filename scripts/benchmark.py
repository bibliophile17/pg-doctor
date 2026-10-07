"""Time every query in a directory and record plans + table size.

  python scripts/benchmark.py --dir queries/before --label before
  (apply sql/03_fixes.sql)
  python scripts/benchmark.py --dir queries/after  --label after
Writes results/<label>.json, and results/benchmark.md once both labels exist.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import psycopg2

DSN = os.environ.get("PGDOCTOR_DSN", "postgresql://postgres:pgdoctor@localhost:5432/iot")
RESULTS = Path("results")


def run(dir_: Path, label: str, repeats: int) -> None:
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT pg_size_pretty(hypertable_size('sensor_readings'))")
    size = cur.fetchone()[0]
    out = {"label": label, "table_size": size, "queries": {}}
    (RESULTS / "plans" / label).mkdir(parents=True, exist_ok=True)
    for f in sorted(dir_.glob("*.sql")):
        sql = f.read_text().strip().rstrip(";")
        cur.execute(sql)
        cur.fetchall()  # warm-up
        times = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            cur.execute(sql)
            cur.fetchall()
            times.append((time.perf_counter() - t0) * 1000)
        server = []
        for _ in range(repeats):
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}")
            plan = cur.fetchone()[0]
            server.append(plan[0]["Execution Time"])
        (RESULTS / "plans" / label / f"{f.stem}.json").write_text(json.dumps(plan, indent=2))
        out["queries"][f.stem] = round(statistics.median(times), 1)
        out.setdefault("server_ms", {})[f.stem] = round(statistics.median(server), 1)
        print(f"{label:6} {f.stem:28} client {out['queries'][f.stem]:>9} ms | server {out['server_ms'][f.stem]:>9} ms")
    (RESULTS / f"{label}.json").write_text(json.dumps(out, indent=2))
    conn.close()


def compare() -> None:
    b, a = RESULTS / "before.json", RESULTS / "after.json"
    if not (b.exists() and a.exists()):
        return
    bj, aj = json.loads(b.read_text()), json.loads(a.read_text())
    rows = ["| Query | Client before/after (ms) | Server before/after (ms) | Server speed-up |", "|---|---|---|---:|"]
    for q, bt in bj["queries"].items():
        at = aj["queries"].get(q)
        bs, as_ = bj.get("server_ms", {}).get(q), aj.get("server_ms", {}).get(q)
        if at and bs and as_:
            rows.append(f"| {q} | {bt} / {at} | {bs} / {as_} | {bs / max(as_, 0.01):.1f}x |")
    rows += ["", f"Table size before: {bj['table_size']} / after (compression policy): {aj['table_size']}"]
    (RESULTS / "benchmark.md").write_text("\n".join(rows) + "\n")
    print("\n" + "\n".join(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    run(Path(args.dir), args.label, args.repeats)
    compare()