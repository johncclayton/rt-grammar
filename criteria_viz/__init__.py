"""Trade criteria visualizer — public API.

Callers should import only from this package root. Parsing, evaluation,
and trades CSV layout are internal implementation details.
"""

from criteria_viz.graph import CriteriaGraph, CriterionNode, build_criteria_graph
from criteria_viz.models import TradeCriteriaView, TradePhase, TradeRecord
from criteria_viz.series import BarSeries, CsvBarSeries, MockBarSeries
from criteria_viz.service import CriteriaTimelineService

__all__ = [
    "BarSeries",
    "CriteriaGraph",
    "CriteriaTimelineService",
    "CriterionNode",
    "CsvBarSeries",
    "MockBarSeries",
    "TradeCriteriaView",
    "TradePhase",
    "TradeRecord",
    "build_criteria_graph",
]
