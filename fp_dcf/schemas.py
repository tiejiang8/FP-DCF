from __future__ import annotations

from dataclasses import asdict, dataclass, field


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
    source: str | None = None


@dataclass(slots=True)
class WACCInputs:
    risk_free_rate: float | None = None
    risk_free_rate_source: str | None = None
    equity_risk_premium: float | None = None
    equity_risk_premium_source: str | None = None
    beta: float | None = None
    beta_source: str | None = None
    cost_of_equity: float | None = None
    pre_tax_cost_of_debt: float | None = None
    pre_tax_cost_of_debt_source: str | None = None
    wacc: float | None = None


@dataclass(slots=True)
class FCFFSummary:
    anchor: float | None = None
    anchor_method: str | None = None
    delta_nwc_source: str | None = None
    last_report_period: str | None = None


@dataclass(slots=True)
class ValuationSummary:
    enterprise_value: float | None = None
    equity_value: float | None = None
    per_share_value: float | None = None
    terminal_growth_rate: float | None = None
    terminal_growth_rate_effective: float | None = None
    present_value_stage1: float | None = None
    present_value_terminal: float | None = None
    terminal_value_share: float | None = None


@dataclass(slots=True)
class ValuationOutput:
    ticker: str
    market: str
    valuation_model: str
    currency: str | None = None
    as_of_date: str | None = None
    tax: TaxAssumptions = field(default_factory=TaxAssumptions)
    wacc_inputs: WACCInputs = field(default_factory=WACCInputs)
    capital_structure: CapitalStructure = field(default_factory=CapitalStructure)
    fcff: FCFFSummary = field(default_factory=FCFFSummary)
    valuation: ValuationSummary = field(default_factory=ValuationSummary)
    diagnostics: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
