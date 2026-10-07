"""Parse EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) output into a flat list of nodes."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

CHUNK_RE = re.compile(r"^_hyper_\d+_\d+_chunk$")
COMPRESSED_RE = re.compile(r"^compress_hyper_\d+_\d+_chunk$")


@dataclass
class Node:
    node_type: str
    relation: Optional[str]
    index_name: Optional[str]
    filter: Optional[str]
    rows_removed: int
    actual_rows: float
    loops: int
    plan_rows: float
    total_time: float
    sort_method: Optional[str]
    depth: int

    @property
    def is_scan(self) -> bool:
        return self.relation is not None and "Scan" in self.node_type

    @property
    def rows_examined(self) -> float:
        """Rows the node looked at (kept + discarded), across all loops."""
        return (self.actual_rows + self.rows_removed) * self.loops


@dataclass
class Plan:
    nodes: list[Node] = field(default_factory=list)
    planning_ms: float = 0.0
    execution_ms: float = 0.0
    buffers_hit: int = 0
    buffers_read: int = 0

    @property
    def scans(self) -> list[Node]:
        return [n for n in self.nodes if n.is_scan]

    @property
    def chunks_scanned(self) -> set[str]:
        return {n.relation for n in self.scans if n.relation and CHUNK_RE.match(n.relation)}

    @property
    def compressed_chunks_scanned(self) -> set[str]:
        return {n.relation for n in self.scans if n.relation and COMPRESSED_RE.match(n.relation)}

    @property
    def reads_materialized_view(self) -> bool:
        return any(n.relation and n.relation.startswith("_materialized_hypertable") for n in self.scans)


def _walk(raw: dict[str, Any], depth: int, out: list[Node]) -> None:
    out.append(Node(
        node_type=raw.get("Node Type", "?"),
        relation=raw.get("Relation Name"),
        index_name=raw.get("Index Name"),
        filter=raw.get("Filter"),
        rows_removed=int(raw.get("Rows Removed by Filter", 0) or 0),
        actual_rows=float(raw.get("Actual Rows", 0) or 0),
        loops=int(raw.get("Actual Loops", 1) or 1),
        plan_rows=float(raw.get("Plan Rows", 0) or 0),
        total_time=float(raw.get("Actual Total Time", 0) or 0),
        sort_method=raw.get("Sort Method"),
        depth=depth,
    ))
    for child in raw.get("Plans", []) or []:
        _walk(child, depth + 1, out)


def load_plan(source: Any) -> Plan:
    """Accept a JSON string, or the already-decoded list/dict that psycopg2 returns."""
    data = json.loads(source) if isinstance(source, (str, bytes)) else source
    if isinstance(data, list):
        data = data[0]
    root = data["Plan"]
    nodes: list[Node] = []
    _walk(root, 0, nodes)
    return Plan(
        nodes=nodes,
        planning_ms=float(data.get("Planning Time", 0) or 0),
        execution_ms=float(data.get("Execution Time", 0) or 0),
        buffers_hit=int(root.get("Shared Hit Blocks", 0) or 0),
        buffers_read=int(root.get("Shared Read Blocks", 0) or 0),
    )
