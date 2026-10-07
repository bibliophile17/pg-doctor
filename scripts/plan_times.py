"""Summarise SERVER-side execution time and scan types from the saved EXPLAIN plans.

  python scripts/plan_times.py
Reads results/plans/before|after/*.json (written by benchmark.py) and writes results/server_side.md.
Client-side timings include network round-trips to the cloud database; these do not.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pgdoctor.plan_parser import load_plan  # noqa: E402

R = Path("results/plans")


def summarise(path: Path):
    plan = load_plan(json.loads(path.read_text()))
    kinds = sorted({n.node_type for n in plan.scans})
    idx = sorted({n.index_name for n in plan.nodes if n.index_name})
    return plan.execution_ms, len(plan.chunks_scanned), plan.buffers_read, kinds, idx


rows = ["| Query | Before (ms) | After (ms) | Chunks before/after | Scan types after | Indexes used after |",
        "|---|---:|---:|---|---|---|"]
for b in sorted((R / "before").glob("*.json")):
    a = R / "after" / b.name
    if not a.exists():
        continue
    be, bc, _, _, _ = summarise(b)
    ae, ac, _, ak, ai = summarise(a)
    rows.append(f"| {b.stem} | {be:.1f} | {ae:.1f} | {bc} / {ac} | {', '.join(ak)} | {', '.join(ai) or '-'} |")
out = "\n".join(rows)
Path("results/server_side.md").write_text(out + "\n")
print(out)
