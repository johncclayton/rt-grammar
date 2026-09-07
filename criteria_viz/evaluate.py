"""Evaluate CriteriaGraph nodes against a BarSeries at one bar (internal)."""

from __future__ import annotations

from typing import Mapping

from criteria_viz.graph import CriteriaGraph, CriterionNode, NodeId, NodeKind
from criteria_viz.models import Scalar
from criteria_viz.series import BarSeries


def evaluate_graph(
    graph: CriteriaGraph,
    series: BarSeries,
    symbol: str,
    bar_index: int,
    root_id: NodeId,
) -> Mapping[NodeId, Scalar]:
    """Return node values for reachable subgraph at a single bar index."""
    values: dict[NodeId, Scalar] = {}
    for nid in graph.reachable_from(root_id):
        node = graph.nodes[nid]
        values[nid] = _eval_node(node, graph, series, symbol, bar_index, values)
    return values


def _eval_node(
    node: CriterionNode,
    graph: CriteriaGraph,
    series: BarSeries,
    symbol: str,
    bar_index: int,
    memo: Mapping[NodeId, Scalar],
) -> Scalar:
    if node.kind is NodeKind.LITERAL:
        return _literal_value(node)
    if node.kind is NodeKind.DATA_REF:
        if node.deps:
            return memo[node.deps[0]]
        return series.value(symbol, node.label, bar_index)
    if node.kind is NodeKind.REF:
        return series.value(symbol, node.label, bar_index)
    if node.kind is NodeKind.UNARY:
        return _eval_unary(node, memo)
    if node.kind is NodeKind.BINARY:
        return _eval_binary(node, memo)
    if node.kind is NodeKind.CALL:
        return _eval_call(node, memo)
    raise ValueError(f"unsupported node kind {node.kind}")


def _literal_value(node: CriterionNode) -> Scalar:
    raw = node.meta.get("value", "0")
    if raw in ("True", "true"):
        return True
    if raw in ("False", "false"):
        return False
    return float(raw)


def _eval_unary(node: CriterionNode, memo: Mapping[NodeId, Scalar]) -> Scalar:
    op = node.meta.get("op", "not")
    arg = memo[node.deps[0]]
    if op in ("not", "!"):
        return not _truthy(arg)
    if op == "-":
        return -(arg or 0)
    raise NotImplementedError(op)


def _eval_binary(node: CriterionNode, memo: Mapping[NodeId, Scalar]) -> Scalar:
    op = node.meta.get("op", "and")
    left, right = memo[node.deps[0]], memo[node.deps[1]]
    if op == "and":
        return _truthy(left) and _truthy(right)
    if op == "or" or op == "||":
        return _truthy(left) or _truthy(right)
    if op == "<":
        return (left or 0) < (right or 0)
    if op == ">":
        return (left or 0) > (right or 0)
    if op == "=" or op == "==":
        return left == right
    raise NotImplementedError(op)


def _eval_call(node: CriterionNode, memo: Mapping[NodeId, Scalar]) -> Scalar:
    # v1: only functions present in export columns resolve; else NotImplemented
    fn = node.meta.get("fn", "")
    raise NotImplementedError(f"call {fn}")


def _truthy(value: Scalar) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value != 0
