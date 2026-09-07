"""CriteriaGraph — load-bearing dependency structure for RTS formulas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Mapping, Optional


NodeId = str
RootKey = tuple[str, str]  # (strategy_name, TradePhase.value)


class NodeKind(Enum):
    """Graph node classification for layout and evaluation."""

    DATA_REF = auto()  # named Data: item (may have formula children)
    REF = auto()  # builtin or unresolved identifier (C, BarsHeld, …)
    LITERAL = auto()
    UNARY = auto()  # not, -, !
    BINARY = auto()  # and, or, +, <, …
    CALL = auto()  # MA(C, 50), IF(…), …


@dataclass(frozen=True, slots=True)
class CriterionNode:
    id: NodeId
    label: str
    kind: NodeKind
    expr_source: str
    deps: tuple[NodeId, ...] = ()
    meta: Mapping[str, str] = field(default_factory=dict)


@dataclass
class CriteriaGraph:
    """Directed acyclic graph of criterion expressions for one RTS script."""

    nodes: dict[NodeId, CriterionNode]
    roots: dict[RootKey, NodeId]
    data_items: frozenset[str]
    source_path: Optional[Path] = None

    def root_for(self, strategy: str, phase_value: str) -> Optional[NodeId]:
        return self.roots.get((strategy, phase_value))

    def node_label(self, node_id: NodeId) -> str:
        return self.nodes[node_id].label

    def reachable_from(self, root_id: NodeId) -> tuple[NodeId, ...]:
        """Topological order of nodes reachable from root (for eval and UI)."""
        seen: set[NodeId] = set()
        order: list[NodeId] = []

        def visit(nid: NodeId) -> None:
            if nid in seen:
                return
            seen.add(nid)
            for dep in self.nodes[nid].deps:
                visit(dep)
            order.append(nid)

        visit(root_id)
        return tuple(order)

    def subgraph(self, root_id: NodeId) -> CriteriaGraph:
        keep = set(self.reachable_from(root_id))
        return CriteriaGraph(
            nodes={nid: self.nodes[nid] for nid in keep},
            roots={},  # caller sets context
            data_items=frozenset(
                n.meta.get("data_item", n.label)
                for n in self.nodes.values()
                if n.kind is NodeKind.DATA_REF and n.id in keep
            ),
            source_path=self.source_path,
        )


def build_criteria_graph(
    rts_path: Path | str,
    *,
    strategy: Optional[str] = None,
    grammar_path: Path | str = "realtest.lark",
) -> CriteriaGraph:
    """Parse an RTS file and return the criteria dependency graph.

    If ``strategy`` is omitted and the script defines exactly one Strategy
    section, that name is used. Multiple strategies require an explicit name.
    """
    from criteria_viz.rts_bridge import GraphBuilder  # lazy: avoids import cycle

    path = Path(rts_path)
    builder = GraphBuilder(grammar_path=Path(grammar_path))
    graph = builder.from_file(path)
    if strategy is not None:
        # Validate requested strategy exists among roots
        if not any(key[0] == strategy for key in graph.roots):
            known = sorted({k[0] for k in graph.roots})
            raise ValueError(f"Strategy '{strategy}' not found; known: {known}")
    return graph
