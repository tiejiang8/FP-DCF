"""FP-DCF public package scaffold."""

from .engine import run_valuation
from .implied_growth import (
    build_implied_growth_output,
    resolve_market_inputs,
    solve_one_stage_implied_growth,
    solve_two_stage_implied_high_growth_rate,
)
from .normalize import normalize_payload
from .sensitivity import build_wacc_terminal_growth_sensitivity
from .schemas import (
    CapitalStructure,
    FCFFSummary,
    ImpliedGrowthSummary,
    MarketInputsSummary,
    MarketImpliedStage1GrowthSummary,
    SensitivityHeatmapOutput,
    TaxAssumptions,
    ValuationOutput,
    ValuationSummary,
    WACCInputs,
)

__all__ = [
    "CapitalStructure",
    "FCFFSummary",
    "ImpliedGrowthSummary",
    "MarketInputsSummary",
    "MarketImpliedStage1GrowthSummary",
    "SensitivityHeatmapOutput",
    "TaxAssumptions",
    "ValuationOutput",
    "ValuationSummary",
    "WACCInputs",
    "build_implied_growth_output",
    "build_wacc_terminal_growth_sensitivity",
    "run_valuation",
    "normalize_payload",
    "resolve_market_inputs",
    "solve_one_stage_implied_growth",
    "solve_two_stage_implied_high_growth_rate",
]

__version__ = "0.4.0"
