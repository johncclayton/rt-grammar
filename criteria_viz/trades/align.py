"""Align trade dates to bar indices in exported series."""

from __future__ import annotations

from datetime import date

from criteria_viz.errors import TradeError
from criteria_viz.export.store import BarSeries
from criteria_viz.trades.load import TradeRecord


def align_date_to_bar(series: BarSeries, target: date) -> int:
    for i, d in enumerate(series.dates):
        if d == target:
            return i
    raise TradeError(
        f"No bar on {target.isoformat()} for {series.symbol} "
        f"(series range {series.dates[0]} .. {series.dates[-1]})"
    )


def align_trade(
    trade: TradeRecord,
    series: BarSeries,
    *,
    phase_date: date,
) -> int:
    try:
        return align_date_to_bar(series, phase_date)
    except TradeError as exc:
        raise TradeError(f"Trade {trade.trade_id}: {exc}") from exc
