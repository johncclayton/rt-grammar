"""Lark parse tree → CriteriaGraph (internal).

Not imported from criteria_viz.__init__. Public callers use build_criteria_graph().
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from lark import Lark, Transformer, v_args

from criteria_viz.graph import CriteriaGraph, CriterionNode, NodeId, NodeKind, RootKey


class GraphBuilder:
    """Build a CriteriaGraph from validated RTS source."""

    def __init__(self, grammar_path: Path) -> None:
        grammar = grammar_path.read_text(encoding="utf-8")
        self._parser = Lark(
            grammar,
            start="start",
            parser="lalr",
            lexer="contextual",
            propagate_positions=True,
            maybe_placeholders=False,
        )
        self._nodes: dict[NodeId, CriterionNode] = {}
        self._roots: dict[RootKey, NodeId] = {}
        self._data_items: set[str] = set()
        self._id_seq = 0

    def from_file(self, rts_path: Path) -> CriteriaGraph:
        source = rts_path.read_text(encoding="utf-8")
        tree = self._parser.parse(source)
        # Transformer walks Data:, Strategy:, Library: — sketch only
        _StrategyGraphTransformer(self)(tree)
        return CriteriaGraph(
            nodes=dict(self._nodes),
            roots=dict(self._roots),
            data_items=frozenset(self._data_items),
            source_path=rts_path,
        )

    def _new_id(self, hint: str) -> NodeId:
        self._id_seq += 1
        return f"n{self._id_seq}:{hint}"

    def add_data_item(self, name: str, expr_tree, expr_source: str) -> NodeId:
        self._data_items.add(name)
        body_id = self._expr_to_node(expr_tree, expr_source)
        nid = self._new_id(name)
        self._nodes[nid] = CriterionNode(
            id=nid,
            label=name,
            kind=NodeKind.DATA_REF,
            expr_source=expr_source,
            deps=(body_id,) if body_id else (),
            meta={"data_item": name},
        )
        return nid

    def add_strategy_root(
        self,
        strategy: str,
        keyword: str,
        phase_value: str,
        expr_tree,
        expr_source: str,
    ) -> None:
        root_body = self._expr_to_node(expr_tree, expr_source)
        nid = self._new_id(f"{strategy}.{keyword}")
        self._nodes[nid] = CriterionNode(
            id=nid,
            label=keyword,
            kind=NodeKind.BINARY if keyword in ("EntrySetup", "ExitRule") else NodeKind.CALL,
            expr_source=expr_source,
            deps=(root_body,) if root_body else (),
            meta={"strategy": strategy, "keyword": keyword},
        )
        self._roots[(strategy, phase_value)] = nid

    def _expr_to_node(self, expr_tree, expr_source: str) -> Optional[NodeId]:
        """Lower formula parse subtree to graph nodes. Implementation TBD."""
        raise NotImplementedError("expr lowering is part of slice 1")


@v_args(inline=True)
class _StrategyGraphTransformer(Transformer):
    """Visitor hooks for strategy_section, data_section, library_section."""

    def __init__(self, builder: GraphBuilder) -> None:
        super().__init__()
        self._b = builder

    # data_item_decl, strategy roots, library_decl handlers wired in slice 1
    ...
