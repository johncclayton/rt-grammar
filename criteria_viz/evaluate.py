"""Minimal formula evaluation — invoked only at bundle build time."""

from __future__ import annotations

from typing import Mapping

from criteria_viz.models import (
    BarCriteria,
    BarRow,
    BarSeries,
    CriterionSnapshot,
    StrategyCriteria,
    TradeRecord,
    TradeTimeline,
)

# Phase 0 stub: constant false unless expression text is literally "True".
# Phase 1 replaces this with a real boolean evaluator over BarRow fields.


def _eval_bool(expr: str | None, row: BarRow, params: Mapping[str, float]) -> CriterionSnapshot:
    name = "unknown"
    if expr is None:
        return CriterionSnapshot(name=name, expr="", value=False)
    lowered = expr.strip().lower()
    if lowered == "true":
        value = True
    elif lowered == "false":
        value = False
    else:
        # Placeholder until Phase 1 evaluator lands.
        value = False
    return CriterionSnapshot(name=name, expr=expr, value=value)


def _phase_for_bar(bar_date: str, entry_date: str, is_last: bool) -> str:
    if bar_date < entry_date:
        return "setup"
    if bar_date == entry_date:
        return "entry"
    if is_last:
        return "exit"
    return "hold"


def compute_trade_timeline(
    *,
    trade: TradeRecord,
    criteria: StrategyCriteria,
    bars: BarSeries,
    params: Mapping[str, float],
    window_before: int = 5,
    window_after: int = 5,
) -> TradeTimeline:
    """
    Eager timeline construction — called exclusively from ``build_session()``.
    """
    idx = next(i for i, r in enumerate(bars.rows) if r.date == trade.date)
    start = max(0, idx - window_before)
    end = min(len(bars.rows), idx + window_after + 1)
    window = bars.rows[start:end]

    bar_criteria: list[BarCriteria] = []
    for i, row in enumerate(window):
        is_last = i == len(window) - 1
        phase = _phase_for_bar(row.date, trade.date, is_last)
        snaps = {
            "entry_setup": _eval_bool(criteria.entry_setup, row, params),
            "entry_skip": _eval_bool(criteria.entry_skip, row, params),
            "setup_skip": _eval_bool(criteria.setup_skip, row, params),
            "exit_rule": _eval_bool(criteria.exit_rule, row, params),
        }
        bar_criteria.append(BarCriteria(date=row.date, phase=phase, criteria=snaps))

    return TradeTimeline(
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        strategy=trade.strategy,
        entry_date=trade.date,
        bars=tuple(bar_criteria),
    )
