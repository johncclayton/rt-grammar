# Trade criteria visualizer — architecture (synthesized)

**Status:** Phase C checkpoint — awaiting decisions before implementation  
**Repo:** rt-grammar (Lark `.rts` validator)  
**Workflow:** `/architect` — Ground → Sketch (arena) → **Agree** → Implement

---

## Phase A: Grounding (existing system)

### What rt-grammar is today

rt-grammar is a **syntax validator** for RealTest Script Language (`.rts`). It is not a strategy runtime.

| Component | Path | Role |
|-----------|------|------|
| Grammar | `realtest.lark` | LALR(1) + contextual lexer; ~655 lines; RealTest 2.0.32.7 aligned |
| Validator CLI | `validate_rts.py` | `load_grammar()`, `validate_file()`; optional `RealTest.exe -parse` cross-check |
| Fixtures | `tests/valid/*.rts`, `tests/invalid/*.rts` | Regression corpus |
| Example | `example_strategy.rts` | Minimal mean-reversion strategy |

**Parser configuration (required):**

```python
Lark(grammar, start="start", parser="lalr", lexer="contextual",
     propagate_positions=False, maybe_placeholders=False, cache=True)
```

### Relevant RTS structure for this feature

**`Data:` section** — named formula items that compose indicators and booleans:

```rts
Data:
    RSIV: RSI(RSIPeriod)
    Oversold: RSIV < RSIThreshold
```

**`Strategy:` section** — entry/exit criteria as formula-valued keywords:

| Role | Keywords (v1 priority) |
|------|------------------------|
| Entry | `EntrySetup`, `EntrySkip`, `EntryLimit`, `EntryStop`, `EntryScore` |
| Exit | `ExitRule`, `ExitLimit`, `ExitStop`, `ExitScore` |
| Timing | `EntryTime`, `ExitTime` (enums — affect bar alignment) |
| Inheritance | `Using:` → `Template:` merge required |

**Trade list playback** — `TradeList:` + `TLFields:` + CSV (`tests/valid/stub_trades.csv`).

**`Trades:` report section** — output column definitions only; not execution.

### What does not exist (gaps)

- No Lark `Transformer` / AST / semantic model
- No formula evaluator
- No trade or bar data loaders
- No web stack

### Constraints the design must honor

1. **Grammar stays source of truth** — reuse `realtest.lark`; do not fork syntax.
2. **Validator stays minimal** — core package remains `lark`-only; viz is an optional extra (`requirements-viz.txt` or `[viz]` extra).
3. **RealTest semantics are hard** — offsets, breadth (`#Rank`), `S.*`/`T.*`, `Compounded`, ambiguity rules. Re-implementing RealTest in Python is a multi-month project.
4. **Linux CI** — cannot depend on `RealTest.exe` for tests.

---

## Problem

RealTest strategies decide trades through **compound formulas** evaluated bar-by-bar. When a trade fires, it is difficult to see:

- Which **sub-conditions** were true/false on each preceding bar
- How **leaf indicators** moved until the compound criterion converged
- Whether exit fired from `ExitRule`, a stop, or a limit

The primary goal is **visualizing convergence**: how compound entry and exit criteria evolved over time until they produced a signal — not replacing RealTest or building a full backtester.

**v1 scope:**

- CLI specifies `.rts` file + trades CSV (+ bar series export)
- Python backend parses criteria structure, aligns trades to bars, serves JSON
- Simple web UI: strategy picker (left), trade table (center), criteria timeline (detail)

**v1 non-goals:**

- Full RealTest formula evaluation in Python
- Live reload / RTS editing via API
- Walk-forward parameter sweeps
- Portfolio-level `S.*` / `Combined` / `StatsGroup` semantics

---

## Usage (caller's view)

*Written first — types derive from this.*

### README quickstart (target)

```bash
# Step 1: discover what RealTest must export for your strategy
python -m criteria_viz plan example_strategy.rts -o export_plan.yaml

# Step 2: run RealTest with generated companion snippet → series_export/*.csv
#         (external; documented workflow)

# Step 3: visualize
python -m criteria_viz serve \
  --rts example_strategy.rts \
  --trades trades.csv \
  --series ./series_export \
  --strategy MeanReversion \
  --port 8765
```

### Call site 1 — CLI operator

```bash
python -m criteria_viz serve \
  --rts path/to/strategy.rts \
  --trades path/to/trades.csv \
  --series path/to/series_export/ \
  --strategy MeanReversion
```

### Call site 2 — library / notebook

```python
from pathlib import Path
from criteria_viz import open_session, TradePhase

session = open_session(
    rts_path=Path("example_strategy.rts"),
    trades_csv=Path("trades.csv"),
    series_dir=Path("series_export"),
    strategy="MeanReversion",
)

view = session.criteria_view(trade_index=0, phase=TradePhase.ENTRY)
for snap in view.timeline:
    print(snap.date, snap.values["Oversold"], snap.values["EntrySetup"])
```

### Call site 3 — CI smoke (no RealTest)

```python
session = open_session(
    rts_path=Path("tests/fixtures/mean_reversion.rts"),
    trades_csv=Path("tests/fixtures/trades.csv"),
    series_dir=Path("tests/fixtures/series_export"),
)
view = session.criteria_view(0, TradePhase.ENTRY)
assert view.signal_bar.values["EntrySetup"] is True
```

### Public API (small surface)

| Symbol | Role |
|--------|------|
| `open_session(...)` | Build immutable session from paths |
| `run_server(session, ...)` | Read-only HTTP + static UI |
| `TradePhase` | `ENTRY` / `EXIT` |
| `CriteriaView` | Graph layout + bar timeline for one trade+phase |
| `ExportPlan` | Output of `plan` subcommand |
| `CriteriaVizError` | Boundary failures |

Parsing, Lark trees, CSV wire formats, and HTTP DTOs stay **private**.

---

## Shape (synthesized architecture)

### Synthesis decision

**Base: Candidate B (Criteria Graph Center)** — `CriteriaGraph` is the load-bearing domain type. Compound `and`/`or`/`not` structure drives UI layout and dependency ordering.

**Grafted from Candidate A (Export-first):**

- `BarSeries` reads **pre-exported CSV columns** from RealTest; Python does **not** evaluate formulas in v1.
- `ExportPlan` + `plan` CLI document the RealTest export contract.
- `evaluate` step becomes **column lookup** keyed by `series_key` on each graph node.

**Grafted from Candidate C (Snapshot Bundle):**

- `open_session()` builds one **immutable `Session`** at startup (graph + trades + series index).
- FastAPI handlers are **read-only projections** — no mutation, no file watch.
- **Rejected from C:** eager precompute of all trade timelines. Timelines are built **lazily** on first `criteria_view()` and cached inside the frozen session (amortizes cost without slow startup).

**Rejected: Python formula evaluator (Candidate B's optional path)** — deferred to v2+; export-first avoids semantic drift from RealTest.

### Architecture diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  open_session() — once at CLI startup                                   │
│                                                                         │
│  parse .rts ──► CriteriaGraph + ExportPlan                              │
│  load trades ──► TradeRecord[]                                          │
│  load series ──► BarSeriesStore (per-symbol CSV, validated columns)     │
│                                                                         │
│  Session (frozen): graph, trades, series, timeline_cache: dict          │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │  criteria_view(trade, phase)  [lazy, cached]
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. Resolve trade → symbol, strategy, signal date (DateIn / DateOut)    │
│  2. Pick graph root: EntrySetup | ExitRule for (strategy, phase)        │
│  3. Slice bar window: [signal - warmup .. signal + padding]             │
│  4. For each bar: copy exported values into node ids (no formula eval)  │
│  5. Compute `changed` diff vs previous bar (for convergence animation)  │
│  6. Return CriteriaView (pruned subgraph + timeline)                    │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
   run_server(session) → GET /api/strategies, /api/trades, /api/view
```

### Core types

```python
# --- Graph (structure; values from export) ---

@dataclass(frozen=True)
class CriterionNode:
    id: str
    label: str
    kind: Literal["data_ref", "strategy_root", "and", "or", "not", "cmp", "call", "literal"]
    series_key: str | None      # CSV column; every displayable node has one in v1
    expr_source: str            # RTS text for tooltips
    deps: tuple[str, ...]       # child node ids

@dataclass(frozen=True)
class CriteriaGraph:
    nodes: Mapping[str, CriterionNode]
    roots: Mapping[tuple[str, TradePhase], str]   # (strategy_name, phase) → node id
    strategies: tuple[str, ...]

# --- Bar data (export backend) ---

class BarSeriesStore(Protocol):
    def dates(self, symbol: str) -> tuple[date, ...]: ...
    def value(self, symbol: str, series_key: str, bar_index: int) -> float | bool | None: ...
    def has_columns(self, symbol: str, keys: frozenset[str]) -> bool: ...

# --- View (per trade + phase) ---

@dataclass(frozen=True)
class BarSnapshot:
    bar_index: int
    date: date
    values: Mapping[str, float | bool | None]   # node id → exported value
    changed: frozenset[str]                     # node ids that changed vs prior bar

@dataclass(frozen=True)
class CriteriaView:
    trade: TradeRecord
    phase: TradePhase
    root_id: str
    graph: CriteriaGraph          # pruned to nodes reachable from root
    timeline: tuple[BarSnapshot, ...]
    signal_bar_index: int
    root_satisfied: bool

# --- Export contract ---

@dataclass(frozen=True)
class SeriesSpec:
    key: str                      # stable CSV column name
    origin: str                   # "data:Oversold" | "strategy:EntrySetup"
    rts_ref: str

@dataclass(frozen=True)
class ExportPlan:
    strategies: Mapping[str, tuple[SeriesSpec, ...]]
    companion_rts_snippet: str  # paste into script for RealTest to materialize columns

# --- Session ---

class Session(Protocol):
    def strategies(self) -> tuple[str, ...]: ...
    def trades(self, strategy: str | None = None, sort: str = "date_in") -> tuple[TradeRecord, ...]: ...
    def criteria_view(self, trade_index: int, phase: TradePhase, *, warmup: int = 20) -> CriteriaView: ...
    def export_plan(self) -> ExportPlan: ...
```

### Module map

```
criteria_viz/
├── __init__.py              # open_session, run_server, CriteriaView, TradePhase, ExportPlan
├── errors.py
├── cli.py                   # plan | serve | check
│
├── graph/
│   ├── model.py             # CriteriaGraph, CriterionNode
│   ├── build.py             # Lark tree → graph (internal)
│   └── inherit.py           # Template / Using: flatten
│
├── export/
│   ├── plan.py              # graph → ExportPlan + companion RTS snippet
│   └── store.py             # CsvBarSeriesStore, MockBarSeriesStore (tests)
│
├── trades/
│   ├── load.py              # CSV → TradeRecord
│   └── align.py             # trade date → bar index in series
│
├── timeline/
│   └── project.py           # Session.criteria_view implementation
│
├── session.py               # open_session(), frozen Session impl
├── server.py                # read-only HTTP + static/
└── _wire.py                 # JSON DTOs (never exported)
```

**Red-flag screen:**

| Flag | Mitigation |
|------|------------|
| Shallow modules | `graph/build`, `export/plan`, `timeline/project` each own real logic |
| Temporal decomposition | No separate load/validate/transform/save pipeline packages |
| Pass-through methods | `Session` orchestrates; submodules are internal |
| Wire types on public API | HTTP JSON only in `_wire.py` |
| Info leakage | Lark `Tree` never leaves `graph/build.py` |

### Web UI (v1)

| Panel | Content |
|-------|---------|
| Left | Strategy names from `session.strategies()` |
| Center | Trade table for selected strategy; sort by DateIn / DateOut |
| Detail (row click) | Entry \| Exit tabs; bar scrubber; criteria tree colored by value at current bar; highlight signal bar |

### Export CSV contract (v1)

Per symbol: `{series_dir}/{SYMBOL}.csv`

| Column | Required |
|--------|----------|
| `Date` | yes |
| `{series_key}` | one per node in ExportPlan |

Optional: `export_manifest.yaml` for date format, file mapping, and `backend: results | scan`.

RealTest produces values via **companion snippet** from `plan`. Two snippet variants (Results-first, Scan-fallback); Python never recomputes formulas. Final variant chosen after Windows experiments.

---

## Tradeoffs accepted

| Tradeoff | Why |
|----------|-----|
| Two-step workflow (`plan` → RealTest export → `serve`) | Correctness matches backtest; no formula engine in v1 |
| Lazy timeline cache vs eager bundle | Faster startup than Candidate C; same read-only API guarantees |
| Graph structure + exported values | Graph for UI/deps; values from RealTest only — no hybrid eval |
| v1 roots: `EntrySetup` + `ExitRule` only | Limits/stops/skips in Phase 1; graph model already supports more roots |
| Trade CSV dates are authoritative for signal bar | `EntryTime: NextOpen` alignment documented; may need ±1 bar offset flag |
| Synthetic `series_key` for anonymous sub-exprs | e.g. `EntrySetup: RSI(2)<10 and C>MA(C,200)` without `Data:` aliases — companion snippet materializes them |
| Optional deps (`fastapi`, `uvicorn`) | Keeps validator install lean |

---

## Alternatives considered

### A — Export-first flat pipeline (partially merged)

`VizSession` + `CriteriaTree` + `ExportPlan` without a persistent graph type. **Why not sole choice:** flat trees don't share sub-expressions across trades/phases cleanly; graph layout and `changed` diff are awkward.

### B — Criteria Graph + Python evaluator (partially merged)

Graph + `evaluate_graph()` computing formulas from OHLCV. **Why deferred:** duplicates RealTest; export lookup replaces eval in v1. `BarSeriesStore` protocol preserves evaluator path for v2.

### C — Eager snapshot bundle (partially merged)

Precompute all timelines at startup. **Why rejected for eager:** slow startup and high memory with large trade lists. **Kept:** immutable session + read-only API.

### D — RealTest.exe delegate

Shell out for bar-level output. **Why rejected:** not portable to Linux CI; opaque; hard to decompose compound criteria for UI.

---

## Decisions recorded

| # | Decision | Status |
|---|----------|--------|
| **Q1** | Per-bar values come from **RealTest export** (wrapped/injected RTS). Mechanism: **`Results:` preferred**, **`Scan:` + `SaveScanAs` fallback**. Exact workflow TBD on Windows experiments. | **Locked (assumed feasible)** |
| **Q2** | v1 strategy keywords: `EntrySetup` + `ExitRule` only; more elements later | **Locked** |
| **Q6** | **Deep decomposition** — full `and`/`or`/`not`/comparison tree in the graph model and export plan | **Locked** |
| **Q6 display** | How much of the tree is shown initially (collapse, focus mode, defaults) | **Separate concern** — UI phasing, not model depth |

### Q1 — export backend (pluggable, experiments later)

Python treats bar data as **opaque CSV** keyed by `series_key`. How RealTest produces that CSV is behind an export-backend boundary:

| Backend | When | `plan` output |
|---------|------|----------------|
| **`results`** (preferred) | Inject/wrap RTS with a `Results:` (or related) section that emits per-bar formula columns | Companion snippet variant A |
| **`scan`** (fallback) | `Scan:` columns mirror `ExportPlan` + `SaveScanAs:` in `Settings` | Companion snippet variant B |
| **`fixture`** | Dev/CI on Linux without RealTest | Hand-crafted CSV under `tests/fixtures/` |

**Phase 0 does not block on Windows.** Implement graph + `plan` + `CsvBarSeriesStore` against fixtures; companion snippets ship as **both** variants with a `backend: results | scan` flag. Lock the default once experiments confirm which path works.

**Experiment checklist (Windows):** for `example_strategy.rts`, can export columns `Date`, `RSIV`, `Oversold`, `AboveTrend`, `EntrySetup` per symbol per bar? Record: section used, `Save*As` setting, file layout (one file vs per-symbol), date format.

### Model depth vs display depth (Q6)

These are intentionally decoupled:

| Layer | Requirement |
|-------|-------------|
| **Graph model** | Always **deep** — every compound operator and comparison is a `CriterionNode` with a stable `series_key` |
| **Export plan** | Lists **all** nodes (named `Data:` items + synthetic keys for anonymous sub-expressions) |
| **API** | Returns the **full** pruned subgraph for a trade+phase; clients choose what to render |
| **UI (phased)** | May default to collapsed tree (root + named refs visible; anonymous `and`/`cmp` nodes expandable) without omitting data |

Example — inline entry `RSIV < RSIThreshold and C > MA50`:

```
EntrySetup (and)           series_key: strategy:MeanReversion:EntrySetup
├── cmp_0 (RSIV < RSIThreshold)   series_key: cv:MeanReversion:EntrySetup:cmp:0
│   ├── RSIV                      series_key: data:RSIV
│   └── RSIThreshold              series_key: param:RSIThreshold
└── cmp_1 (C > MA50)              series_key: cv:MeanReversion:EntrySetup:cmp:1
    ├── C                         series_key: builtin:C
    └── MA50                      series_key: data:MA50
```

The visualizer **always knows** this tree exists; the first UI might only highlight `EntrySetup` + `Oversold`/`AboveTrend` when those are named `Data:` aliases — but nothing prevents drilling into `cmp_0` immediately once export columns exist.

---

## Open questions — decisions needed

Please answer these before implementation starts. Each blocks or shapes a slice.

### Q1 — Bar data source

**Resolved:** Assume RealTest can export per-bar series. Preferred path: injected/wrapped **`Results:`**; fallback: **`Scan:`** + `SaveScanAs`. Dev/CI uses fixture CSV until Windows experiments lock the companion-snippet shape.

### Q2 — Entry/exit scope

**Resolved:** v1 roots are `EntrySetup` and `ExitRule` only. Additional strategy elements (`EntrySkip`, stops, limits, …) are follow-on work; the graph model already supports extra roots.

### Q3 — Trade list source

| Source | CSV shape |
|--------|-----------|
| Backtest `SaveTradesAs` Compact/Full | RealTest export columns |
| `TradeList` playback | `stub_trades.csv` style |
| Both | Auto-detect headers |

**Question:** Which trade CSV formats must v1 support?

### Q4 — Signal bar definition

Trade CSV `DateIn`/`DateOut` vs formula truth on prior bars (`EntryTime: NextOpen`).

**Question:** Should the signal bar be (a) the trade CSV date exactly, (b) first bar where root criterion became true before that date, or (c) configurable offset?

### Q5 — Time window

Bars shown before entry / after exit:

| Option | Behavior |
|--------|----------|
| Fixed | e.g. 20 bars before, 5 after (CLI flags) |
| Derived | max lookback from indicator refs in graph |
| Both | derived default, fixed override |

**Question:** Preference?

### Q6 — Sub-expression decomposition depth

**Resolved:** Deep model always. Display phasing is a UI-only concern (see [Decisions recorded](#decisions-recorded)).

### Q7 — Template inheritance

Strategies with `Using: base` (see `strategy_elements.rts`).

**Question:** Must v1 resolve `Template:` merge, or only single/self-contained strategies initially?

### Q8 — Packaging

**Question:** `requirements-viz.txt` in repo root vs `pip install rt-grammar[viz]` optional extra?

### Q9 — Frontend in v1

| Option | Scope |
|--------|-------|
| API + `check` CLI only | Fastest proof |
| API + minimal static UI | Matches original request |

**Question:** Ship static UI in first PR or second?

---

## Phased delivery

### Phase 0 — Spike (parser + export plan + fixture CSV)

**Unblocked** — Q1 assumed feasible; no RealTest required for this phase.

- [ ] `graph/build.py`: parse `example_strategy.rts` → deep `CriteriaGraph` for `EntrySetup`/`ExitRule`
- [ ] `export/plan.py`: emit `ExportPlan` + companion snippets (**results** and **scan** variants)
- [ ] `export/store.py`: load hand-crafted fixture CSV matching `ExportPlan` keys
- [ ] `cli plan` and `cli check`: validate graph + fixture alignment
- [ ] No web UI

**Exit:** `python -m criteria_viz check --rts example_strategy.rts --trades ... --series ...` exits 0 on Linux CI.

**Parallel (Windows):** run experiments; update `plan` default backend + document winning snippet in `criteria_viz/docs/realtest-export.md`.

### Phase 1 — MVP (your stated v1)

- [ ] `open_session` + lazy `criteria_view`
- [ ] `serve` + static UI (strategy panel, trade table, timeline)
- [ ] `Template:` merge if Q7 requires it
- [ ] Fixture tests in CI (no RealTest.exe)

### Phase 2 — Hardening

- [ ] Secondary entry/exit fields (`EntrySkip`, stops/limits)
- [ ] Documented RealTest export workflow + sample script
- [ ] Trade CSV auto-detect (Compact vs playback)

### Phase 3 — Optional evaluator path

- [ ] `EvaluatorBarSeriesStore` for common functions over OHLCV only
- [ ] Clearly labeled "approximate" in UI when not using export

---

## Next implementation step

**Phase 0 is unblocked.** Start with:

> `graph/build.py` + `export/plan.py` (deep tree, dual snippet variants) + fixture CSV + `cli check` for `example_strategy.rts`.

Windows experiments refine which snippet variant becomes default; they do not block the parser or fixture-based timeline path.

---

## Appendix: arena candidates

Exploration artifacts on branch `cursor/trade-criteria-viz-design-03d8`:

| Candidate | Focus | Location |
|-----------|-------|----------|
| A | Export-first, `VizSession`, no evaluator | arena output (text) |
| B | `CriteriaGraph` + `CriteriaTimelineService` | `criteria_viz/rationale.md` + stubs |
| C | Eager `SessionBundle` | `criteria_viz/DESIGN.md` + stubs |

This document supersedes individual candidate docs for implementation. Stubs may be refactored to match the synthesized module map.
