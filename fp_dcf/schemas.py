from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaxAssumptions:
    effective_tax_rate: float | None = None
    effective_tax_rate_source: str | None = None
    marginal_tax_rate: float | None = None
    marginal_tax_rate_source: str | None = None


@dataclass(slots=True)
class CapitalStructure:
    equity_weight: float | None = None
    debt_weight: float | None = None


@dataclass(slots=True)
class FCFFSummary:
    anchor: float | None = None
    anchor_method: str | None = None
    delta_nwc_source: str | None = None
    last_report_period: str | None = None


@dataclass(slots=True)
class ValuationOutput:
    ticker: str
    market: str
    valuation_model: str
    tax: TaxAssumptions = field(default_factory=TaxAssumptions)
    capital_structure: CapitalStructure = field(default_factory=CapitalStructure)
    fcff: FCFFSummary = field(default_factory=FCFFSummary)
    enterprise_value: float | None = None
    equity_value: float | None = None
    per_share_value: float | None = None
    diagnostics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
