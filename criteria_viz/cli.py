"""CLI entry: build bundle at startup, serve read-only API."""

from __future__ import annotations

import argparse
import sys

from criteria_viz.bundle import build_session
from criteria_viz.serve import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="criteria_viz", description="Trade criteria visualizer")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_p = sub.add_parser("serve", help="Build session bundle once, serve read-only API")
    serve_p.add_argument("--rts", required=True, help="Path to .rts strategy script")
    serve_p.add_argument("--trades", required=True, help="Path to trade list CSV")
    serve_p.add_argument("--bars", required=True, help="Path to OHLCV bar CSV")
    serve_p.add_argument("--grammar", default="realtest.lark", help="Lark grammar path")
    serve_p.add_argument("--host", default="127.0.0.1")
    serve_p.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)

    if args.command == "serve":
        print("[criteria_viz] building session bundle …", file=sys.stderr)
        session = build_session(
            rts_path=args.rts,
            trades_path=args.trades,
            bars_path=args.bars,
            grammar_path=args.grammar,
        )
        print(f"[criteria_viz] session fingerprint: {session.fingerprint}", file=sys.stderr)
        print(f"[criteria_viz] precomputed timelines: {len(session.timelines)}", file=sys.stderr)
        print(f"[criteria_viz] serving read-only API at http://{args.host}:{args.port}", file=sys.stderr)
        serve(session, host=args.host, port=args.port)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
