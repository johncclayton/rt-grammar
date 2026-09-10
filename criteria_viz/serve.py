"""Read-only FastAPI server over a frozen SessionBundle."""

from __future__ import annotations

from criteria_viz.models import SessionBundle
from criteria_viz.projections import get_trade_timeline, list_trades, session_meta


def create_app(session: SessionBundle):
    """
    Factory: bind ``session`` into a read-only FastAPI app.

    No mutation routes; no reload; no shared mutable state beyond the frozen
    bundle reference held in closure.
    """
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "fastapi is required for serve(); install with pip install rt-grammar[viz]"
        ) from exc

    app = FastAPI(title="criteria_viz", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "fingerprint": session.fingerprint}

    @app.get("/session/meta")
    def meta():
        return session_meta(session)

    @app.get("/trades")
    def trades():
        return list_trades(session)

    @app.get("/trades/{trade_id}/timeline")
    def timeline(trade_id: str):
        try:
            return get_trade_timeline(session, trade_id).to_dict()
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown trade_id: {trade_id}")

    @app.get("/strategies/{strategy_name}/criteria")
    def strategy_criteria(strategy_name: str):
        crit = session.strategies.get(strategy_name)
        if crit is None:
            raise HTTPException(status_code=404, detail=f"unknown strategy: {strategy_name}")
        return {
            "name": crit.name,
            "compounded": crit.compounded,
            "entry_setup": crit.entry_setup,
            "entry_skip": crit.entry_skip,
            "setup_skip": crit.setup_skip,
            "exit_rule": crit.exit_rule,
        }

    return app


def serve(session: SessionBundle, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Block until interrupted; serves projections from ``session`` only."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "uvicorn is required for serve(); install with pip install rt-grammar[viz]"
        ) from exc

    uvicorn.run(create_app(session), host=host, port=port, log_level="info")
