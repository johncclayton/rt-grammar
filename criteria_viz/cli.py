"""CLI for criteria_viz Phase 0: plan and check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from criteria_viz.errors import CriteriaVizError
from criteria_viz.export.plan import (
    build_export_plan_from_rts,
    render_companion_snippet,
    write_export_plan,
)
from criteria_viz.export.store import CsvBarSeriesStore
from criteria_viz.graph.build import build_criteria_graph
from criteria_viz.graph.model import TradePhase
from criteria_viz.timeline.project import build_criteria_view
from criteria_viz.trades.load import load_trades_csv


def _cmd_plan(args: argparse.Namespace) -> int:
    plan = build_export_plan_from_rts(Path(args.rts), strategy=args.strategy)
    out = Path(args.output)
    write_export_plan(out, plan)
    print(f"Wrote export plan: {out}")

    strategy = args.strategy or plan.strategies[0]
    snippets_dir = out.parent / "companion_snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)

    for backend in ("results", "scan"):
        snippet = render_companion_snippet(plan, strategy, backend=backend)
        snippet_path = snippets_dir / f"{strategy}_{backend}.rts"
        snippet_path.write_text(snippet, encoding="utf-8")
        print(f"Wrote companion snippet ({backend}): {snippet_path}")

    print(f"Series columns ({strategy}): {len(plan.per_strategy[strategy].series)}")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    rts_path = Path(args.rts)
    trades_path = Path(args.trades)
    series_dir = Path(args.series)

    graph = build_criteria_graph(rts_path, strategy=args.strategy)
    plan = build_export_plan_from_rts(rts_path, strategy=args.strategy)
    strategy = args.strategy or graph.strategies[0]

    store = CsvBarSeriesStore.from_directory(series_dir, plan=plan, strategy=strategy)
    trades = load_trades_csv(trades_path, strategy_filter=strategy)

    failures = 0
    for trade in trades:
        for phase in (TradePhase.ENTRY, TradePhase.EXIT):
            if phase == TradePhase.EXIT and trade.date_out is None:
                continue
            try:
                view = build_criteria_view(
                    graph,
                    plan,
                    store,
                    trade,
                    phase,
                    warmup=args.warmup,
                    padding=args.padding,
                )
            except (CriteriaVizError, ValueError) as exc:
                print(f"FAIL {trade.trade_id} {phase.value}: {exc}")
                failures += 1
                continue

            snap = view.timeline[view.signal_bar_index - view.timeline[0].bar_index]
            root_val = snap.values.get(view.root_id)
            ok = view.root_satisfied
            status = "OK" if ok else "WARN"
            print(
                f"{status} {trade.trade_id} {phase.value} "
                f"signal={snap.date} root={view.root_id} value={root_val}"
            )
            if not ok:
                failures += 1

    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="criteria_viz", description="Trade criteria visualizer (Phase 0)")
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Emit export plan JSON and companion RTS snippets")
    plan_p.add_argument("rts", help="Path to .rts strategy file")
    plan_p.add_argument("-o", "--output", default="export_plan.json", help="Output plan JSON path")
    plan_p.add_argument("--strategy", help="Strategy name (required if multiple strategies)")
    plan_p.set_defaults(func=_cmd_plan)

    check_p = sub.add_parser("check", help="Validate exported series against trades")
    check_p.add_argument("--rts", required=True, help="Path to .rts strategy file")
    check_p.add_argument("--trades", required=True, help="Path to trades CSV")
    check_p.add_argument("--series", required=True, help="Directory of per-symbol series CSV exports")
    check_p.add_argument("--strategy", help="Strategy name filter")
    check_p.add_argument("--warmup", type=int, default=20, help="Bars before signal")
    check_p.add_argument("--padding", type=int, default=5, help="Bars after signal")
    check_p.set_defaults(func=_cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CriteriaVizError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
