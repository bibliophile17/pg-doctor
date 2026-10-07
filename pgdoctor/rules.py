"""Diagnostic rules. Each rule inspects a Plan (+ the SQL text) and returns Findings.

Explanations are written for the customer, not for a DBA.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .plan_parser import Plan

BLOCK_KB = 8  # PostgreSQL block size


@dataclass
class Context:
    query: str
    time_column: str = "time"
    chunk_threshold: int = 10

    @property
    def table(self) -> str:
        m = re.search(r"\bfrom\s+([a-z_][\w.]*)", self.query, re.I)
        return m.group(1) if m else "<your_table>"


@dataclass
class Finding:
    rule_id: str
    severity: str  # high | medium | low
    title: str
    explanation: str
    recommendation: str
    evidence: dict[str, str] = field(default_factory=dict)
    sql_fix: Optional[str] = None


def _filter_columns(filters: list[str], time_col: str) -> list[str]:
    cols: list[str] = []
    for f in filters:
        for m in re.finditer(r"\(?\s*([a-z_][a-z0-9_]*)\s*(?:=|<>|<=|>=|<|>)", f, re.I):
            c = m.group(1)
            if c.lower() not in ("and", "or", "not") and c != time_col and c not in cols:
                cols.append(c)
    return cols


def rule_inefficient_filter(plan: Plan, ctx: Context) -> list[Finding]:
    scans = [n for n in plan.scans if n.filter and n.rows_removed > 0]
    examined = sum(n.rows_examined for n in scans)
    removed = sum(n.rows_removed * n.loops for n in scans)
    if examined < 100_000 or removed / examined < 0.9:
        return []
    kept = examined - removed
    cols = _filter_columns([n.filter for n in scans if n.filter], ctx.time_column)
    col_list = ", ".join(cols) if cols else "<filter_columns>"
    idx = f"idx_{ctx.table}_{'_'.join(cols) if cols else 'cols'}_{ctx.time_column}"
    return [Finding(
        rule_id="INEFFICIENT_FILTER",
        severity="high",
        title="The database reads far more rows than it needs",
        explanation=(
            f"To answer your query, the database looked at {examined:,.0f} rows and threw away "
            f"{removed:,.0f} of them ({removed / examined:.1%}), keeping only {kept:,.0f}. "
            "It is like finding one person's name by reading every page of a phone book, "
            "instead of using the index at the back. An index on the column(s) you filter by "
            "lets the database jump straight to the matching rows."
        ),
        recommendation=(
            f"Create an index on ({col_list}, {ctx.time_column} DESC). On a large, busy table, "
            "use the per-chunk option so writes are not blocked for long."
        ),
        evidence={"rows examined": f"{examined:,.0f}", "rows discarded": f"{removed:,.0f}",
                  "filter columns": col_list},
        sql_fix=(f"CREATE INDEX {idx[:60]} ON {ctx.table} ({col_list}, {ctx.time_column} DESC)\n"
                 "  WITH (timescaledb.transaction_per_chunk);"),
    )]


def rule_no_chunk_exclusion(plan: Plan, ctx: Context) -> list[Finding]:
    n_chunks = len(plan.chunks_scanned)
    if n_chunks < ctx.chunk_threshold:
        return []
    q = ctx.query.lower()
    tc = re.escape(ctx.time_column.lower())
    if re.search(rf"\b{tc}\b\s*(>=|<=|>|<|between)", q):
        return []  # a real time range exists; the range is just wide
    wrapped = re.search(rf"\w+\([^)]*\b{tc}\b[^)]*\)\s*(=|>=|<=|>|<)", q)
    if wrapped:
        why = (
            f"Your query applies a function to the '{ctx.time_column}' column before comparing it. "
            "The database cannot tell in advance which time slices (chunks) can match, so it opens all of them."
        )
        rec = (f"Compare the bare '{ctx.time_column}' column against a range instead, e.g. "
               f"{ctx.time_column} >= start AND {ctx.time_column} < end.")
    else:
        why = (f"Your query has no time range on '{ctx.time_column}', so the database has to open every "
               "time slice (chunk) of the table, even old ones you probably do not care about.")
        rec = (f"Add a time range such as {ctx.time_column} > now() - interval '24 hours', "
               "or create an index so each chunk is cheap to check.")
    return [Finding(
        rule_id="NO_CHUNK_EXCLUSION",
        severity="high",
        title="The query touches every time slice of the table",
        explanation=(f"TimescaleDB splits data into time-based chunks and can skip chunks outside your time range. "
                     f"{why} This query read {n_chunks} chunks."),
        recommendation=rec,
        evidence={"chunks scanned": str(n_chunks)},
    )]


def rule_high_buffer_reads(plan: Plan, ctx: Context) -> list[Finding]:
    total = plan.buffers_hit + plan.buffers_read
    if plan.buffers_read < 10_000 or total == 0 or plan.buffers_read / total < 0.5:
        return []
    mb = plan.buffers_read * BLOCK_KB / 1024
    return [Finding(
        rule_id="HIGH_BUFFER_READS",
        severity="medium",
        title="Most of the data had to be fetched from disk",
        explanation=(f"The query pulled about {mb:,.0f} MB from disk because it was not already in memory "
                     f"({plan.buffers_read / total:.0%} of the blocks it touched). Disk reads are much slower "
                     "than memory. This usually means the query reads more data than it needs, or the data "
                     "has not been touched recently."),
        recommendation="Reduce the data scanned first (index / time range). Only then consider more memory.",
        evidence={"blocks read from disk": f"{plan.buffers_read:,}", "blocks from cache": f"{plan.buffers_hit:,}",
                  "approx MB read": f"{mb:,.0f}"},
    )]


def rule_naive_aggregate(plan: Plan, ctx: Context) -> list[Finding]:
    q = ctx.query.lower()
    if "time_bucket" not in q or "group by" not in q or plan.reads_materialized_view:
        return []
    scanned = sum(n.rows_examined for n in plan.scans)
    if scanned < 500_000:
        return []
    return [Finding(
        rule_id="NAIVE_AGGREGATE",
        severity="medium",
        title="The same summary is recalculated from raw data every time",
        explanation=(f"This query summarised {scanned:,.0f} raw rows into time buckets. If you run it often, "
                     "the database repeats that work each time. A continuous aggregate keeps the summary "
                     "pre-calculated and up to date in the background, so reads become tiny."),
        recommendation="Create a continuous aggregate over the same bucket and query it instead.",
        evidence={"raw rows scanned": f"{scanned:,.0f}"},
        sql_fix=("CREATE MATERIALIZED VIEW <name>_hourly WITH (timescaledb.continuous) AS\n"
                 f"SELECT time_bucket('1 hour', {ctx.time_column}) AS bucket, <group_cols>, avg(<value>) AS avg_value\n"
                 f"FROM {ctx.table} GROUP BY bucket, <group_cols> WITH NO DATA;"),
    )]


def rule_sort_spill(plan: Plan, ctx: Context) -> list[Finding]:
    spills = [n for n in plan.nodes if n.sort_method and "external" in n.sort_method.lower()]
    if not spills:
        return []
    return [Finding(
        rule_id="SORT_SPILL",
        severity="low",
        title="A sort was too big for memory and used temporary disk files",
        explanation="Sorting the results needed more memory than allowed, so PostgreSQL wrote temporary files to disk, which is slower.",
        recommendation="Return fewer rows, add an index that already provides the order, or raise work_mem for this session.",
        evidence={"sort method": spills[0].sort_method or ""},
    )]


def rule_bad_estimates(plan: Plan, ctx: Context) -> list[Finding]:
    bad = []
    for n in plan.nodes:
        if n.plan_rows <= 0 or n.loops < 1:
            continue
        ratio = max(n.actual_rows, 1) / n.plan_rows
        if max(n.actual_rows, n.plan_rows) >= 1000 and (ratio >= 100 or ratio <= 0.01):
            bad.append(n)
    if not bad:
        return []
    n = bad[0]
    return [Finding(
        rule_id="BAD_ROW_ESTIMATE",
        severity="low",
        title="The planner's guess about row counts was far off",
        explanation=(f"At a '{n.node_type}' step the database expected {n.plan_rows:,.0f} rows but found "
                     f"{n.actual_rows:,.0f}. Wrong guesses can lead it to choose a slower plan."),
        recommendation="Refresh statistics with ANALYZE on the table, then re-check the plan.",
        evidence={"expected rows": f"{n.plan_rows:,.0f}", "actual rows": f"{n.actual_rows:,.0f}"},
        sql_fix=f"ANALYZE {ctx.table};",
    )]


RULES: list[Callable[[Plan, Context], list[Finding]]] = [
    rule_no_chunk_exclusion, rule_inefficient_filter, rule_high_buffer_reads,
    rule_naive_aggregate, rule_sort_spill, rule_bad_estimates,
]
_ORDER = {"high": 0, "medium": 1, "low": 2}


def diagnose(plan: Plan, ctx: Context) -> list[Finding]:
    findings = [f for rule in RULES for f in rule(plan, ctx)]
    return sorted(findings, key=lambda f: _ORDER[f.severity])
