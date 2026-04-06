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


def _append_once(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def _resolve_fcff_preferred_path(assumptions: dict, warnings: list[str]) -> str:
    preferred_path = str(assumptions.get("fcff_preferred_path") or "cfo").strip().lower()
    if preferred_path not in {"cfo", "ebiat"}:
        _append_once(warnings, "fcff_preferred_path_invalid_defaulted_to_cfo")
        return "cfo"
    return preferred_path


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


def _resolve_after_tax_interest_adjustment_from_values(
    interest_paid: float | None,
    interest_expense: float | None,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[float | None, str | None]:
    if interest_paid is not None:
        return abs(interest_paid) * (1.0 - float(tax.effective_tax_rate or 0.25)), "interest_paid"

    if interest_expense is not None:
        _append_once(warnings, "interest_paid_missing_used_interest_expense_proxy")
        return (
            abs(interest_expense) * (1.0 - float(tax.effective_tax_rate or 0.25)),
            "interest_expense_proxy",
        )

    return None, None


def _resolve_after_tax_interest_adjustment(
    fundamentals: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[float | None, str | None]:
    return _resolve_after_tax_interest_adjustment_from_values(
        _coerce_float(fundamentals.get("interest_paid")),
        _coerce_float(fundamentals.get("interest_expense")),
        tax,
        warnings,
    )


def _coerce_history_series(value) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, float] = {}
    for key, raw in value.items():
        numeric = _coerce_float(raw)
        if numeric is not None:
            out[str(key)] = numeric
    return dict(sorted(out.items()))


def _get_historical_series(fundamentals: dict, key: str) -> dict[str, float]:
    historical_series = fundamentals.get("historical_series") or {}
    if not isinstance(historical_series, dict):
        return {}
    return _coerce_history_series(historical_series.get(key))


def _last_n_periods(series: dict[str, float], limit: int = 3) -> list[tuple[str, float]]:
    return list(sorted(series.items()))[-limit:]


def _average_period_values(periods: list[tuple[str, float]]) -> float | None:
    if not periods:
        return None
    return sum(value for _, value in periods) / len(periods)


def _warn_on_large_fcff_gap(reconciliation_gap_pct: float | None, warnings: list[str]) -> None:
    if reconciliation_gap_pct is not None and abs(reconciliation_gap_pct) > 0.10:
        _append_once(warnings, "fcff_reconciliation_gap_pct_above_0.10")


def _summarize_interest_sources(sources: list[str]) -> str | None:
    if not sources:
        return None
    unique_sources = sorted(set(sources))
    if len(unique_sources) == 1:
        return unique_sources[0]
    return "mixed_interest_sources"


def _build_historical_fcff_paths(
    fundamentals: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, str]]:
    ebit_series = _get_historical_series(fundamentals, "ebit")
    ocf_series = _get_historical_series(fundamentals, "ocf")
    da_series = _get_historical_series(fundamentals, "da")
    capex_series = _get_historical_series(fundamentals, "capex")
    delta_nwc_series = _get_historical_series(fundamentals, "delta_nwc")
    interest_paid_series = _get_historical_series(fundamentals, "interest_paid")
    interest_expense_series = _get_historical_series(fundamentals, "interest_expense")

    ebiat_path_anchors: dict[str, float] = {}
    for period, ebit in ebit_series.items():
        ebiat = ebit * (1.0 - float(tax.effective_tax_rate or 0.25))
        ebiat_path_anchors[period] = (
            ebiat
            + da_series.get(period, 0.0)
            - capex_series.get(period, 0.0)
            - delta_nwc_series.get(period, 0.0)
        )

    cfo_path_anchors: dict[str, float] = {}
    cfo_after_tax_interest: dict[str, float] = {}
    cfo_interest_sources: dict[str, str] = {}
    for period, ocf in ocf_series.items():
        after_tax_interest, interest_source = _resolve_after_tax_interest_adjustment_from_values(
            interest_paid_series.get(period),
            interest_expense_series.get(period),
            tax,
            warnings,
        )
        if after_tax_interest is None:
            continue
        cfo_after_tax_interest[period] = after_tax_interest
        cfo_path_anchors[period] = ocf + after_tax_interest - capex_series.get(period, 0.0)
        if interest_source is not None:
            cfo_interest_sources[period] = interest_source

    return ebiat_path_anchors, cfo_path_anchors, cfo_after_tax_interest, cfo_interest_sources


def _compute_historical_mode_fcff_anchor(
    fundamentals: dict,
    assumptions: dict,
    tax: TaxAssumptions,
    warnings: list[str],
    anchor_mode: str,
) -> FCFFSummary | None:
    ebiat_history, cfo_history, cfo_after_tax_interest, cfo_interest_sources = _build_historical_fcff_paths(
        fundamentals,
        tax,
        warnings,
    )
    preferred_path = _resolve_fcff_preferred_path(assumptions, warnings)
    if not ebiat_history and not cfo_history:
        return None

    if anchor_mode == "reconciled_average":
        common_periods = sorted(set(ebiat_history) & set(cfo_history))[-3:]
        if common_periods:
            if len(common_periods) < 3:
                _append_once(
                    warnings,
                    "fcff_anchor_mode_reconciled_average_used_less_than_three_periods",
                )
            cfo_periods = [(period, cfo_history[period]) for period in common_periods]
            ebiat_periods = [(period, ebiat_history[period]) for period in common_periods]
            cfo_average = _average_period_values(cfo_periods)
            ebiat_average = _average_period_values(ebiat_periods)
            anchor = None
            if cfo_average is not None and ebiat_average is not None:
                anchor = (cfo_average + ebiat_average) / 2.0
            gap = None
            gap_pct = None
            if cfo_average is not None and ebiat_average is not None and anchor not in (None, 0):
                gap = cfo_average - ebiat_average
                gap_pct = gap / abs(anchor)
            _warn_on_large_fcff_gap(gap_pct, warnings)
            return FCFFSummary(
                anchor=anchor,
                anchor_method="reconciled_average_of_cfo_and_ebiat_paths",
                selected_path="reconciled",
                anchor_ebiat_path=ebiat_average,
                anchor_cfo_path=cfo_average,
                ebiat_path_available=ebiat_average is not None,
                cfo_path_available=cfo_average is not None,
                after_tax_interest=_average_period_values(
                    [
                        (period, cfo_after_tax_interest[period])
                        for period in common_periods
                        if period in cfo_after_tax_interest
                    ]
                ),
                after_tax_interest_source=_summarize_interest_sources(
                    [
                        cfo_interest_sources[period]
                        for period in common_periods
                        if period in cfo_interest_sources
                    ]
                ),
                reconciliation_gap=gap,
                reconciliation_gap_pct=gap_pct,
                anchor_mode="reconciled_average",
                anchor_observation_count=len(common_periods),
                delta_nwc_source=str(fundamentals.get("delta_nwc_source") or "historical_series"),
                last_report_period=common_periods[-1],
            )
        _append_once(
            warnings,
            "fcff_anchor_mode_reconciled_average_unavailable_fallback_to_three_period_average",
        )

    cfo_periods = _last_n_periods(cfo_history)
    ebiat_periods = _last_n_periods(ebiat_history)
    if not cfo_periods and not ebiat_periods:
        return None

    if cfo_periods and ebiat_periods:
        selected_path = preferred_path
        selected_periods = cfo_periods if preferred_path == "cfo" else ebiat_periods
    else:
        selected_periods = cfo_periods if cfo_periods else ebiat_periods
        selected_path = "cfo" if cfo_periods else "ebiat"
    if len(selected_periods) < 3:
        _append_once(warnings, "fcff_anchor_mode_three_period_average_used_less_than_three_periods")

    cfo_average = _average_period_values(cfo_periods)
    ebiat_average = _average_period_values(ebiat_periods)
    anchor = cfo_average if selected_path == "cfo" else ebiat_average
    gap = None
    gap_pct = None
    if cfo_average is not None and ebiat_average is not None and anchor not in (None, 0):
        gap = cfo_average - ebiat_average
        gap_pct = gap / abs(anchor)
    _warn_on_large_fcff_gap(gap_pct, warnings)

    return FCFFSummary(
        anchor=anchor,
        anchor_method=(
            "cfo_plus_after_tax_interest_minus_capex_three_period_average"
            if selected_path == "cfo"
            else "ebiat_plus_da_minus_capex_minus_delta_nwc_three_period_average"
        ),
        selected_path=selected_path,
        anchor_ebiat_path=ebiat_average,
        anchor_cfo_path=cfo_average,
        ebiat_path_available=ebiat_average is not None,
        cfo_path_available=cfo_average is not None,
        after_tax_interest=_average_period_values(
            [
                (period, cfo_after_tax_interest[period])
                for period, _ in cfo_periods
                if period in cfo_after_tax_interest
            ]
        ),
        after_tax_interest_source=(
            _summarize_interest_sources(
                [
                    cfo_interest_sources[period]
                    for period, _ in cfo_periods
                    if period in cfo_interest_sources
                ]
            )
            if selected_path == "cfo"
            else None
        ),
        reconciliation_gap=gap,
        reconciliation_gap_pct=gap_pct,
        anchor_mode="three_period_average",
        anchor_observation_count=len(selected_periods),
        delta_nwc_source=str(fundamentals.get("delta_nwc_source") or "historical_series"),
        last_report_period=selected_periods[-1][0],
    )


def _compute_ebiat_path_anchor(
    fundamentals: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[float | None, str | None]:
    ebit = _coerce_float(fundamentals.get("ebit"))
    if ebit is None:
        return None, None

    da = _coerce_float(fundamentals.get("da")) or 0.0
    capex = _coerce_float(fundamentals.get("capex")) or 0.0
    delta_nwc, delta_source = _resolve_delta_nwc(fundamentals, warnings)
    ebiat = ebit * (1.0 - float(tax.effective_tax_rate or 0.25))
    return ebiat + da - capex - delta_nwc, delta_source


def _compute_cfo_path_anchor(
    fundamentals: dict,
    tax: TaxAssumptions,
    warnings: list[str],
) -> tuple[float | None, float | None, str | None]:
    ocf = _coerce_float(fundamentals.get("ocf"))
    if ocf is None:
        return None, None, None

    after_tax_interest, interest_source = _resolve_after_tax_interest_adjustment(
        fundamentals,
        tax,
        warnings,
    )
    if after_tax_interest is None:
        return None, None, None

    capex = _coerce_float(fundamentals.get("capex")) or 0.0
    return ocf + after_tax_interest - capex, after_tax_interest, interest_source


def _compute_fcff_anchor(
    fundamentals: dict,
    assumptions: dict,
    tax: TaxAssumptions,
    warnings: list[str],
    diagnostics: list[str],
) -> FCFFSummary:
    explicit_anchor = _coerce_float(fundamentals.get("fcff_anchor"))
    if explicit_anchor is not None:
        return FCFFSummary(
            anchor=explicit_anchor,
            anchor_method=str(fundamentals.get("fcff_anchor_method") or "manual_input"),
            selected_path="manual_anchor",
            ebiat_path_available=False,
            cfo_path_available=False,
            anchor_mode="manual",
            anchor_observation_count=1,
            delta_nwc_source=str(fundamentals.get("delta_nwc_source") or "manual_input"),
            last_report_period=fundamentals.get("last_report_period"),
        )

    anchor_mode = str(assumptions.get("fcff_anchor_mode") or "latest").strip().lower()
    if anchor_mode not in {"manual", "latest", "three_period_average", "reconciled_average"}:
        _append_once(warnings, "fcff_anchor_mode_invalid_defaulted_to_latest")
        anchor_mode = "latest"
    if anchor_mode == "manual":
        raise ValueError("Missing fundamentals.fcff_anchor for manual fcff_anchor_mode")
    if anchor_mode in {"three_period_average", "reconciled_average"}:
        historical_fcff = _compute_historical_mode_fcff_anchor(
            fundamentals,
            assumptions,
            tax,
            warnings,
            anchor_mode,
        )
        if historical_fcff is not None:
            return historical_fcff
        _append_once(
            warnings,
            f"fcff_anchor_mode_{anchor_mode}_history_unavailable_fallback_to_latest",
        )

    preferred_path = _resolve_fcff_preferred_path(assumptions, warnings)
    ebiat_path_anchor, delta_source = _compute_ebiat_path_anchor(fundamentals, tax, warnings)
    cfo_path_anchor, after_tax_interest, interest_source = _compute_cfo_path_anchor(
        fundamentals,
        tax,
        warnings,
    )
    ebiat_path_available = ebiat_path_anchor is not None
    cfo_path_available = cfo_path_anchor is not None

    if not ebiat_path_available and not cfo_path_available:
        raise ValueError(
            "Missing FCFF anchor inputs: provide fundamentals.fcff_anchor, "
            "EBIAT-path inputs, or CFO-path inputs"
        )

    if cfo_path_available and ebiat_path_available:
        if preferred_path == "ebiat":
            anchor = float(ebiat_path_anchor)
            anchor_method = "ebiat_plus_da_minus_capex_minus_delta_nwc"
            selected_path = "ebiat"
            diagnostics.append("fcff_path_selector_preferred_ebiat")
        else:
            anchor = float(cfo_path_anchor)
            anchor_method = "cfo_plus_after_tax_interest_minus_capex"
            selected_path = "cfo"
            diagnostics.append("fcff_path_selector_preferred_cfo")
    elif cfo_path_available:
        anchor = cfo_path_anchor
        anchor_method = "cfo_plus_after_tax_interest_minus_capex"
        selected_path = "cfo"
        diagnostics.append("fcff_path_selector_only_cfo_available")
    else:
        anchor = float(ebiat_path_anchor)
        anchor_method = "ebiat_plus_da_minus_capex_minus_delta_nwc"
        selected_path = "ebiat"
        diagnostics.append("fcff_path_selector_only_ebiat_available")

    reconciliation_gap = None
    reconciliation_gap_pct = None
    if cfo_path_available and ebiat_path_available:
        reconciliation_gap = cfo_path_anchor - ebiat_path_anchor
        if anchor != 0:
            reconciliation_gap_pct = reconciliation_gap / abs(anchor)
    _warn_on_large_fcff_gap(reconciliation_gap_pct, warnings)

    return FCFFSummary(
        anchor=anchor,
        anchor_method=anchor_method,
        selected_path=selected_path,
        anchor_ebiat_path=ebiat_path_anchor,
        anchor_cfo_path=cfo_path_anchor,
        ebiat_path_available=ebiat_path_available,
        cfo_path_available=cfo_path_available,
        after_tax_interest=after_tax_interest,
        after_tax_interest_source=interest_source,
        reconciliation_gap=reconciliation_gap,
        reconciliation_gap_pct=reconciliation_gap_pct,
        anchor_mode="latest",
        anchor_observation_count=1,
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
    fcff = _compute_fcff_anchor(fundamentals, assumptions, tax, warnings, diagnostics)
    if fcff.anchor is None:
        raise ValueError("Unable to compute FCFF anchor")
    if fcff.anchor <= 0:
        warnings.append("fcff_anchor_non_positive")
    if fcff.selected_path:
        diagnostics.append(f"fcff_path_selected:{fcff.selected_path}")

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
