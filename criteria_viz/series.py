"""Pluggable per-bar value backends."""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from criteria_viz.graph import CriteriaGraph
from criteria_viz.models import Scalar


class BarSeries(ABC):
    """Read bar-aligned values for symbols and formula identifiers."""

    @abstractmethod
    def dates_for(self, symbol: str) -> Sequence[date]:
        """All bar dates available for symbol, ascending."""

    @abstractmethod
    def value(self, symbol: str, item: str, bar_index: int) -> Scalar:
        """Value of ``item`` (data item name or builtin) on ``bar_index``."""

    @abstractmethod
    def items_available(self, symbol: str) -> frozenset[str]:
        """Column / series names present for symbol."""

    def bar_index_on_or_before(self, symbol: str, target: date) -> int | None:
        dates = self.dates_for(symbol)
        for i in range(len(dates) - 1, -1, -1):
            if dates[i] <= target:
                return i
        return None


@dataclass
class CsvBarSeries(BarSeries):
    """v1 backend: wide CSV with Date, Symbol, and value columns."""

    _by_symbol: Mapping[str, list[date]]
    _columns: Mapping[str, Mapping[str, list[Scalar]]]  # symbol -> item -> series

    @classmethod
    def from_csv(cls, path: Path | str) -> CsvBarSeries:
        path = Path(path)
        by_symbol: dict[str, list[date]] = {}
        columns: dict[str, dict[str, list[Scalar]]] = {}
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                sym = row["Symbol"]
                d = date.fromisoformat(row["Date"])
                by_symbol.setdefault(sym, []).append(d)
                bucket = columns.setdefault(sym, {})
                for key, raw in row.items():
                    if key in ("Symbol", "Date"):
                        continue
                    bucket.setdefault(key, []).append(_parse_scalar(raw))
        return cls(_by_symbol=by_symbol, _columns=columns)

    def dates_for(self, symbol: str) -> Sequence[date]:
        return self._by_symbol[symbol]

    def value(self, symbol: str, item: str, bar_index: int) -> Scalar:
        return self._columns[symbol][item][bar_index]

    def items_available(self, symbol: str) -> frozenset[str]:
        return frozenset(self._columns[symbol])


@dataclass
class MockBarSeries(BarSeries):
    """Deterministic series for unit tests without RealTest export."""

    _dates: Mapping[str, Sequence[date]]
    _values: Mapping[str, Mapping[str, Sequence[Scalar]]]

    @classmethod
    def for_graph(
        cls,
        graph: CriteriaGraph,
        symbol: str,
        dates: Sequence[date],
        overrides: Mapping[str, Sequence[Scalar]] | None = None,
    ) -> MockBarSeries:
        """Seed columns for each data item in graph; caller supplies overrides."""
        items = {name: [0.0] * len(dates) for name in graph.data_items}
        if overrides:
            items.update(overrides)
        return cls(_dates={symbol: dates}, _values={symbol: items})

    def dates_for(self, symbol: str) -> Sequence[date]:
        return self._dates[symbol]

    def value(self, symbol: str, item: str, bar_index: int) -> Scalar:
        return self._values[symbol][item][bar_index]

    def items_available(self, symbol: str) -> frozenset[str]:
        return frozenset(self._values[symbol])


def _parse_scalar(raw: str) -> Scalar:
    if raw in ("", "NaN", "nan"):
        return None
    if raw in ("True", "true", "1"):
        return True
    if raw in ("False", "false", "0"):
        return False
    return float(raw)
