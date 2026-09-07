# RealTest export experiments (Windows)

Phase 0 assumes per-bar criteria values can be exported from RealTest. The exact
mechanism is validated on a Windows machine with RealTest installed.

## Goal

For `tests/fixtures/criteria_viz/mean_reversion.rts`, produce per-symbol CSV with
columns matching `python -m criteria_viz plan` output (see `export_plan.json` and
`companion_snippets/`).

Minimum columns at signal bar for trade `SPY` on `2020-01-02`:

- `Date`, `RSIV`, `Oversold`, `AboveTrend`, `EntrySetup`, `ExitRule`
- Plus deep `cv_*` columns if Results/Scan can materialize anonymous sub-expressions

## Experiment A — Results (preferred)

1. Run `python -m criteria_viz plan tests/fixtures/criteria_viz/mean_reversion.rts -o export_plan.json`
2. Open `companion_snippets/MeanReversion_results.rts`
3. Wrap or inject into a backtest script that includes the strategy
4. Run RealTest; capture per-bar output to `series_export/SPY.csv`
5. Record: settings used (`ResultsFile`, etc.), column headers, date format

## Experiment B — Scan (fallback)

1. Use `companion_snippets/MeanReversion_scan.rts`
2. Ensure `SaveScanAs:` points at `criteria_viz_scan.csv`
3. Run scan across the trade date range for held symbols
4. Normalize output to per-symbol files under `series_export/`

## Validate

```bash
python -m criteria_viz check \
  --rts tests/fixtures/criteria_viz/mean_reversion.rts \
  --trades tests/fixtures/criteria_viz/trades.csv \
  --series path/to/series_export
```

Exit code 0 means export columns align with the deep graph.

## Notes

- `Results:` in grammar fixtures shows **aggregate** strategy stats; your wrapped
  workflow may use Results differently — document what RealTest actually emits.
- `Scan:` is the documented per-symbol formula column mechanism (`SaveScanAs`).
- Linux CI uses hand-crafted `tests/fixtures/criteria_viz/series/` until experiments land.
