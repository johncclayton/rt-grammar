# Trade criteria visualizer (v1 design)

Analyze RealTest `.rts` strategy files to discover which data items and formulas drive entry/exit criteria, then replay how those compound criteria evolved bar-by-bar until each trade's signal fired.

**Design candidate:** Criteria Graph Center (B). The load-bearing type is `CriteriaGraph`; bar history is supplied by a pluggable `BarSeries` backend. A single `CriteriaTimelineService` produces a `TradeCriteriaView` for any trade and phase.

## Quick start (intended v1 CLI)

```bash
# Analyze one trade's entry criteria and open the local UI
python -m criteria_viz \
  --rts example_strategy.rts \
  --trades playback_trades.csv \
  --trade 0 \
  --phase entry \
  --series export_values.csv \
  --serve

# Batch JSON for all trades (no UI)
python -m criteria_viz \
  --rts example_strategy.rts \
  --trades playback_trades.csv \
  --series export_values.csv \
  --all \
  --format json \
  -o criteria_timelines.json
```

Inputs:

| Input | Role |
|-------|------|
| `.rts` | Strategy script; `Data:` items and `Strategy:` entry/exit formulas are parsed into a `CriteriaGraph` |
| trades CSV | RealTest-style trade list (`Symbol`, `Date`, `Time`, `Action`, `Strategy`, …) — identifies which trade and when it fired |
| series CSV (v1) | Per-bar exported values for symbols and data items referenced by the graph (mock backend available for tests) |

Output: `TradeCriteriaView` — graph layout + bar-by-bar node values from the lookback window through the signal bar.

## Library usage

```python
from pathlib import Path
from criteria_viz import (
    CriteriaTimelineService,
    CsvBarSeries,
    build_criteria_graph,
    TradePhase,
)

graph = build_criteria_graph(Path("example_strategy.rts"), strategy="MeanReversion")
series = CsvBarSeries.from_csv(Path("export_values.csv"))
service = CriteriaTimelineService(graph=graph, series=series, trades_csv=Path("trades.csv"))

view = service.view_for_trade(trade_index=0, phase=TradePhase.ENTRY)
print(view.signal_bar.date, view.root_satisfied)  # e.g. 2020-01-02 True
```

See `rationale.md` for the full design and `__init__.py` for the public surface.
