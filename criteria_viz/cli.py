"""CLI for trade criteria visualization (v1 sketch)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from criteria_viz import (
    CriteriaTimelineService,
    CsvBarSeries,
    MockBarSeries,
    TradePhase,
    build_criteria_graph,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Visualize how RTS entry/exit criteria evolved bar-by-bar per trade.",
    )
    parser.add_argument("--rts", required=True, type=Path, help="RealTest .rts strategy file")
    parser.add_argument("--trades", required=True, type=Path, help="Trades CSV export")
    parser.add_argument("--series", type=Path, help="Bar values CSV export")
    parser.add_argument("--mock-series", action="store_true", help="Use MockBarSeries (tests)")
    parser.add_argument("--strategy", help="Strategy name when script defines several")
    parser.add_argument("--trade", type=int, default=0, help="Trade row index (0-based)")
    parser.add_argument(
        "--phase",
        choices=[p.value for p in TradePhase],
        default=TradePhase.ENTRY.value,
    )
    parser.add_argument("--lookback", type=int, default=30)
    parser.add_argument("--all", action="store_true", help="Emit views for every trade")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("-o", "--output", type=Path, help="Write JSON to file instead of stdout")
    parser.add_argument("--serve", action="store_true", help="Start web UI")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    graph = build_criteria_graph(args.rts, strategy=args.strategy)
    if args.mock_series:
        # Slice 1: caller must extend with scenario-specific overrides
        series = MockBarSeries(_dates={}, _values={})
    elif args.series:
        series = CsvBarSeries.from_csv(args.series)
    else:
        parser.error("provide --series or --mock-series")

    service = CriteriaTimelineService(
        graph=graph,
        series=series,
        trades_csv=args.trades,
        default_strategy=args.strategy,
        lookback_bars=args.lookback,
    )

    phase = TradePhase(args.phase)

    if args.serve:
        from criteria_viz.web.app import run_server

        run_server(service, port=args.port)
        return 0

    if args.all:
        payload = [v.to_json() for v in service.all_views(phase)]
    else:
        view = service.view_for_trade(args.trade, phase)
        payload = view.to_json() if view else {"error": "no criterion for phase"}

    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
