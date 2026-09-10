"""Read-only projections from a frozen SessionBundle."""

from __future__ import annotations

from criteria_viz.models import SessionBundle, TradeTimeline


def get_trade_timeline(session: SessionBundle, trade_id: str) -> TradeTimeline:
    """
    Pure projection: return precomputed timeline for ``trade_id``.

    Raises ``KeyError`` if unknown. Does not parse, load, or evaluate.
    """
    try:
        return session.timelines[trade_id]
    except KeyError as exc:
        raise KeyError(f"unknown trade_id: {trade_id!r}") from exc


def list_trades(session: SessionBundle) -> tuple[dict, ...]:
    """Lightweight trade index for GET /trades."""
    return tuple(
        {
            "trade_id": t.trade_id,
            "symbol": t.symbol,
            "strategy": t.strategy,
            "date": t.date,
            "action": t.action,
        }
        for t in session.trades
    )


def session_meta(session: SessionBundle) -> dict:
    return {
        "fingerprint": session.fingerprint,
        "rts_path": str(session.rts_path),
        "strategies": list(session.strategies.keys()),
        "trade_count": len(session.trades),
        "symbols": sorted(session.bars.keys()),
    }
