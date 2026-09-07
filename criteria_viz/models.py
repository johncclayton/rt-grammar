"""Shared value types for trade criteria visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping, Optional

from criteria_viz.graph import CriteriaGraph, NodeId


Scalar = float | bool | None


class TradePhase(str, Enum):
    """Which strategy formula root to replay."""

    ENTRY = "entry"
    EXIT = "exit"

    @property
    def strategy_keyword(self) -> str:
        return "EntrySetup" if self is TradePhase.ENTRY else "ExitRule"


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """One row from a RealTest-style trades export."""

    index: int
    symbol: str
    action: str  # Buy, Sell, …
    quantity: float
    price: float
    trade_time: Optional[datetime]
    trade_date: date
    strategy: Optional[str] = None
    extra: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BarSnapshot:
    """Criterion node values on a single bar."""

    bar_index: int
    trade_date: date
    values: Mapping[NodeId, Scalar]
    changed: tuple[NodeId, ...] = ()

    @property
    def date(self) -> date:
        return self.trade_date


@dataclass(frozen=True, slots=True)
class TradeCriteriaView:
    """Bar-by-bar replay of compound criteria for one trade and phase."""

    trade: TradeRecord
    phase: TradePhase
    strategy: str
    root_id: NodeId
    graph: CriteriaGraph
    timeline: tuple[BarSnapshot, ...]
    signal_bar: BarSnapshot
    root_satisfied: bool
    lookback_bars: int

    def to_json(self) -> dict[str, Any]:
        """Serialize for the web UI and CLI --format json."""
        g = self.graph
        return {
            "trade": {
                "index": self.trade.index,
                "symbol": self.trade.symbol,
                "action": self.trade.action,
                "date": self.trade.trade_date.isoformat(),
                "strategy": self.trade.strategy,
            },
            "phase": self.phase.value,
            "strategy": self.strategy,
            "root_id": self.root_id,
            "root_satisfied": self.root_satisfied,
            "lookback_bars": self.lookback_bars,
            "nodes": [
                {
                    "id": nid,
                    "label": g.node_label(nid),
                    "kind": g.nodes[nid].kind.name,
                    "deps": list(g.nodes[nid].deps),
                    "expr_source": g.nodes[nid].expr_source,
                }
                for nid in g.reachable_from(self.root_id)
            ],
            "timeline": [
                {
                    "bar_index": snap.bar_index,
                    "date": snap.trade_date.isoformat(),
                    "values": {nid: snap.values.get(nid) for nid in g.reachable_from(self.root_id)},
                    "changed": list(snap.changed),
                }
                for snap in self.timeline
            ],
            "signal_bar_index": self.signal_bar.bar_index,
        }
