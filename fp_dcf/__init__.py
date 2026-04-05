"""FP-DCF public package scaffold."""

from .engine import run_valuation
from .normalize import normalize_payload
from .sensitivity import build_wacc_terminal_growth_sensitivity
from .schemas import (
    CapitalStructure,
    FCFFSummary,
    SensitivityHeatmapOutput,
    TaxAssumptions,
    ValuationOutput,
    ValuationSummary,
    WACCInputs,
)

__all__ = [
    "CapitalStructure",
    "FCFFSummary",
    "SensitivityHeatmapOutput",
    "TaxAssumptions",
    "ValuationOutput",
    "ValuationSummary",
    "WACCInputs",
    "build_wacc_terminal_growth_sensitivity",
    "run_valuation",
    "normalize_payload",
]

__version__ = "0.1.0"
