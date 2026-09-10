# Trade Criteria Visualizer — Design Package (Candidate C: Snapshot Bundle)

**Status:** Architecture candidate  
**Repo context:** rt-grammar — Lark syntax validator for RealTest `.rts` scripts. No AST, evaluator, or web app today.  
**Design stance:** Immutable `SessionBundle` built once at CLI startup; all API reads are projections. No mutable server state. Functional core.

---

## Problem

RealTest strategies express trade decisions as **compound boolean formulas** spread across many strategy elements (`EntrySetup`, `EntrySkip`, `SetupSkip`, `ExitRule`, `ExitLimit`, `ExitStop`, …). A single trade is the convergence of those expressions over a bar window — setup phase, entry phase, hold, exit triggers — often with `Compounded: True` semantics that chain prior criterion state.

Today rt-grammar answers only: *“Is this script syntactically valid?”* It does not help answer:

1. **Which sub-criteria were true on each bar** for a specific trade?
2. **When did the entry/exit convergence occur** relative to indicator values and skips?
3. **Which formula branch blocked or allowed** the trade at a given bar?

Without a per-trade timeline of criterion truth values, debugging “why did this trade happen (or not)?” requires running RealTest externally and mentally mapping static script text to bar history — slow, error-prone, and opaque for compound logic.

**Goal:** A local visualizer (CLI + read-only HTTP API) that, for each trade in a trade list, exposes a **bar-aligned timeline** of entry/exit criterion convergence — built from parsed RTS + trade list + bar data.

---

## Usage First

### CLI (primary entry)

```bash
# Build bundle once at startup, serve read-only API until Ctrl+C
python -m criteria_viz serve \
  --rts example_strategy.rts \
  --trades tests/valid/stub_trades.csv \
  --bars tests/valid/stub_values.csv \
  --port 8765
```

Expected startup log (sketch):

```
[criteria_viz] building session bundle …
[criteria_viz]   rts: example_strategy.rts (1 strategy: MeanReversion)
[criteria_viz]   trades: 1 row → 1 trade key
[criteria_viz]   bars: SPY Daily 2020-01-01..2020-01-31 (21 bars)
[criteria_viz]   precomputed timelines: 1 trade × 21 bars × 4 criteria
[criteria_viz] session fingerprint: sha256:abc123…
[criteria_viz] serving read-only API at http://127.0.0.1:8765
```

### HTTP (projections only — no mutation endpoints)

```http
GET /health
GET /session/meta
GET /trades
GET /trades/{trade_id}/timeline
GET /strategies/{strategy_name}/criteria
```

Example timeline slice:

```json
{
  "trade_id": "playback:SPY:2020-01-02:Buy",
  "symbol": "SPY",
  "strategy": "playback",
  "entry_date": "2020-01-02",
  "bars": [
    {
      "date": "2020-01-02",
      "phase": "entry",
      "criteria": {
        "entry_setup": {"expr": "C > MA(C, 200) and RSI(2) < 10", "value": true, "parts": {"C > MA(C, 200)": true, "RSI(2) < 10": true}},
        "entry_skip": {"expr": "IsNaN(ATR(20))", "value": false},
        "exit_rule": {"expr": "BarsHeld >= 10", "value": false}
      }
    }
  ]
}
```

### Programmatic (small public API)

```python
from criteria_viz import build_session, serve, get_trade_timeline

session = build_session(
    rts_path="example_strategy.rts",
    trades_path="tests/valid/stub_trades.csv",
    bars_path="tests/valid/stub_values.csv",
)

timeline = get_trade_timeline(session, trade_id="playback:SPY:2020-01-02:Buy")
assert timeline.bars[-1].criteria["entry_setup"].value is True

serve(session, host="127.0.0.1", port=8765)  # blocks; bundle never mutated
```

**Contract:** `build_session()` is **idempotent** — same inputs (paths + optional parameter overrides) → byte-identical bundle fingerprint. `serve()` and `get_trade_timeline()` are **read-only projections**; they never re-parse RTS, reload CSVs, or re-evaluate formulas.

---

## Shape

### Architecture diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI startup (once)                                             │
│                                                                 │
│  build_session(rts, trades, bars)  ──►  SessionBundle (frozen)   │
│         │                                    │                  │
│         ├─ parse RTS (Lark)                  ├─ meta/fingerprint│
│         ├─ extract strategy criteria         ├─ trades index    │
│         ├─ load trade list                   ├─ bars by symbol  │
│         ├─ load bar CSV/RTD slice            └─ timelines[*]    │
│         └─ evaluate criteria × bars (eager)       (precomputed) │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
     get_trade_timeline(session, id)   serve(session) → FastAPI
              │                               │
              └─ pure projection ──────────────┘
                    (no I/O, no mutation)
```

### Module layout (`criteria_viz/`)

| Module | Responsibility |
|--------|----------------|
| `__init__.py` | Public API: `build_session`, `serve`, `get_trade_timeline` |
| `models.py` | Frozen dataclasses: `SessionBundle`, `TradeTimeline`, `CriterionSnapshot` |
| `bundle.py` | `build_session()` orchestration; fingerprinting |
| `loaders.py` | RTS parse, trade CSV, bar CSV → normalized inputs |
| `extract.py` | Walk Lark tree → per-strategy criterion expressions (text + refs) |
| `evaluate.py` | Minimal boolean formula evaluator over bar columns (Phase 0 scope) |
| `projections.py` | `get_trade_timeline`, list trades, strategy criteria metadata |
| `serve.py` | Read-only FastAPI app factory; injects frozen bundle |
| `cli.py` | `python -m criteria_viz serve …` |

### Core types (sketch)

```python
@dataclass(frozen=True)
class SessionBundle:
    fingerprint: str
    rts_path: Path
    strategies: Mapping[str, StrategyCriteria]
    trades: tuple[TradeRecord, ...]
    bars: Mapping[str, BarSeries]           # symbol → OHLCV+date index
    timelines: Mapping[str, TradeTimeline]  # trade_id → precomputed projection
```

**Key invariant:** `timelines` is populated entirely inside `build_session()`. HTTP handlers and `get_trade_timeline()` only index into `session.timelines` (or derive views from it without recomputation).

### Idempotent `build_session()`

```python
def build_session(*, rts_path, trades_path, bars_path, params=None) -> SessionBundle:
    inputs = _normalize_inputs(...)           # resolve paths, stable sort keys
    fingerprint = _hash_inputs(inputs)        # sha256 of file bytes + params JSON
    parsed = _parse_rts(inputs.rts_path)      # Lark — same as validate_rts
    criteria = extract_strategy_criteria(parsed)
    trades = load_trades(inputs.trades_path)
    bars = load_bars(inputs.bars_path)
    timelines = {
        trade.trade_id: _compute_timeline(trade, criteria[trade.strategy], bars)
        for trade in trades
    }
    return SessionBundle(fingerprint=fingerprint, ..., timelines=frozen_map(timelines))
```

Properties:

- **Pure relative to inputs:** no globals, no caches keyed by wall clock, no environment except explicit `params`.
- **Deterministic trade IDs:** `{strategy}:{symbol}:{date}:{action}` with normalized dates.
- **Eager evaluation:** CPU cost paid once; API latency is O(window) dict lookup, not O(bars × formulas).

### Read-only FastAPI

```python
def create_app(session: SessionBundle) -> FastAPI:
    app = FastAPI(title="criteria_viz", docs_url="/docs")

    @app.get("/trades/{trade_id}/timeline")
    def timeline(trade_id: str) -> TradeTimelineDTO:
        return get_trade_timeline(session, trade_id).to_dict()

    return app

def serve(session: SessionBundle, host="127.0.0.1", port=8765) -> None:
    uvicorn.run(create_app(session), host=host, port=port)
```

No `POST`, `PUT`, or session store. Changing inputs requires restart with a new `build_session()` call.

### Criterion convergence model (Phase 0)

For each bar in `[setup_window_start .. exit_window_end]` around a trade:

| Phase | Criteria evaluated |
|-------|-------------------|
| `setup` | `EntrySetup`, `SetupSkip`, `SetupScore` (boolean only) |
| `entry` | above + `EntrySkip`, compounded gate if enabled |
| `hold` | `ExitRule`, `ExitLimit`/`ExitStop` trigger expressions (as booleans) |
| `exit` | exit criteria at exit bar |

Each criterion snapshot records:

- `expr` — source text from RTS
- `value` — bool (or numeric for scores, Phase 1)
- `parts` — optional map of decomposed sub-expression → bool (for `and`/`or` trees)

---

## Tradeoffs

### What Candidate C buys

| Benefit | Mechanism |
|---------|-----------|
| **Predictable latency** | Timelines precomputed; API is lookup |
| **Simple mental model** | One bundle = one snapshot of reality; no cache invalidation |
| **Easy testing** | `build_session` → assert on `get_trade_timeline`; golden fingerprints |
| **Safe concurrency** | Frozen bundle is shareable across threads/workers without locks |
| **Reproducible bugs** | Fingerprint ties bug reports to exact input bytes |

### What Candidate C costs

| Cost | Mitigation |
|------|------------|
| **Startup time** | Acceptable for dev/CLI; show progress + fingerprint |
| **Memory** | Store only trade windows, not full history × all symbols |
| **Stale data** | Document: restart to refresh; no live reload in v1 |
| **Parameter sweeps** | Each param vector = new bundle (see Open Questions) |

### Explicit non-goals (v1)

- Full RealTest formula semantics (breadth ops, portfolio functions, walk-forward)
- Editing RTS or trades through the API
- Streaming live market data
- AST export from rt-grammar (reuse Lark tree internally only)

---

## Alternatives

### Candidate A — Stream / recompute on read

Each `GET /timeline` re-loads bars, re-parses formulas, re-evaluates for the requested trade window.

- ✅ Lower memory; always “fresh” if files change on disk.
- ❌ Hot path does I/O + parse + eval; harder to test; race if files mutate mid-request.
- ❌ Invites mutable file-watch state in the server.

**Why not chosen:** Optimizes for freshness over clarity; conflicts with “functional core” and reproducible debugging.

### Candidate B — Mutable session with LRU cache

Server holds paths; cache `(trade_id, file mtime)` → timeline; invalidates on mtime change.

- ✅ Faster startup than full eager build.
- ❌ Cache invalidation complexity; non-deterministic across runs if files change.
- ❌ Hidden state between requests.

**Why not chosen:** Same user value as C for debugging, but strictly more complex operationally.

### Candidate D — Delegate evaluation to RealTest.exe

Shell out to RealTest for bar-level criterion output; visualizer is a thin viewer.

- ✅ Perfect semantic fidelity.
- ❌ Requires RealTest install; opaque batch logs; hard to decompose sub-expressions.
- ❌ Not portable to CI / Linux cloud agents.

**Why not chosen:** rt-grammar’s value is standalone Python; keep Phase 0 self-contained with stub CSV bars, optional RealTest bridge later.

### Candidate C vs A (summary)

| Dimension | C: Snapshot Bundle | A: Stream / recompute |
|-----------|-------------------|----------------------|
| Startup | Slower (eager) | Fast |
| Request | O(1) lookup | O(bars × eval) |
| Correctness testing | Golden fingerprint | Need to mock I/O each test |
| File change | Restart | Ambiguous mid-flight |
| Server state | None | Implicit (file handles, parsers) |

---

## Open Questions

1. **Evaluator scope:** Phase 0 covers boolean `EntrySetup` / `ExitRule` with Data-section refs and OHLCV columns from stub CSV. Which RealTest builtins must land in Phase 1 (`BarsHeld`, `IsSetup`, `Compounded` chaining)?

2. **Bar data source:** Stub CSV (`stub_values.csv`) vs `.rtd` binary vs on-the-fly Yahoo import — bundle builder should accept pluggable `BarSource`, but which is v1 default?

3. **Trade window sizing:** How many bars before entry / after exit to include? Fixed (e.g. 20/20), or strategy-derived (max indicator lookback from extracted refs)?

4. **Sub-expression decomposition:** Full parse tree for `and`/`or` vs top-level only — affects UI complexity and eval cost at build time.

5. **Multi-strategy scripts:** `StatsGroup` / `Combined` — visualize per underlying strategy trade only, or expose combined sleeve context?

6. **Parameter overrides:** `build_session(..., params={"RSIPeriod": 3})` — include in fingerprint; require full re-build. Acceptable for CLI?

7. **Frontend:** API-only v1, or ship minimal static timeline chart (HTMX/Chart.js) in `criteria_viz/static/`?

8. **Relationship to rt-grammar:** New optional deps (`fastapi`, `uvicorn`) in `requirements-viz.txt` or extras `pip install rt-grammar[viz]`?

---

## Next Step

**Phase 0 spike (1–2 focused PRs):**

1. ✅ Land `criteria_viz/` sketches + this design doc.
2. Implement `extract.py` — pull `EntrySetup`, `EntrySkip`, `ExitRule` text from Lark tree for one strategy (reuse `validate_rts.load_grammar`).
3. Implement `loaders.py` — parse `stub_trades.csv` + `stub_values.csv` from `tests/valid/`.
4. Implement minimal `evaluate.py` — support `and`/`or`/`not`, comparisons, `RSI()`/`MA()` over CSV columns, named Data items as column aliases.
5. Wire `build_session()` → precompute one timeline for `stub_trades.csv` / `playback` strategy.
6. Add `tests/test_bundle_determinism.py` — two builds → same `fingerprint`; `get_trade_timeline` golden JSON.
7. Optional: `serve()` + manual curl check; defer UI.

**Success criteria for Phase 0:** Given the existing test stubs, `get_trade_timeline(session, trade_id)` returns a bar-aligned JSON document with entry/exit criterion booleans, and repeated `build_session()` calls produce identical fingerprints.

---

## Appendix: Dependency sketch

```
# requirements-viz.txt (optional extra)
fastapi>=0.110
uvicorn[standard]>=0.27
```

Entry point registration (future):

```toml
[project.optional-dependencies]
viz = ["fastapi>=0.110", "uvicorn[standard]>=0.27"]
```
