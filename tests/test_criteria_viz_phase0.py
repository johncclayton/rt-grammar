"""Phase 0 tests for criteria_viz."""

from __future__ import annotations

import unittest
from pathlib import Path

from criteria_viz.export.plan import build_export_plan_from_rts, render_companion_snippet
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

    def test_export_plan_dual_snippets(self):
        plan = build_export_plan_from_rts(RTS, strategy="MeanReversion")
        results = render_companion_snippet(plan, "MeanReversion", backend="results")
        scan = render_companion_snippet(plan, "MeanReversion", backend="scan")

        self.assertIn("Results:", results)
        self.assertIn("EntrySetup", results)
        self.assertIn("Scan:", scan)
        self.assertIn("SaveScanAs:", scan)

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
