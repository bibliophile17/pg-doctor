"""Command line interface.

  python -m pgdoctor diagnose --file queries/before/q1_device_lookup.sql --dsn $PGDOCTOR_DSN
  python -m pgdoctor diagnose --file q.sql --plan-json saved_plan.json      # offline, no database
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import db, report
from .plan_parser import load_plan
from .rules import Context, diagnose

DEFAULT_DSN = "postgresql://postgres:pgdoctor@localhost:5432/iot"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pgdoctor")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diagnose", help="diagnose one query")
    d.add_argument("--file", required=True, help="SQL file containing one SELECT")
    d.add_argument("--dsn", default=os.environ.get("PGDOCTOR_DSN", DEFAULT_DSN))
    d.add_argument("--plan-json", help="use a saved EXPLAIN JSON instead of connecting")
    d.add_argument("--time-column", default="time")
    d.add_argument("--out-dir", default="reports")
    a = p.parse_args(argv)

    sql = Path(a.file).read_text()
    raw = json.loads(Path(a.plan_json).read_text()) if a.plan_json else db.explain(a.dsn, sql)
    plan = load_plan(raw)
    findings = diagnose(plan, Context(query=sql, time_column=a.time_column))
    md = report.render(Path(a.file).stem, sql, plan, findings)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{Path(a.file).stem}.md").write_text(md)
    if not a.plan_json:
        (out / f"{Path(a.file).stem}.plan.json").write_text(json.dumps(raw, indent=2))
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
