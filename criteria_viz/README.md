# criteria_viz (Phase 0)

Parse RealTest `.rts` strategies into a **deep criteria graph**, emit an **export
plan** for RealTest bar-series output, and **check** fixture (or exported) CSV
against trades.

## Commands

```bash
# Export plan + companion RTS snippets (results + scan variants)
python -m criteria_viz plan example_strategy.rts -o export_plan.json

# Validate series CSV against trades (fixtures for CI)
python -m criteria_viz check \
  --rts tests/fixtures/criteria_viz/mean_reversion.rts \
  --trades tests/fixtures/criteria_viz/trades.csv \
  --series tests/fixtures/criteria_viz/series
```

## Layout

```
criteria_viz/
  graph/       # Lark → deep CriteriaGraph
  export/      # ExportPlan, CSV store, companion snippets
  trades/      # Trade CSV loader + date alignment
  timeline/    # Project graph values onto bar windows
  docs/        # Windows RealTest export experiments
```

See `docs/architecture/trade-criteria-visualizer.md` for full design.
