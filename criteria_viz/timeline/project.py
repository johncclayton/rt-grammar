"""Project exported bar values onto criteria graph nodes for a trade window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from criteria_viz.export.plan import ExportPlan, SeriesSpec
from criteria_viz.export.store import BarSeries, CsvBarSeriesStore, value_at
from criteria_viz.graph.model import CriteriaGraph, TradePhase
from criteria_viz.trades.align import align_trade
from criteria_viz.trades.load import TradeRecord


@dataclass(frozen=True, slots=True)
class BarSnapshot:
    bar_index: int
    date: date
    values: Mapping[str, float | bool | None]
    changed: frozenset[str]


@dataclass(frozen=True, slots=True)
class CriteriaView:
    trade: TradeRecord
    phase: TradePhase
    strategy: str
    root_id: str
    graph: CriteriaGraph
    timeline: tuple[BarSnapshot, ...]
    signal_bar_index: int
    root_satisfied: bool


def _as_bool(value: float | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return value != 0


def build_criteria_view(
    graph: CriteriaGraph,
    plan: ExportPlan,
    store: CsvBarSeriesStore,
    trade: TradeRecord,
    phase: TradePhase,
    *,
    warmup: int = 20,
    padding: int = 5,
) -> CriteriaView:
    root_id = graph.root_for(trade.strategy, phase)
    if not root_id:
        raise ValueError(f"Strategy {trade.strategy} has no root for phase {phase.value}")

    signal_date = trade.date_in if phase == TradePhase.ENTRY else trade.date_out
    if signal_date is None:
        raise ValueError(f"Trade {trade.trade_id} has no date for phase {phase.value}")

    series = store.get(trade.symbol)
    signal_bar = align_trade(trade, series, phase_date=signal_date)

    start = max(0, signal_bar - warmup)
    end = min(len(series.dates) - 1, signal_bar + padding)

    spec_list = plan.per_strategy[trade.strategy].series
    spec_by_key = {s.key: s for s in spec_list}
    reachable = graph.reachable(root_id)

    timeline: list[BarSnapshot] = []
    prev: dict[str, float | bool | None] = {}

    for bar_index in range(start, end + 1):
        values: dict[str, float | bool | None] = {}
        for node_id in reachable:
            node = graph.node(node_id)
            if node.kind == "literal":
                continue
            values[node_id] = value_at(series, spec_by_key, node.series_key, bar_index)

        changed = frozenset(
            nid for nid, val in values.items() if nid not in prev or prev[nid] != val
        )
        timeline.append(
            BarSnapshot(
                bar_index=bar_index,
                date=series.dates[bar_index],
                values=values,
                changed=changed,
            )
        )
        prev = dict(values)

    signal_snapshot = timeline[signal_bar - start]
    root_val = signal_snapshot.values.get(root_id)
    root_satisfied = _as_bool(root_val)

    pruned_nodes = {nid: graph.node(nid) for nid in reachable}
    pruned = CriteriaGraph(
        nodes=pruned_nodes,
        roots={(trade.strategy, phase): root_id},
        strategies=graph.strategies,
        data_items=graph.data_items,
    )

    return CriteriaView(
        trade=trade,
        phase=phase,
        strategy=trade.strategy,
        root_id=root_id,
        graph=pruned,
        timeline=tuple(timeline),
        signal_bar_index=signal_bar,
        root_satisfied=root_satisfied,
    )
