# RealTest export experiments (Windows)

Phase 0 assumes per-bar criteria values can be exported from RealTest. The exact
mechanism is validated on a Windows machine with RealTest installed.

## Goal

Produce per-symbol CSV with columns matching `python -m criteria_viz plan` output
(see `export_plan.json` and `companion_snippets/`).

## Important: Include the original strategy first

RealTest export scripts **must** load the source strategy before the export
section. `plan` generates runnable scripts in this shape:

```rts
Include:
    ?scriptpath?/YourStrategy.rts

Results:
    EntrySetup:    {//}    ...
    ...
```

Run the generated `*_results.rts` or `*_scan.rts` directly in RealTest — do not
strip the `Include:` block.

If the strategy lives in a different folder from the export script, re-run
`plan` with `-o` under `companion_snippets/` or edit the `Include:` path.

## Experiment A — Results (preferred)

1. `python -m criteria_viz plan path/to/strategy.rts -o export_plan.json`
2. Run RealTest on `companion_snippets/{Strategy}_results.rts`
3. Capture per-bar output → `series_export/{SYMBOL}.csv`
4. Record: settings (`ResultsFile`, etc.), column headers, date format

## Experiment B — Scan (fallback)

1. Run RealTest on `companion_snippets/{Strategy}_scan.rts`
2. `SaveScanAs:` writes `criteria_viz_scan.csv` beside the script
3. Split/normalize to per-symbol files under `series_export/`

## Validate

```powershell
python -m criteria_viz check `
  --rts path/to/strategy.rts `
  --trades path/to/trades.csv `
  --series path/to/series_export `
  --strategy StrategyName
```

Exit code 0 means export columns align with the deep graph.

## Notes

- `Results:` in grammar fixtures shows aggregate strategy stats; your wrapped
  workflow may emit per-bar columns — document what RealTest actually outputs.
- Linux CI uses hand-crafted `tests/fixtures/criteria_viz/series/` until
  experiments land.
