"""
Trade criteria visualizer — Snapshot Bundle (Candidate C).

Public API (small surface):
    build_session  — idempotent bundle construction at startup
    serve          — read-only FastAPI over a frozen SessionBundle
    get_trade_timeline — pure projection from bundle to one trade
"""

from criteria_viz.bundle import build_session
from criteria_viz.projections import get_trade_timeline
from criteria_viz.serve import serve

__all__ = ["build_session", "serve", "get_trade_timeline"]
