"""Idempotent ``build_session()`` — eager bundle construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Optional

from criteria_viz.evaluate import compute_trade_timeline
from criteria_viz.extract import extract_strategy_criteria
from criteria_viz.loaders import load_bars, load_trades, parse_rts_file
from criteria_viz.models import SessionBundle, TradeTimeline


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _fingerprint(
    *,
    rts_path: Path,
    trades_path: Path,
    bars_path: Path,
    params: Optional[Mapping[str, float]],
) -> str:
    payload = {
        "rts": _file_digest(rts_path),
        "trades": _file_digest(trades_path),
        "bars": _file_digest(bars_path),
        "params": dict(sorted((params or {}).items())),
        "schema": 1,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def build_session(
    *,
    rts_path: str | Path,
    trades_path: str | Path,
    bars_path: str | Path,
    params: Optional[Mapping[str, float]] = None,
    grammar_path: str | Path = "realtest.lark",
) -> SessionBundle:
    """
    Build an immutable session bundle from RTS + trades + bars.

    Idempotent: identical inputs (file bytes + ``params``) yield the same
    ``fingerprint`` and equivalent timelines. Safe to call repeatedly; no
    global mutable state is consulted.
    """
    rts = Path(rts_path).resolve()
    trades = Path(trades_path).resolve()
    bars = Path(bars_path).resolve()
    grammar = Path(grammar_path).resolve()

    fingerprint = _fingerprint(
        rts_path=rts,
        trades_path=trades,
        bars_path=bars,
        params=params,
    )

    tree = parse_rts_file(rts, grammar_path=grammar)
    strategies = extract_strategy_criteria(tree)
    trade_rows = load_trades(trades)
    bar_map = load_bars(bars)

    timelines: dict[str, TradeTimeline] = {}
    for trade in trade_rows:
        strat = strategies.get(trade.strategy)
        if strat is None:
            raise KeyError(f"trade references unknown strategy {trade.strategy!r}")
        series = bar_map.get(trade.symbol)
        if series is None:
            raise KeyError(f"no bar data for symbol {trade.symbol!r}")
        timelines[trade.trade_id] = compute_trade_timeline(
            trade=trade,
            criteria=strat,
            bars=series,
            params=params or {},
        )

    return SessionBundle(
        fingerprint=fingerprint,
        rts_path=rts,
        strategies=strategies,
        trades=tuple(trade_rows),
        bars=bar_map,
        timelines=timelines,
    )
