"""Frozen value types for the snapshot bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class CriterionSnapshot:
    """Truth value (and optional decomposition) for one criterion on one bar."""

    name: str
    expr: str
    value: bool
    parts: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class BarCriteria:
    date: str
    phase: str  # setup | entry | hold | exit
    criteria: Mapping[str, CriterionSnapshot]


@dataclass(frozen=True)
class TradeTimeline:
    trade_id: str
    symbol: str
    strategy: str
    entry_date: str
    bars: tuple[BarCriteria, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "entry_date": self.entry_date,
            "bars": [
                {
                    "date": b.date,
                    "phase": b.phase,
                    "criteria": {
                        name: {
                            "expr": c.expr,
                            "value": c.value,
                            **({"parts": dict(c.parts)} if c.parts else {}),
                        }
                        for name, c in b.criteria.items()
                    },
                }
                for b in self.bars
            ],
        }


@dataclass(frozen=True)
class TradeRecord:
    trade_id: str
    symbol: str
    strategy: str
    action: str
    quantity: float
    price: float
    date: str
    time: str = ""


@dataclass(frozen=True)
class StrategyCriteria:
    """Extracted criterion expressions for one Strategy: block."""

    name: str
    compounded: bool
    entry_setup: Optional[str] = None
    entry_skip: Optional[str] = None
    setup_skip: Optional[str] = None
    exit_rule: Optional[str] = None


@dataclass(frozen=True)
class BarRow:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    extras: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class BarSeries:
    symbol: str
    rows: tuple[BarRow, ...]


@dataclass(frozen=True)
class SessionBundle:
    """
    Immutable session snapshot. All API reads project from this object.

    ``timelines`` is fully populated by ``build_session()``; handlers must not
    recompute formulas or reload source files.
    """

    fingerprint: str
    rts_path: Path
    strategies: Mapping[str, StrategyCriteria]
    trades: tuple[TradeRecord, ...]
    bars: Mapping[str, BarSeries]
    timelines: Mapping[str, TradeTimeline]
