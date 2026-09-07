"""Extract strategy criterion expressions from a Lark parse tree."""

from __future__ import annotations

import re
from typing import Mapping

from lark import Tree

from criteria_viz.models import StrategyCriteria

# Phase 0: line-oriented extraction from raw RTS text embedded in tree leaves.
# Phase 1: structured walk of strategy_section nodes in realtest.lark.

_CRITERION_KWS = (
    "EntrySetup",
    "EntrySkip",
    "SetupSkip",
    "ExitRule",
)
_BOOL_KW = re.compile(r"^\s*(Compounded)\s*:\s*(True|False)\s*$", re.I)
_CRIT_KW = re.compile(
    r"^\s*(" + "|".join(_CRITERION_KWS) + r")\s*:\s*(.+?)\s*$",
    re.I,
)
_STRATEGY = re.compile(r"^\s*Strategy\s*:\s*(\S+)", re.I)


def extract_strategy_criteria(tree: Tree) -> Mapping[str, StrategyCriteria]:
    """
    Return criterion expression text keyed by strategy name.

    Sketch: scan pretty-printed tree for ``Strategy:`` blocks. Replace with
    grammar-aware visitor when rt-grammar grows an AST export.
    """
    text = tree.pretty()
    strategies: dict[str, StrategyCriteria] = {}
    current: str | None = None
    compounded = False
    fields: dict[str, str | bool] = {}

    def flush() -> None:
        nonlocal current, compounded, fields
        if current is None:
            return
        strategies[current] = StrategyCriteria(
            name=current,
            compounded=bool(compounded),
            entry_setup=fields.get("entry_setup"),  # type: ignore[arg-type]
            entry_skip=fields.get("entry_skip"),  # type: ignore[arg-type]
            setup_skip=fields.get("setup_skip"),  # type: ignore[arg-type]
            exit_rule=fields.get("exit_rule"),  # type: ignore[arg-type]
        )
        current = None
        compounded = False
        fields = {}

    for line in text.splitlines():
        m_strat = _STRATEGY.match(line)
        if m_strat:
            flush()
            current = m_strat.group(1)
            continue
        if current is None:
            continue
        m_bool = _BOOL_KW.match(line)
        if m_bool and m_bool.group(1).lower() == "compounded":
            compounded = m_bool.group(2).lower() == "true"
            continue
        m_crit = _CRIT_KW.match(line)
        if m_crit:
            key = m_crit.group(1).lower()
            fields[key] = m_crit.group(2).strip()

    flush()
    return strategies
