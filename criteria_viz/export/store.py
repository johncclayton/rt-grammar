from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from criteria_viz.errors import ExportError
from criteria_viz.export.plan import ExportPlan, SeriesSpec, export_date_column


@dataclass(frozen=True, slots=True)
class BarSeries:
    symbol: str
    dates: tuple[date, ...]
    columns: Mapping[str, tuple[float | bool | None, ...]]


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ExportError(f"Unrecognized date format: {value!r}")


def _parse_cell(value: str) -> float | bool | None:
    value = value.strip()
    if value == "":
        return None
    lower = value.lower()
    if lower in ("true", "t", "yes"):
        return True
    if lower in ("false", "f", "no"):
        return False
    try:
        if "." in value or "e" in lower:
            return float(value)
        return float(int(value))
    except ValueError:
        return None


class CsvBarSeriesStore:
    def __init__(self, series_by_symbol: Mapping[str, BarSeries]):
        self._series = dict(series_by_symbol)

    @classmethod
    def from_directory(
        cls,
        series_dir: Path,
        *,
        plan: ExportPlan,
        strategy: str,
    ) -> "CsvBarSeriesStore":
        spec = plan.per_strategy[strategy]
        required = {s.csv_column for s in spec.series}
        date_col = export_date_column()
        required.add(date_col)

        loaded: dict[str, BarSeries] = {}
        for csv_path in sorted(series_dir.glob("*.csv")):
            symbol = csv_path.stem.upper()
            loaded[symbol] = _load_symbol_csv(
                csv_path, required_columns=required, date_column=date_col
            )
        return cls(loaded)

    def get(self, symbol: str) -> BarSeries:
        key = symbol.upper()
        if key not in self._series:
            raise ExportError(f"No series file for symbol {symbol!r} in export directory")
        return self._series[key]

    def symbols(self) -> Sequence[str]:
        return tuple(sorted(self._series.keys()))


def _load_symbol_csv(
    path: Path, *, required_columns: set[str], date_column: str
) -> BarSeries:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ExportError(f"{path}: empty or missing header")
        fields = {f.strip() for f in reader.fieldnames}
        missing = required_columns - fields
        if missing:
            raise ExportError(f"{path}: missing columns: {sorted(missing)}")

        dates: list[date] = []
        value_columns = required_columns - {date_column}
        column_buffers: dict[str, list[float | bool | None]] = {c: [] for c in value_columns}

        for row in reader:
            dates.append(_parse_date(row[date_column]))
            for col in column_buffers:
                column_buffers[col].append(_parse_cell(row.get(col, "")))

    symbol = path.stem.upper()
    columns = {col: tuple(vals) for col, vals in column_buffers.items()}
    return BarSeries(symbol=symbol, dates=tuple(dates), columns=columns)


def value_at(
    series: BarSeries,
    spec_by_key: Mapping[str, SeriesSpec],
    series_key: str,
    bar_index: int,
    *,
    expr_source: str | None = None,
    expr_to_col: Mapping[str, str] | None = None,
) -> float | bool | None:
    spec = spec_by_key.get(series_key)
    if spec is None:
        if expr_source and expr_to_col and expr_source in expr_to_col:
            col = expr_to_col[expr_source]
        else:
            raise ExportError(f"No export spec for series_key {series_key!r}")
    else:
        col = spec.csv_column
    if col not in series.columns:
        raise ExportError(f"Column {col!r} not loaded for {series.symbol}")
    return series.columns[col][bar_index]
