from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class TradePhase(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"


@dataclass(frozen=True, slots=True)
class CriterionNode:
    id: str
    label: str
    kind: str
    series_key: str
    expr_source: str
    deps: tuple[str, ...] = ()
    meta: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CriteriaGraph:
    """Deep criteria dependency graph for one or more strategies."""

    nodes: Mapping[str, CriterionNode]
    roots: Mapping[tuple[str, TradePhase], str]
    strategies: tuple[str, ...]
    data_items: tuple[str, ...]

    def root_for(self, strategy: str, phase: TradePhase) -> str | None:
        return self.roots.get((strategy, phase))

    def node(self, node_id: str) -> CriterionNode:
        return self.nodes[node_id]

    def reachable(self, root_id: str) -> frozenset[str]:
        seen: set[str] = set()
        stack = [root_id]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            stack.extend(self.nodes[nid].deps)
        return frozenset(seen)
