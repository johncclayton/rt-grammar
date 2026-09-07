"""Minimal web UI — consumes TradeCriteriaView JSON from CriteriaTimelineService."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from criteria_viz.service import CriteriaTimelineService


def create_app(service: CriteriaTimelineService):
    """Return a FastAPI (or Flask) app with /api/trades and /api/view endpoints.

    Implementation deferred to post-slice-1; sketch signatures only.
    """
    raise NotImplementedError("web UI follows mock-series integration test")


def run_server(service: CriteriaTimelineService, *, port: int = 8765) -> None:
    """Block and serve static graph + timeline scrubber."""
    app = create_app(service)
    # uvicorn.run(app, host="127.0.0.1", port=port)
    raise NotImplementedError("web UI follows mock-series integration test")
