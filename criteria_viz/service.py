"""CriteriaTimelineService — project CriteriaGraph onto BarSeries per trade."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

from criteria_viz.evaluate import evaluate_graph
from criteria_viz.graph import CriteriaGraph
from criteria_viz.models import BarSnapshot, TradeCriteriaView, TradePhase, TradeRecord
from criteria_viz.series import BarSeries
from criteria_viz.trades import load_trades


class CriteriaTimelineService:
    """Single entry point: graph + series + trades → TradeCriteriaView."""

    def __init__(
        self,
        graph: CriteriaGraph,
        series: BarSeries,
        trades_csv: Path | str,
        *,
        default_strategy: Optional[str] = None,
        lookback_bars: int = 30,
    ) -> None:
        self._graph = graph
        self._series = series
        self._trades = load_trades(trades_csv)
        self._default_strategy = default_strategy or _infer_single_strategy(graph)
        self._lookback = lookback_bars

    @property
    def trades(self) -> tuple[TradeRecord, ...]:
        return tuple(self._trades)

    def view_for_trade(
        self,
        trade_index: int,
        phase: TradePhase,
        *,
        lookback_bars: Optional[int] = None,
    ) -> Optional[TradeCriteriaView]:
        trade = self._trades[trade_index]
        strategy = trade.strategy or self._default_strategy
        if strategy is None:
            raise ValueError("trade has no Strategy column and graph has multiple strategies")

        root_id = self._graph.root_for(strategy, phase.value)
        if root_id is None:
            return None

        signal_idx = self._series.bar_index_on_or_before(trade.symbol, trade.trade_date)
        if signal_idx is None:
            raise ValueError(f"no bars for {trade.symbol} on or before {trade.trade_date}")

        lookback = lookback_bars if lookback_bars is not None else self._lookback
        start = max(0, signal_idx - lookback)
        timeline: list[BarSnapshot] = []
        prev_values: dict = {}

        for bar_index in range(start, signal_idx + 1):
            dates = self._series.dates_for(trade.symbol)
            values = evaluate_graph(
                self._graph, self._series, trade.symbol, bar_index, root_id
            )
            changed = tuple(nid for nid, val in values.items() if prev_values.get(nid) != val)
            snap = BarSnapshot(
                bar_index=bar_index,
                trade_date=dates[bar_index],
                values=values,
                changed=changed,
            )
            timeline.append(snap)
            prev_values = dict(values)

        signal_bar = timeline[-1]
        root_val = signal_bar.values[root_id]
        subgraph = self._graph.subgraph(root_id)

        return TradeCriteriaView(
            trade=trade,
            phase=phase,
            strategy=strategy,
            root_id=root_id,
            graph=subgraph,
            timeline=tuple(timeline),
            signal_bar=signal_bar,
            root_satisfied=bool(root_val),
            lookback_bars=lookback,
        )

    def all_views(self, phase: TradePhase) -> Iterator[TradeCriteriaView]:
        for i in range(len(self._trades)):
            view = self.view_for_trade(i, phase)
            if view is not None:
                yield view


def _infer_single_strategy(graph: CriteriaGraph) -> Optional[str]:
    names = {key[0] for key in graph.roots}
    if len(names) == 1:
        return next(iter(names))
    return None
