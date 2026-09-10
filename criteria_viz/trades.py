"""Load RealTest-style trades CSV (internal)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

from criteria_viz.models import TradeRecord


def load_trades(path: Path | str) -> list[TradeRecord]:
    path = Path(path)
    records: list[TradeRecord] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for index, row in enumerate(reader):
            trade_date = _parse_date(row.get("Date", ""))
            trade_time = _parse_time(row.get("Time", ""), trade_date)
            records.append(
                TradeRecord(
                    index=index,
                    symbol=row["Symbol"],
                    action=row.get("Action", ""),
                    quantity=float(row.get("Quantity") or 0),
                    price=float(row.get("Price") or 0),
                    trade_time=trade_time,
                    trade_date=trade_date,
                    strategy=row.get("Strategy") or None,
                    extra={k: v for k, v in row.items() if k not in _CORE_COLUMNS},
                )
            )
    return records


_CORE_COLUMNS = frozenset(
    {"Symbol", "Action", "Quantity", "Price", "Time", "Date", "Strategy"}
)


def _parse_date(raw: str) -> date:
    # RealTest exports vary; v1 accepts ISO and YYYY-MM-DD
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 100:
                y += 2000
            return date(y, m, d)
    return date.fromisoformat(raw)


def _parse_time(raw: str, trade_date: date) -> datetime | None:
    if not raw:
        return None
    hour, minute = raw.split(":")[:2]
    return datetime(trade_date.year, trade_date.month, trade_date.day, int(hour), int(minute))
