"""Load trade lists from CSV."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from criteria_viz.errors import TradeError


@dataclass(frozen=True, slots=True)
class TradeRecord:
    trade_id: str
    strategy: str
    symbol: str
    date_in: date
    date_out: date | None
    action: str | None
    row_index: int


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise TradeError(f"Unrecognized trade date: {value!r}")


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "")


def load_trades_csv(
    path: Path,
    *,
    strategy_filter: str | None = None,
) -> tuple[TradeRecord, ...]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise TradeError(f"{path}: missing header row")

        header_map = {_normalize_header(h): h for h in reader.fieldnames}
        sym_col = _pick(header_map, ("symbol",))
        date_col = _pick(header_map, ("datein", "date"))
        strat_col = _pick(header_map, ("strategy",), required=False)
        date_out_col = _pick(header_map, ("dateout",), required=False)
        action_col = _pick(header_map, ("action",), required=False)

        trades: list[TradeRecord] = []
        for i, row in enumerate(reader):
            symbol = row[sym_col].strip().upper()
            strategy = row[strat_col].strip() if strat_col else "default"
            if strategy_filter and strategy != strategy_filter:
                continue
            date_in = _parse_date(row[date_col])
            date_out = _parse_date(row[date_out_col]) if date_out_col and row.get(date_out_col, "").strip() else None
            action = row[action_col].strip() if action_col else None
            trade_id = f"{strategy}:{symbol}:{date_in.isoformat()}:{action or 'trade'}"
            trades.append(
                TradeRecord(
                    trade_id=trade_id,
                    strategy=strategy,
                    symbol=symbol,
                    date_in=date_in,
                    date_out=date_out,
                    action=action,
                    row_index=i,
                )
            )

    if not trades:
        raise TradeError(f"No trades loaded from {path}")

    return tuple(trades)


def _pick(header_map: dict[str, str], names: tuple[str, ...], *, required: bool = True) -> str | None:
    for name in names:
        if name in header_map:
            return header_map[name]
    if required:
        raise TradeError(f"Trade CSV missing required column (one of {names})")
    return None
