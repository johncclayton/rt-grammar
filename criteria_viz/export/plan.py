"""Export plan and RealTest companion snippets (Results + Scan variants)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Mapping, Sequence

from criteria_viz.graph.build import build_criteria_graph
from criteria_viz.graph.model import CriteriaGraph, CriterionNode, TradePhase

ExportBackend = Literal["results", "scan"]


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

    def to_dict(self) -> dict:
        return {
            "rts_path": str(self.rts_path),
            "strategies": list(self.strategies),
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
    if node.kind == "data_ref":
        return node.label
    if node.kind == "strategy_root":
        return node.label
    if node.kind in ("param", "builtin"):
        return node.label
    if node.kind == "literal":
        return f"_lit_{node.label.replace('.', '_')}"
    safe = node.series_key.replace(":", "_")
    return safe


def _origin_for(node: CriterionNode) -> str:
    if node.kind == "data_ref":
        return f"data:{node.label}"
    if node.kind == "strategy_root":
        return f"strategy:{node.label}"
    return node.kind


def build_export_plan(
    graph: CriteriaGraph,
    *,
    rts_path: Path,
    strategy: str | None = None,
) -> ExportPlan:
    strategies = (strategy,) if strategy else graph.strategies
    per_strategy: dict[str, StrategyExportSpec] = {}

    for strat in strategies:
        specs: list[SeriesSpec] = []
        seen: set[str] = set()
        for phase in (TradePhase.ENTRY, TradePhase.EXIT):
            root_id = graph.root_for(strat, phase)
            if not root_id:
                continue
            for node_id in graph.reachable(root_id):
                node = graph.node(node_id)
                if node.series_key in seen:
                    continue
                if node.kind == "literal":
                    continue
                seen.add(node.series_key)
                specs.append(
                    SeriesSpec(
                        key=node.series_key,
                        csv_column=csv_column_for_node(node),
                        origin=_origin_for(node),
                        rts_ref=node.expr_source,
                        node_id=node.id,
                    )
                )
        per_strategy[strat] = StrategyExportSpec(strategy=strat, series=tuple(specs))

    return ExportPlan(
        rts_path=rts_path,
        strategies=tuple(per_strategy.keys()),
        per_strategy=per_strategy,
    )


def build_export_plan_from_rts(
    rts_path: Path,
    *,
    strategy: str | None = None,
    grammar_path: Path | None = None,
) -> ExportPlan:
    graph = build_criteria_graph(rts_path, strategy=strategy, grammar_path=grammar_path)
    return build_export_plan(graph, rts_path=rts_path, strategy=strategy or graph.strategies[0])


def render_companion_snippet(
    plan: ExportPlan,
    strategy: str,
    backend: ExportBackend = "results",
) -> str:
    spec = plan.per_strategy[strategy]
    lines = [
        f"// criteria_viz companion snippet ({backend}) for strategy: {strategy}",
        f"// Generated from {plan.rts_path.name} — run in RealTest on Windows to export bar series.",
        "",
    ]

    if backend == "results":
        lines.extend(_render_results_snippet(spec))
    else:
        lines.extend(_render_scan_snippet(spec))

    return "\n".join(lines) + "\n"


def _render_results_snippet(spec: StrategyExportSpec) -> list[str]:
    """Results-first variant (preferred once Windows experiments confirm shape)."""
    lines = [
        "// Preferred export path: inject/wrap with Results columns (per-bar TBD on RealTest).",
        "Results:",
    ]
    for s in spec.series:
        col = _safe_column_name(s.csv_column)
        lines.append(f"\t{col}:\t{{//}}\t{s.rts_ref}")
    lines.append("")
    lines.append("// Settings: point ResultsFile / export path at your series_export folder.")
    return lines


def _render_scan_snippet(spec: StrategyExportSpec) -> list[str]:
    """Scan + SaveScanAs fallback variant."""
    lines = [
        "// Fallback export path: Scan columns + SaveScanAs in Settings.",
        "Settings:",
        "\tSaveScanAs:\t?scriptpath?\\criteria_viz_scan.csv",
        "",
        "Scan:",
        "\tFilter:\t\tTrue",
        "\tSym:\t\t{?}\t?Symbol",
        "\tDate:\t\t{//}\tBarDate",
    ]
    for s in spec.series:
        col = _safe_column_name(s.csv_column)
        lines.append(f"\t{col}:\t\t{{#}}\t{s.rts_ref}")
    lines.append("\tSort:\t\tDate, Sym")
    return lines


def _safe_column_name(name: str) -> str:
    if name and name[0].isdigit():
        return f"_{name}"
    return name.replace(" ", "_")


def write_export_plan(path: Path, plan: ExportPlan) -> None:
    path.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")


def required_csv_columns(plan: ExportPlan, strategy: str) -> frozenset[str]:
    spec = plan.per_strategy[strategy]
    cols = {"Date"}
    cols.update(s.csv_column for s in spec.series)
    return frozenset(cols)
