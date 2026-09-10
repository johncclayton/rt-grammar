"""Export plan and RealTest companion snippets (Results + Scan variants)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence

from criteria_viz.export.reserved import is_reserved_item_name, safe_item_label
from criteria_viz.graph.build import build_criteria_graph
from criteria_viz.graph.model import CriteriaGraph, CriterionNode, TradePhase
from criteria_viz.graph.parse_rts import extract_parameters, parse_rts_file

ExportBackend = Literal["results", "scan"]

# RealTest item / column name limit
MAX_ITEM_NAME_LEN = 64
_VALID_ITEM_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def is_valid_realtest_item_name(name: str) -> bool:
    """RealTest: must start with letter/underscore; only letters, digits, period, underscore."""
    return bool(_VALID_ITEM_NAME.match(name)) and len(name) <= MAX_ITEM_NAME_LEN


@dataclass(frozen=True, slots=True)
class SeriesSpec:
    key: str
    csv_column: str
    origin: str
    rts_ref: str
    node_id: str


@dataclass(frozen=True, slots=True)
class StrategyExportSpec:
    strategy: str
    series: tuple[SeriesSpec, ...]


@dataclass(frozen=True, slots=True)
class ExportPlan:
    rts_path: Path
    strategies: tuple[str, ...]
    per_strategy: Mapping[str, StrategyExportSpec]
    parameters: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        return {
            "rts_path": str(self.rts_path),
            "strategies": list(self.strategies),
            "parameters": sorted(self.parameters),
            "per_strategy": {
                name: {
                    "strategy": spec.strategy,
                    "series": [
                        {
                            "key": s.key,
                            "csv_column": s.csv_column,
                            "origin": s.origin,
                            "rts_ref": s.rts_ref,
                            "node_id": s.node_id,
                        }
                        for s in spec.series
                    ],
                }
                for name, spec in self.per_strategy.items()
            },
        }


def csv_column_for_node(node: CriterionNode) -> str:
    if node.kind in ("data_ref", "strategy_root", "param", "builtin"):
        base = _clamp_item_name(node.label)
    elif node.kind == "literal":
        base = _clamp_item_name(f"_lit_{node.label.replace('.', '_')}")
    elif node.id.startswith("cv:"):
        base = _clamp_item_name(f"cv_{node.id.split(':', 1)[1]}")
    else:
        base = _clamp_item_name(node.label.replace(" ", "_"))

    if is_reserved_item_name(base):
        # RHS may still reference Close, C, etc.; LHS needs a non-reserved alias.
        if node.id.startswith("cv:"):
            return _clamp_item_name(f"cv_{node.id.split(':', 1)[1]}")
        return _clamp_item_name(safe_item_label(base))
    return base


def export_date_column() -> str:
    """CSV / Scan column label for bar date (BarDate on RHS)."""
    return _clamp_item_name(safe_item_label("Date"))


# def param_bridge_name(param: str) -> str:
#     """Data: bridge for Data Scan only — TestScan uses Parameters directly."""
#     base = _clamp_item_name(f"prm_{param}")
#     if is_reserved_item_name(base):
#         return _clamp_item_name(safe_item_label(base))
#     return base


def _clamp_item_name(name: str) -> str:
    name = name.strip()
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    name = name.replace(" ", "_").replace("%", "pct")
    if len(name) <= MAX_ITEM_NAME_LEN:
        return name
    digest = hashlib.sha256(name.encode()).hexdigest()[:8]
    keep = MAX_ITEM_NAME_LEN - 9  # underscore + 8 hex chars
    return f"{name[:keep]}_{digest}"


def _origin_for(node: CriterionNode) -> str:
    if node.kind == "data_ref":
        return f"data:{node.label}"
    if node.kind == "strategy_root":
        return f"strategy:{node.label}"
    return node.kind


def _export_priority(node: CriterionNode) -> int:
    if node.kind == "strategy_root":
        return 0
    if node.kind == "data_ref":
        return 1
    if node.id.startswith("ref:"):
        return 2
    return 3


def _skip_export_node(node: CriterionNode) -> bool:
    if node.kind in ("literal", "string_literal"):
        return True
    if node.kind == "builtin" and node.label.lower() in ("not", "and", "or"):
        return True
    # TestScan reads Parameters directly; skip param re-export columns (they shadow params).
    if node.kind == "param" and node.expr_source == node.label:
        return True
    return not is_valid_realtest_item_name(csv_column_for_node(node))


def build_export_plan(
    graph: CriteriaGraph,
    *,
    rts_path: Path,
    strategy: str | None = None,
) -> ExportPlan:
    strategies = (strategy,) if strategy else graph.strategies
    per_strategy: dict[str, StrategyExportSpec] = {}

    for strat in strategies:
        candidates: list[tuple[int, str, CriterionNode]] = []
        seen_keys: set[str] = set()
        for phase in (TradePhase.ENTRY, TradePhase.EXIT):
            root_id = graph.root_for(strat, phase)
            if not root_id:
                continue
            for node_id in graph.reachable(root_id):
                node = graph.node(node_id)
                if node.series_key in seen_keys:
                    continue
                seen_keys.add(node.series_key)
                if _skip_export_node(node):
                    continue
                candidates.append((_export_priority(node), node_id, node))

        best_by_expr: dict[str, tuple[int, str, CriterionNode]] = {}
        for priority, node_id, node in candidates:
            prev = best_by_expr.get(node.expr_source)
            if prev is None or priority < prev[0]:
                best_by_expr[node.expr_source] = (priority, node_id, node)

        specs = [
            SeriesSpec(
                key=node.series_key,
                csv_column=csv_column_for_node(node),
                origin=_origin_for(node),
                rts_ref=node.expr_source,
                node_id=node.id,
            )
            for _, _, node in sorted(best_by_expr.values(), key=lambda t: t[1])
        ]
        per_strategy[strat] = StrategyExportSpec(strategy=strat, series=tuple(specs))

    return ExportPlan(
        rts_path=rts_path,
        strategies=tuple(per_strategy.keys()),
        per_strategy=per_strategy,
        parameters=frozenset(),
    )


def build_export_plan_from_rts(
    rts_path: Path,
    *,
    strategy: str | None = None,
    grammar_path: Path | None = None,
) -> ExportPlan:
    tree = parse_rts_file(rts_path, grammar_path=grammar_path)
    parameters = extract_parameters(tree)
    graph = build_criteria_graph(
        rts_path, strategy=strategy, grammar_path=grammar_path, tree=tree
    )
    plan = build_export_plan(graph, rts_path=rts_path, strategy=strategy or graph.strategies[0])
    return ExportPlan(
        rts_path=plan.rts_path,
        strategies=plan.strategies,
        per_strategy=plan.per_strategy,
        parameters=parameters,
    )


def companion_snippet_name(strategy: str, backend: ExportBackend = "scan") -> str:
    return f"{strategy}_{backend}.rts"


def include_snippet_from_main(strategy: str, backend: ExportBackend = "scan") -> str:
    """Include line to add to the primary strategy script."""
    return f"?scriptpath?/{companion_snippet_name(strategy, backend)}"


def render_companion_snippet(
    plan: ExportPlan,
    strategy: str,
    backend: ExportBackend = "scan",
    *,
    wrapper_dir: Path | None = None,
) -> str:
    """Companion snippet for criteria export (TestScan by default)."""
    _ = wrapper_dir
    spec = plan.per_strategy[strategy]
    snippet_name = companion_snippet_name(strategy, backend)
    lines = [
        f"// criteria_viz export companion ({backend}) for strategy: {strategy}",
        f"// Source strategy: {plan.rts_path.name}",
        f"// Include this file FROM the primary strategy, e.g.:",
        f"//\tInclude:\t{include_snippet_from_main(strategy, backend)}",
        f"// Run the primary strategy in Test mode:",
        f"//\tRealTest.exe -test {plan.rts_path.name}",
        "",
    ]

    if backend == "results":
        lines.extend(_render_results_snippet(spec))
    else:
        lines.extend(_render_testscan_snippet(spec))

    return "\n".join(lines) + "\n"


def _render_results_snippet(spec: StrategyExportSpec) -> list[str]:
    """Results-first variant (preferred once Windows experiments confirm shape)."""
    lines = [
        "// Per-bar formula columns — confirm RealTest output shape on Windows.",
        "Results:",
    ]
    for s in spec.series:
        col = _safe_column_name(s.csv_column)
        lines.append(f"\t{col}:\t{{//}}\t{s.rts_ref}")
    lines.append("")
    lines.append("// Settings: point ResultsFile / export path at your series_export folder.")
    return lines


# Data Scan bridged Parameters via Data: — not used; TestScan reads Parameters directly.
#
# def _params_in_formulas(formulas: Iterable[str], parameters: frozenset[str]) -> frozenset[str]:
#     ...
#
# def _substitute_param_bridges(formula: str, bridges: Mapping[str, str]) -> str:
#     ...


def _testscan_column_name(csv_column: str, rts_ref: str) -> str:
    """TestScan columns cannot be named like their sole identifier (self-reference)."""
    col = _safe_column_name(csv_column)
    if col == rts_ref.strip():
        return _safe_column_name(f"cv_{csv_column}")
    return col


def _render_testscan_snippet(spec: StrategyExportSpec) -> list[str]:
    """TestScan export — run primary strategy with RealTest.exe -test."""
    date_col = export_date_column()
    lines = [
        "TestSettings:",
        "\tTestOutput:\t\tScan",
        "\tTestScanAllDates:\tTrue",
        "\tSaveScanAs:\t\t?scriptpath?\\criteria_viz_testscan.csv",
        "",
        "TestScan:",
        "\tFilter:\t\tTrue",
        "\tSym:\t\t{?}\t?Symbol",
        f"\t{date_col}:\t\t{{//}}\tBarDate",
    ]
    for s in spec.series:
        col = _testscan_column_name(s.csv_column, s.rts_ref)
        lines.append(f"\t{col}:\t\t{{#}}\t{s.rts_ref}")
    lines.append(f"\tSort:\t\t{date_col}, Sym")
    return lines


def _safe_column_name(name: str) -> str:
    if name and name[0].isdigit():
        return f"_{name}"
    return name.replace(" ", "_")


def write_export_plan(path: Path, plan: ExportPlan) -> None:
    path.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")


def expr_to_column_map(plan: ExportPlan, strategy: str) -> Mapping[str, str]:
    """Map formula text to export column (for nodes deduped out of the plan)."""
    return {s.rts_ref: s.csv_column for s in plan.per_strategy[strategy].series}


def required_csv_columns(plan: ExportPlan, strategy: str) -> frozenset[str]:
    spec = plan.per_strategy[strategy]
    cols = {export_date_column()}
    cols.update(s.csv_column for s in spec.series)
    return frozenset(cols)
