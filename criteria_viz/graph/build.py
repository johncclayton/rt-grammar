"""Build a deep CriteriaGraph from extracted RTS formulas."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from lark import Token, Tree

from criteria_viz.graph.expr_text import expr_to_text
from criteria_viz.graph.model import CriteriaGraph, CriterionNode, TradePhase
from criteria_viz.graph.parse_rts import ENTRY_ROOT, EXIT_ROOT, extract_script, parse_rts_file
from pathlib import Path


class _GraphBuilder:
    def __init__(self, strategy: str, data_items: Mapping[str, Tree]):
        self.strategy = strategy
        self.data_items = dict(data_items)
        self.nodes: dict[str, CriterionNode] = {}
        self._synthetic_seq = 0

    def build_all(self, formulas: Mapping[str, Tree]) -> dict[tuple[str, TradePhase], str]:
        for name, expr in self.data_items.items():
            self._build_data_item(name, expr)

        roots: dict[tuple[str, TradePhase], str] = {}
        if ENTRY_ROOT in formulas:
            roots[(self.strategy, TradePhase.ENTRY)] = self._build_strategy_root(
                ENTRY_ROOT, formulas[ENTRY_ROOT]
            )
        if EXIT_ROOT in formulas:
            roots[(self.strategy, TradePhase.EXIT)] = self._build_strategy_root(
                EXIT_ROOT, formulas[EXIT_ROOT]
            )
        return roots

    def _build_data_item(self, name: str, expr: Tree) -> str:
        node_id = f"data:{name}"
        if node_id in self.nodes:
            return node_id
        child_id = self._build_expr(expr, context=f"data:{name}", label=name)
        child = self.nodes[child_id]
        if child_id == node_id:
            return node_id
        self.nodes[node_id] = CriterionNode(
            id=node_id,
            label=name,
            kind="data_ref",
            series_key=f"data:{name}",
            expr_source=expr_to_text(expr),
            deps=(child_id,),
        )
        return node_id

    def _build_strategy_root(self, root_name: str, expr: Tree) -> str:
        node_id = f"strategy:{self.strategy}:{root_name}"
        child_id = self._build_expr(expr, context=root_name, label=root_name)
        child = self.nodes[child_id]
        if child_id != node_id:
            self.nodes[node_id] = CriterionNode(
                id=node_id,
                label=root_name,
                kind="strategy_root",
                series_key=f"strategy:{self.strategy}:{root_name}",
                expr_source=expr_to_text(expr),
                deps=(child_id,),
            )
        else:
            self.nodes[node_id] = replace(
                child,
                id=node_id,
                label=root_name,
                kind="strategy_root",
                series_key=f"strategy:{self.strategy}:{root_name}",
            )
        return node_id

    def _next_synthetic_id(self) -> str:
        node_id = f"cv:{self._synthetic_seq}"
        self._synthetic_seq += 1
        return node_id

    def _build_expr(self, tree: Tree | Token, *, context: str, label: str) -> str:
        if isinstance(tree, Token):
            if tree.type == "STRING":
                return self._build_string_literal(tree.value)
            return self._build_ref(tree.value, context=context, label=label)

        name = tree.data
        children = tree.children

        if name == "logical_not":
            op_id = self._next_synthetic_id()
            dep = self._build_expr(children[0], context=context, label="not")
            text = expr_to_text(tree)
            self.nodes[op_id] = CriterionNode(
                id=op_id,
                label=text,
                kind="not",
                series_key=op_id,
                expr_source=text,
                deps=(dep,),
            )
            return op_id

        if name in ("and_expr", "or_expr"):
            op_kind = "and" if name == "and_expr" else "or"
            dep_ids: list[str] = []
            for child in children:
                if isinstance(child, Token) and child.type in ("AND", "OR"):
                    continue
                dep_ids.append(self._build_expr(child, context=context, label=label))
            if len(dep_ids) == 1:
                return dep_ids[0]
            op_id = self._next_synthetic_id()
            text = expr_to_text(tree)
            self.nodes[op_id] = CriterionNode(
                id=op_id,
                label=text,
                kind=op_kind,
                series_key=op_id,
                expr_source=text,
                deps=tuple(dep_ids),
            )
            return op_id

        if name == "comparison":
            if len(children) == 1:
                return self._build_expr(children[0], context=context, label=label)
            op_id = self._next_synthetic_id()
            left_id = self._build_expr(children[0], context=context, label="left")
            right_id = self._build_expr(children[2], context=context, label="right")
            op_tok = children[1].value if len(children) > 1 else ""
            text = expr_to_text(tree)
            self.nodes[op_id] = CriterionNode(
                id=op_id,
                label=text,
                kind="cmp",
                series_key=op_id,
                expr_source=text,
                deps=(left_id, right_id),
                meta={"op": op_tok},
            )
            return op_id

        if name == "funcall":
            op_id = self._next_synthetic_id()
            dep_ids = []
            fname = children[0].value
            for child in children[1:]:
                if isinstance(child, Tree) and child.data == "argument" and child.children:
                    arg = child.children[0]
                    if isinstance(arg, Token) and arg.type == "STRING":
                        continue
                    dep_ids.append(self._build_expr(arg, context=context, label="arg"))
            text = expr_to_text(tree)
            self.nodes[op_id] = CriterionNode(
                id=op_id,
                label=text,
                kind="call",
                series_key=op_id,
                expr_source=text,
                deps=tuple(dep_ids),
                meta={"fn": fname},
            )
            return op_id

        if name in ("additive", "multiplicative", "power", "offset", "negate", "unary_plus", "bitwise_not"):
            op_id = self._next_synthetic_id()
            dep_ids = tuple(
                self._build_expr(c, context=context, label=label)
                for c in children
                if not (isinstance(c, Token) and c.type in ("PLUS", "MINUS", "STAR", "SLASH", "MOD", "CARET", "BITOR", "BITXOR", "BITAND", "LSHIFT", "RSHIFT"))
            )
            text = expr_to_text(tree)
            self.nodes[op_id] = CriterionNode(
                id=op_id,
                label=text,
                kind=name,
                series_key=op_id,
                expr_source=text,
                deps=dep_ids,
            )
            return op_id

        if name in ("atom", "tagged_value", "argument") and children:
            if len(children) == 1:
                return self._build_expr(children[0], context=context, label=label)

        if len(children) == 1:
            return self._build_expr(children[0], context=context, label=label)

        op_id = self._next_synthetic_id()
        dep_ids = tuple(self._build_expr(c, context=context, label=label) for c in children if isinstance(c, (Tree, Token)))
        text = expr_to_text(tree)
        self.nodes[op_id] = CriterionNode(
            id=op_id,
            label=text,
            kind=name,
            series_key=op_id,
            expr_source=text,
            deps=dep_ids,
        )
        return op_id

    def _build_string_literal(self, value: str) -> str:
        node_id = f"str:{value}"
        if node_id not in self.nodes:
            self.nodes[node_id] = CriterionNode(
                id=node_id,
                label=value,
                kind="string_literal",
                series_key=node_id,
                expr_source=value,
                deps=(),
            )
        return node_id

    def _build_ref(self, name: str, *, context: str, label: str) -> str:
        if name.startswith('"') and name.endswith('"'):
            return self._build_string_literal(name)

        if name in self.data_items:
            return self._build_data_item(name, self.data_items[name])

        if name.replace(".", "").isdigit() or self._is_number(name):
            node_id = self._next_synthetic_id()
            self.nodes[node_id] = CriterionNode(
                id=node_id,
                label=name,
                kind="literal",
                series_key=node_id,
                expr_source=name,
                deps=(),
                meta={"value": name},
            )
            return node_id

        node_id = f"ref:{name}"
        if node_id not in self.nodes:
            kind = "param" if name[0].isupper() or name in ("RSIPeriod", "RSIThreshold", "NumPositions") else "builtin"
            series = f"{kind}:{name}"
            self.nodes[node_id] = CriterionNode(
                id=node_id,
                label=name,
                kind=kind,
                series_key=series,
                expr_source=name,
                deps=(),
            )
        return node_id

    @staticmethod
    def _is_number(value: str) -> bool:
        try:
            float(value)
            return True
        except ValueError:
            return False


def build_criteria_graph(
    rts_path: Path,
    *,
    strategy: str | None = None,
    grammar_path: Path | None = None,
    tree: Tree | None = None,
) -> CriteriaGraph:
    if tree is None:
        tree = parse_rts_file(rts_path, grammar_path=grammar_path)
    data_items, strategies = extract_script(tree)

    if strategy is None:
        if len(strategies) != 1:
            names = ", ".join(sorted(strategies))
            raise ValueError(f"Multiple strategies found ({names}); pass strategy=...")
        strategy = next(iter(strategies))

    if strategy not in strategies:
        raise ValueError(f"Strategy '{strategy}' not found in {rts_path}")

    builder = _GraphBuilder(strategy, data_items)
    roots = builder.build_all(strategies[strategy])

    return CriteriaGraph(
        nodes=dict(builder.nodes),
        roots=roots,
        strategies=tuple(strategies.keys()),
        data_items=tuple(data_items.keys()),
    )
