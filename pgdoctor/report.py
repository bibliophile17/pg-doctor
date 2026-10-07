"""Render findings as a customer-facing Markdown report."""
from __future__ import annotations

from .plan_parser import Plan
from .rules import Finding


def render(title: str, query: str, plan: Plan, findings: list[Finding]) -> str:
    out = [f"# Query review: {title}", "",
           "## Summary", "",
           f"Your query took **{plan.execution_ms:,.1f} ms** to run "
           f"(planning: {plan.planning_ms:,.1f} ms). "]
    if findings:
        n = len(findings)
        out.append(f"We found **{n} thing{'s' if n != 1 else ''}** that can be improved.")
    else:
        out.append("We did not find any common performance problems in this query's plan.")
    out += ["", "```sql", query.strip(), "```", ""]
    for i, f in enumerate(findings, 1):
        out += [f"## {i}. {f.title}  _(priority: {f.severity})_", "",
                "**What is happening**", "", f.explanation, "",
                "**What we recommend**", "", f.recommendation, ""]
        if f.sql_fix:
            out += ["```sql", f.sql_fix, "```", ""]
        if f.evidence:
            out += ["<details><summary>Supporting numbers</summary>", ""]
            out += [f"- {k}: {v}" for k, v in f.evidence.items()]
            out += ["", "</details>", ""]
    if findings:
        out += ["## What to expect", "",
                "After applying these changes, re-run the query and send us the new timing. "
                "If it is still slower than you need, send the new `EXPLAIN (ANALYZE, BUFFERS)` output "
                "and we will take another look.", ""]
    return "\n".join(out)
