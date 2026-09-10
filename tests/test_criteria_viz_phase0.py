"""Phase 0 tests for criteria_viz."""

from __future__ import annotations

import unittest
from pathlib import Path

from criteria_viz.export.plan import (
    build_export_plan_from_rts,
    export_date_column,
    render_companion_snippet,
)
from criteria_viz.graph.expr_text import expr_to_text
from criteria_viz.graph.parse_rts import extract_script, parse_rts_file
from criteria_viz.export.reserved import is_reserved_item_name
from criteria_viz.export.store import CsvBarSeriesStore
from criteria_viz.graph.build import build_criteria_graph
from criteria_viz.graph.model import TradePhase
from criteria_viz.timeline.project import build_criteria_view
from criteria_viz.trades.load import load_trades_csv

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "criteria_viz"
RTS = FIXTURES / "mean_reversion.rts"
TRADES = FIXTURES / "trades.csv"
SERIES_DIR = FIXTURES / "series"


class CriteriaVizPhase0Tests(unittest.TestCase):
    def test_graph_deep_decomposition(self):
        graph = build_criteria_graph(RTS, strategy="MeanReversion")

        self.assertEqual(graph.strategies, ("MeanReversion",))
        self.assertIn("data:Oversold", graph.nodes)
        self.assertIn("data:AboveTrend", graph.nodes)
        self.assertEqual(
            graph.root_for("MeanReversion", TradePhase.ENTRY),
            "strategy:MeanReversion:EntrySetup",
        )

        entry_root = graph.root_for("MeanReversion", TradePhase.ENTRY)
        reachable = graph.reachable(entry_root)
        and_nodes = [nid for nid in reachable if graph.node(nid).kind == "and"]
        self.assertTrue(and_nodes, "expected deep AND node under EntrySetup")

        oversold = graph.node("data:Oversold")
        self.assertTrue(oversold.deps, "Oversold should decompose to cmp/call children")

    def test_expr_to_text_additive_multiplicative(self):
        snippet = FIXTURES / "_expr_text_snippet.rts"
        snippet.write_text(
            "Data:\n"
            "\ta: 1 - mr1_PcntLower / 100\n"
            "\tb: ATR(5) * mr1_AtrOversold\n"
            "\tc: 0.02 * C\n"
            "\td: Min(C, Open) - ATR(5) * x\n"
            "Strategy: S\n"
            "\tEntrySetup: True\n"
            "\tExitRule: True\n",
            encoding="utf-8",
        )
        try:
            data_items, _ = extract_script(parse_rts_file(snippet))
            expected = {
                "a": "1 - mr1_PcntLower / 100",
                "b": "ATR(5) * mr1_AtrOversold",
                "c": "0.02 * C",
                "d": "Min(C, Open) - ATR(5) * x",
            }
            for name, want in expected.items():
                self.assertEqual(expr_to_text(data_items[name]), want, msg=name)
        finally:
            snippet.unlink(missing_ok=True)

    def test_export_columns_avoid_reserved_names(self):
        plan = build_export_plan_from_rts(RTS, strategy="MeanReversion")
        cols = [s.csv_column for s in plan.per_strategy["MeanReversion"].series]
        for col in cols:
            self.assertFalse(is_reserved_item_name(col), f"reserved export name: {col}")

    def test_export_plan_testscan_snippet(self):
        plan = build_export_plan_from_rts(RTS, strategy="MeanReversion")
        scan = render_companion_snippet(plan, "MeanReversion", backend="scan")

        self.assertIn("Include this file FROM the primary strategy", scan)
        self.assertIn("MeanReversion_scan.rts", scan)
        self.assertIn("TestSettings:", scan)
        self.assertIn("TestOutput:", scan)
        self.assertIn("TestScanAllDates:", scan)
        self.assertIn("TestScan:", scan)
        self.assertNotRegex(scan, r"(?m)^Scan:")
        self.assertIn("SaveScanAs:", scan)
        date_col = export_date_column()
        self.assertIn(f"{date_col}:", scan)
        self.assertIn(f"Sort:\t\t{date_col}, Sym", scan)
        self.assertNotRegex(scan, r"^\tDate:\t", scan)
        self.assertNotIn("Data:", scan)
        self.assertIn("RSIV < RSIThreshold", scan)
        self.assertIn("RSI(RSIPeriod)", scan)
        self.assertNotRegex(scan, r"^\tRSIPeriod:\t", scan)

    def test_check_fixture_trade_entry(self):
        graph = build_criteria_graph(RTS, strategy="MeanReversion")
        plan = build_export_plan_from_rts(RTS, strategy="MeanReversion")
        store = CsvBarSeriesStore.from_directory(SERIES_DIR, plan=plan, strategy="MeanReversion")
        trades = load_trades_csv(TRADES, strategy_filter="MeanReversion")
        trade = trades[0]

        view = build_criteria_view(
            graph, plan, store, trade, TradePhase.ENTRY, warmup=5, padding=2
        )

        self.assertTrue(view.root_satisfied)
        signal_snap = view.timeline[view.signal_bar_index - view.timeline[0].bar_index]
        self.assertIn(signal_snap.values[view.root_id], (1, True, 1.0))


if __name__ == "__main__":
    unittest.main()
