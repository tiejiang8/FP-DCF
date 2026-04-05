from __future__ import annotations

from datetime import date
from math import isfinite

from .schemas import (
    CapitalStructure,
    FCFFSummary,
    TaxAssumptions,
    ValuationOutput,
    ValuationSummary,
    WACCInputs,
)


def _coerce_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if isfinite(out) else None


def _clip_rate(value: float | None, *, low: float = 0.0, high: float = 0.95) -> float | None:
    if value is None:
        return None
    return min(max(value, low), high)


def _normalize_weights(
    equity_weight: float | None,
    debt_weight: float | None,
    source: str | None = None,
) -> tuple[float, float, str]:
    ew = _coerce_float(equity_weight)
    dw = _coerce_float(debt_weight)

    if ew is None and dw is None:
        return 0.7, 0.3, "default"
    if ew is None and dw is not None:
        ew = max(0.0, 1.0 - dw)
    if dw is None and ew is not None:
        dw = max(0.0, 1.0 - ew)

    ew = 0.0 if ew is None else max(0.0, ew)
    dw = 0.0 if dw is None else max(0.0, dw)
    total = ew + dw
    if total <= 0:
        return 0.7, 0.3, "default"
    return ew / total, dw / total, source or "manual_input"


def _resolve_tax_inputs(
    payload: dict,
    warnings: list[str],
    diagnostics: list[str],
) -> TaxAssumptions:
    assumptions = payload.get("assumptions") or {}
    effective = _clip_rate(_coerce_float(assumptions.get("effective_tax_rate")))
    marginal = _clip_rate(_coerce_float(assumptions.get("marginal_tax_rate")))
    effective_source = (
        assumptions.get("effective_tax_rate_source")
        if effective is not None
        else None
    )
    marginal_source = (
        assumptions.get("marginal_tax_rate_source")
        if marginal is not None
        else None
    )
    if effective is not None and not effective_source:
        effective_source = "manual_input"
    if marginal is not None and not marginal_source:
        marginal_source = "manual_input"

    if effective is None and marginal is not None:
        effective = marginal
        effective_source = "reused_marginal_tax_rate"
        warnings.append("effective_tax_rate_missing_reused_marginal_tax_rate")
    elif effective is None:
        effective = 0.25
        effective_source = "default"
        warnings.append("effective_tax_rate_missing_defaulted_to_0.25")

    if marginal is None and assumptions.get("effective_tax_rate") is not None:
        marginal = effective
        marginal_source = "reused_effective_tax_rate"
        warnings.append("marginal_tax_rate_missing_reused_effective_tax_rate")
    elif marginal is None:
        marginal = 0.25
        marginal_source = "default"
        warnings.append("marginal_tax_rate_missing_defaulted_to_0.25")

    if effective_source != marginal_source or effective != marginal:
        diagnostics.append("tax_rate_paths_are_separated")
    else:
        diagnostics.append("tax_rate_paths_are_shared")

    return TaxAssumptions(
        effective_tax_rate=effective,
        effective_tax_rate_source=effective_source,
        marginal_tax_rate=marginal,
        marginal_tax_rate_source=marginal_source,
    )


def _resolve_delta_nwc(fundamentals: dict, warnings: list[str]) -> tuple[float, str]:
    candidates = [
        ("delta_nwc", "delta_nwc"),
        ("op_nwc_delta", "OpNWC_delta"),
        ("nwc_delta", "NWC_delta"),
    ]
    for key, source in candidates:
        value = _coerce_float(fundamentals.get(key))
        if value is not None:
            return value, str(fundamentals.get("delta_nwc_source") or source)

    change_wc = _coerce_float(fundamentals.get("change_in_working_capital"))
    if change_wc is not None:
        warnings.append("delta_nwc_derived_from_cash_flow_change_in_working_capital")
        return -change_wc, "cashflow_change_in_working_capital"

    warnings.append("delta_nwc_missing_assumed_zero")
    return 0.0, "assumed_zero"


def _compute_fcff_anchor(
    fundamentals: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> FCFFSummary:
    explicit_anchor = _coerce_float(fundamentals.get("fcff_anchor"))
    if explicit_anchor is not None:
        return FCFFSummary(
            anchor=explicit_anchor,
            anchor_method=str(fundamentals.get("fcff_anchor_method") or "manual_input"),
            delta_nwc_source=str(fundamentals.get("delta_nwc_source") or "manual_input"),
            last_report_period=fundamentals.get("last_report_period"),
        )

    ebit = _coerce_float(fundamentals.get("ebit"))
    da = _coerce_float(fundamentals.get("da")) or 0.0
    capex = _coerce_float(fundamentals.get("capex")) or 0.0
    delta_nwc, delta_source = _resolve_delta_nwc(fundamentals, warnings)

    if ebit is None:
        raise ValueError("Missing fundamentals.ebit or fundamentals.fcff_anchor")

    ebiat = ebit * (1.0 - float(tax.effective_tax_rate or 0.25))
    anchor = ebiat + da - capex - delta_nwc
    return FCFFSummary(
        anchor=anchor,
        anchor_method="ebiat_plus_da_minus_capex_minus_delta_nwc",
        delta_nwc_source=delta_source,
        last_report_period=fundamentals.get("last_report_period"),
    )


def _compute_wacc(
    payload: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[WACCInputs, CapitalStructure]:
    assumptions = payload.get("assumptions") or {}
    rf = _clip_rate(_coerce_float(assumptions.get("risk_free_rate")), low=0.0, high=0.25)
    erp = _clip_rate(_coerce_float(assumptions.get("equity_risk_premium")), low=0.0, high=0.25)
    beta = _coerce_float(assumptions.get("beta"))
    rd = _clip_rate(_coerce_float(assumptions.get("pre_tax_cost_of_debt")), low=0.0, high=0.25)

    rf_source = assumptions.get("risk_free_rate_source") if rf is not None else "default"
    erp_source = assumptions.get("equity_risk_premium_source") if erp is not None else "default"
    beta_source = assumptions.get("beta_source") if beta is not None else "default"
    rd_source = assumptions.get("pre_tax_cost_of_debt_source") if rd is not None else "default"
    if rf is not None and not rf_source:
        rf_source = "manual_input"
    if erp is not None and not erp_source:
        erp_source = "manual_input"
    if beta is not None and not beta_source:
        beta_source = "manual_input"
    if rd is not None and not rd_source:
        rd_source = "manual_input"

    if rf is None:
        rf = 0.04
        warnings.append("risk_free_rate_missing_defaulted_to_0.04")
    if erp is None:
        erp = 0.05
        warnings.append("equity_risk_premium_missing_defaulted_to_0.05")
    if beta is None:
        beta = 1.0
        warnings.append("beta_missing_defaulted_to_1.0")
    if rd is None:
        rd = 0.03
        warnings.append("pre_tax_cost_of_debt_missing_defaulted_to_0.03")

    equity_weight, debt_weight, weight_source = _normalize_weights(
        assumptions.get("equity_weight"),
        assumptions.get("debt_weight"),
        assumptions.get("capital_structure_source"),
    )
    cost_of_equity = rf + beta * erp
    wacc = (
        equity_weight * cost_of_equity
        + debt_weight * rd * (1.0 - float(tax.marginal_tax_rate or 0.25))
    )

    return (
        WACCInputs(
            risk_free_rate=rf,
            risk_free_rate_source=rf_source,
            equity_risk_premium=erp,
            equity_risk_premium_source=erp_source,
            beta=beta,
            beta_source=beta_source,
            cost_of_equity=cost_of_equity,
            pre_tax_cost_of_debt=rd,
            pre_tax_cost_of_debt_source=rd_source,
            wacc=wacc,
        ),
        CapitalStructure(
            equity_weight=equity_weight,
            debt_weight=debt_weight,
            source=weight_source,
        ),
    )


def _steady_state_valuation(
    fcff_anchor: float,
    wacc: float,
    growth_rate: float,
    net_debt: float,
    shares_out: float | None,
    warnings: list[str],
) -> ValuationSummary:
    effective_growth = growth_rate
    if effective_growth >= wacc:
        effective_growth = max(0.0, wacc - 0.01)
        warnings.append("terminal_growth_rate_clamped_below_wacc")

    fcff_1 = fcff_anchor * (1.0 + effective_growth)
    enterprise_value = fcff_1 / (wacc - effective_growth)
    equity_value = enterprise_value - net_debt
    per_share = equity_value / shares_out if shares_out and shares_out > 0 else None

    if shares_out in (None, 0):
        warnings.append("shares_out_missing_per_share_value_unavailable")

    return ValuationSummary(
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        per_share_value=per_share,
        terminal_growth_rate=growth_rate,
        terminal_growth_rate_effective=effective_growth,
        present_value_stage1=0.0,
        present_value_terminal=enterprise_value,
        terminal_value_share=1.0,
    )


def _two_stage_valuation(
    fcff_anchor: float,
    wacc: float,
    growth_rate_high: float,
    years_high: int,
    growth_rate_stable: float,
    net_debt: float,
    shares_out: float | None,
    warnings: list[str],
) -> ValuationSummary:
    years = max(1, int(years_high))
    g_stable_eff = growth_rate_stable
    if g_stable_eff >= wacc:
        g_stable_eff = max(0.0, wacc - 0.01)
        warnings.append("stable_growth_rate_clamped_below_wacc")

    fcff_t = fcff_anchor
    pv_stage1 = 0.0
    for year in range(1, years + 1):
        fcff_t = fcff_t * (1.0 + growth_rate_high)
        pv_stage1 += fcff_t / ((1.0 + wacc) ** year)

    fcff_terminal = fcff_t * (1.0 + g_stable_eff)
    terminal_value = fcff_terminal / (wacc - g_stable_eff)
    pv_terminal = terminal_value / ((1.0 + wacc) ** years)
    enterprise_value = pv_stage1 + pv_terminal
    equity_value = enterprise_value - net_debt
    per_share = equity_value / shares_out if shares_out and shares_out > 0 else None

    if shares_out in (None, 0):
        warnings.append("shares_out_missing_per_share_value_unavailable")

    terminal_share = pv_terminal / enterprise_value if enterprise_value else None
    if terminal_share is not None and terminal_share > 0.75:
        warnings.append("terminal_value_share_above_0.75")

    return ValuationSummary(
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        per_share_value=per_share,
        terminal_growth_rate=growth_rate_stable,
        terminal_growth_rate_effective=g_stable_eff,
        present_value_stage1=pv_stage1,
        present_value_terminal=pv_terminal,
        terminal_value_share=terminal_share,
    )


def run_valuation(payload: dict) -> ValuationOutput:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    fundamentals = payload.get("fundamentals") or {}
    assumptions = payload.get("assumptions") or {}
    warnings: list[str] = list(payload.get("_prefill_warnings", []))
    diagnostics: list[str] = list(payload.get("_prefill_diagnostics", []))

    tax = _resolve_tax_inputs(payload, warnings, diagnostics)
    fcff = _compute_fcff_anchor(fundamentals, tax, warnings)
    if fcff.anchor is None:
        raise ValueError("Unable to compute FCFF anchor")
    if fcff.anchor <= 0:
        warnings.append("fcff_anchor_non_positive")

    wacc_inputs, capital_structure = _compute_wacc(payload, tax, warnings)
    if wacc_inputs.wacc is None or wacc_inputs.wacc <= 0:
        raise ValueError("Unable to compute a positive WACC")

    growth_rate = _clip_rate(
        _coerce_float(assumptions.get("terminal_growth_rate")),
        low=0.0,
        high=0.15,
    )
    if growth_rate is None:
        growth_rate = 0.03
        warnings.append("terminal_growth_rate_missing_defaulted_to_0.03")

    net_debt = _coerce_float(fundamentals.get("net_debt")) or 0.0
    shares_out = _coerce_float(fundamentals.get("shares_out"))
    valuation_model = str(payload.get("valuation_model") or "steady_state_single_stage")

    if valuation_model == "two_stage":
        growth_rate_high = _clip_rate(
            _coerce_float(assumptions.get("high_growth_rate")),
            low=-0.5,
            high=1.0,
        )
        if growth_rate_high is None:
            growth_rate_high = 0.10
            warnings.append("high_growth_rate_missing_defaulted_to_0.10")
        years_high = int(_coerce_float(assumptions.get("high_growth_years")) or 5)
        valuation = _two_stage_valuation(
            fcff_anchor=fcff.anchor,
            wacc=wacc_inputs.wacc,
            growth_rate_high=growth_rate_high,
            years_high=years_high,
            growth_rate_stable=growth_rate,
            net_debt=net_debt,
            shares_out=shares_out,
            warnings=warnings,
        )
        diagnostics.append("valuation_model_two_stage")
    else:
        valuation = _steady_state_valuation(
            fcff_anchor=fcff.anchor,
            wacc=wacc_inputs.wacc,
            growth_rate=growth_rate,
            net_debt=net_debt,
            shares_out=shares_out,
            warnings=warnings,
        )
        diagnostics.append("valuation_model_steady_state_single_stage")

    if capital_structure.source == "default":
        warnings.append("capital_structure_weights_defaulted_to_0.7_0.3")

    output = ValuationOutput(
        ticker=str(payload.get("ticker") or "UNKNOWN"),
        market=str(payload.get("market") or "UNKNOWN"),
        currency=payload.get("currency"),
        as_of_date=str(payload.get("as_of_date") or date.today().isoformat()),
        valuation_model=valuation_model,
        tax=tax,
        wacc_inputs=wacc_inputs,
        capital_structure=capital_structure,
        fcff=fcff,
        valuation=valuation,
        diagnostics=diagnostics,
        warnings=warnings,
    )
    return output
