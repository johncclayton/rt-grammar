"""Exceptions raised at package boundaries."""


class CriteriaVizError(Exception):
    """Base error for trade criteria visualizer."""


class ParseError(CriteriaVizError):
    """RTS file could not be parsed or extracted."""


class ExportError(CriteriaVizError):
    """Series export CSV does not match the export plan."""


class TradeError(CriteriaVizError):
    """Trade list could not be loaded or aligned to bar series."""
