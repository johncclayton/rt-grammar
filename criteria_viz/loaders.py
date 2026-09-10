"""Input loaders — RTS parse, trade list, bar CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from lark import Tree

from criteria_viz.models import BarRow, BarSeries, TradeRecord

# Reuse validator grammar loader when available.
try:
    from validate_rts import load_grammar, read_script
except ImportError:  # pragma: no cover — sketch fallback
    load_grammar = None
    read_script = None


def parse_rts_file(path: Path, *, grammar_path: Path) -> Tree:
    if load_grammar is None or read_script is None:
        raise RuntimeError("validate_rts helpers unavailable; run from repo root")
    parser = load_grammar(str(grammar_path), quiet=True)
    content = read_script(path)
    return parser.parse(content)


def _trade_id(strategy: str, symbol: str, date: str, action: str) -> str:
    return f"{strategy}:{symbol}:{date}:{action}"


def load_trades(path: Path) -> Sequence[TradeRecord]:
    """
    Load RealTest-style trade CSV (see tests/valid/stub_trades.csv).

    TLFields vary by script; Phase 0 assumes header row with Symbol, Action,
    Quantity, Price, Time, Date, Strategy columns.
    """
    rows: list[TradeRecord] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            symbol = raw.get("Symbol", "").strip()
            action = raw.get("Action", "").strip()
            date = raw.get("Date", "").strip()
            strategy = (raw.get("Strategy") or "default").strip()
            qty = float(raw.get("Quantity") or raw.get("QtyIn") or 0)
            price = float(raw.get("Price") or raw.get("PriceIn") or 0)
            time = (raw.get("Time") or raw.get("TimeIn") or "").strip()
            rows.append(
                TradeRecord(
                    trade_id=_trade_id(strategy, symbol, date, action),
                    symbol=symbol,
                    strategy=strategy,
                    action=action,
                    quantity=qty,
                    price=price,
                    date=date,
                    time=time,
                )
            )
    return rows


def load_bars(path: Path) -> dict[str, BarSeries]:
    """
    Load OHLCV CSV keyed by symbol.

    Phase 0: single-symbol files or a Symbol column per row.
    """
    by_symbol: dict[str, list[BarRow]] = {}
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            symbol = (raw.get("Symbol") or "SPY").strip()
            row = BarRow(
                date=raw["Date"].strip(),
                open=float(raw.get("Open") or raw.get("O") or 0),
                high=float(raw.get("High") or raw.get("H") or 0),
                low=float(raw.get("Low") or raw.get("L") or 0),
                close=float(raw.get("Close") or raw.get("C") or 0),
                volume=float(raw.get("Volume") or raw.get("V") or 0),
            )
            by_symbol.setdefault(symbol, []).append(row)

    return {
        sym: BarSeries(symbol=sym, rows=tuple(sorted(rows, key=lambda r: r.date)))
        for sym, rows in by_symbol.items()
    }
