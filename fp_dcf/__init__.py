"""FP-DCF public package scaffold."""

from .engine import run_valuation
from .market_implied_growth import resolve_market_inputs
from .normalize import normalize_payload
from .sensitivity import build_wacc_terminal_growth_sensitivity
from .schemas import (
    CapitalStructure,
    FCFFSummary,
    MarketImpliedGrowthInput,
    MarketImpliedGrowthOutput,
    MarketInputsSummary,
    SensitivityHeatmapOutput,
    TaxAssumptions,
    ValuationOutput,
    ValuationSummary,
    WACCInputs,
)

__all__ = [
    "CapitalStructure",
    "FCFFSummary",
    "MarketImpliedGrowthInput",
    "MarketImpliedGrowthOutput",
    "MarketInputsSummary",
    "SensitivityHeatmapOutput",
    "TaxAssumptions",
    "ValuationOutput",
    "ValuationSummary",
    "WACCInputs",
    "build_wacc_terminal_growth_sensitivity",
    "run_valuation",
    "normalize_payload",
    "resolve_market_inputs",
]

__version__ = "0.4.0"
