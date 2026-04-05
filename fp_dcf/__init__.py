"""FP-DCF public package scaffold."""

from .engine import run_valuation
from .schemas import (
    CapitalStructure,
    FCFFSummary,
    TaxAssumptions,
    ValuationOutput,
    ValuationSummary,
    WACCInputs,
)

__all__ = [
    "CapitalStructure",
    "FCFFSummary",
    "TaxAssumptions",
    "ValuationOutput",
    "ValuationSummary",
    "WACCInputs",
    "run_valuation",
]

__version__ = "0.1.0"
