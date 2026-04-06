from __future__ import annotations

from math import isfinite

from .schemas import ImpliedGrowthSummary, MarketInputsSummary


def _coerce_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if isfinite(out) else None


def _pick_float(*candidates: tuple[object, str]) -> tuple[float | None, str | None]:
    for value, source in candidates:
        coerced = _coerce_float(value)
        if coerced is not None:
            return coerced, source
    return None, None


def resolve_market_inputs(payload: dict) -> MarketInputsSummary:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    market_inputs = payload.get("market_inputs") or {}
    fundamentals = payload.get("fundamentals") or {}

    enterprise_value_market, enterprise_value_market_source = _pick_float(
        (market_inputs.get("enterprise_value_market"), "market_inputs.enterprise_value_market"),
    )
    market_price, market_price_source = _pick_float(
        (market_inputs.get("market_price"), "market_inputs.market_price"),
        (fundamentals.get("market_price"), "fundamentals.market_price"),
    )
    shares_out, shares_out_source = _pick_float(
        (market_inputs.get("shares_out"), "market_inputs.shares_out"),
        (fundamentals.get("shares_out"), "fundamentals.shares_out"),
    )
    net_debt, net_debt_source = _pick_float(
        (market_inputs.get("net_debt"), "market_inputs.net_debt"),
        (fundamentals.get("net_debt"), "fundamentals.net_debt"),
    )

    equity_value_market = None
    if market_price is not None and shares_out is not None:
        equity_value_market = market_price * shares_out

    if enterprise_value_market is None and equity_value_market is not None and net_debt is not None:
        enterprise_value_market = equity_value_market + net_debt
        enterprise_value_market_source = "derived_from_market_price_shares_out_and_net_debt"

    return MarketInputsSummary(
        enterprise_value_market=enterprise_value_market,
        enterprise_value_market_source=enterprise_value_market_source,
        equity_value_market=equity_value_market,
        market_price=market_price,
        market_price_source=market_price_source,
        shares_out=shares_out,
        shares_out_source=shares_out_source,
        net_debt=net_debt,
        net_debt_source=net_debt_source,
    )


def solve_one_stage_implied_growth(
    *,
    fcff_anchor: float,
    wacc: float,
    enterprise_value_market: float,
) -> float:
    fcff = _coerce_float(fcff_anchor)
    discount_rate = _coerce_float(wacc)
    enterprise_value = _coerce_float(enterprise_value_market)

    if fcff is None:
        raise ValueError("fcff_anchor is required for implied growth")
    if discount_rate is None or discount_rate <= 0:
        raise ValueError("wacc must be positive for implied growth")
    if enterprise_value is None or enterprise_value <= 0:
        raise ValueError("enterprise_value_market must be positive for implied growth")

    denominator = enterprise_value + fcff
    if denominator == 0:
        raise ValueError("one-stage implied growth denominator cannot be zero")

    return (enterprise_value * discount_rate - fcff) / denominator


def _two_stage_enterprise_value(
    *,
    fcff_anchor: float,
    wacc: float,
    high_growth_rate: float,
    high_growth_years: int,
    stable_growth_rate: float,
) -> float:
    if stable_growth_rate >= wacc:
        raise ValueError("stable_growth_rate must be below wacc for two-stage implied growth")

    fcff_t = fcff_anchor
    pv_stage1 = 0.0
    for year in range(1, max(1, int(high_growth_years)) + 1):
        fcff_t = fcff_t * (1.0 + high_growth_rate)
        pv_stage1 += fcff_t / ((1.0 + wacc) ** year)

    fcff_terminal = fcff_t * (1.0 + stable_growth_rate)
    terminal_value = fcff_terminal / (wacc - stable_growth_rate)
    pv_terminal = terminal_value / ((1.0 + wacc) ** max(1, int(high_growth_years)))
    return pv_stage1 + pv_terminal


def solve_two_stage_implied_high_growth_rate(
    *,
    fcff_anchor: float,
    wacc: float,
    enterprise_value_market: float,
    stable_growth_rate: float,
    high_growth_years: int,
    lower_bound: float = -0.5,
    upper_bound: float = 1.0,
    tolerance: float = 1e-7,
    max_iterations: int = 200,
) -> tuple[float, int]:
    fcff = _coerce_float(fcff_anchor)
    discount_rate = _coerce_float(wacc)
    enterprise_value = _coerce_float(enterprise_value_market)
    lower = _coerce_float(lower_bound)
    upper = _coerce_float(upper_bound)
    stable = _coerce_float(stable_growth_rate)

    if fcff is None:
        raise ValueError("fcff_anchor is required for implied growth")
    if discount_rate is None or discount_rate <= 0:
        raise ValueError("wacc must be positive for implied growth")
    if enterprise_value is None or enterprise_value <= 0:
        raise ValueError("enterprise_value_market must be positive for implied growth")
    if stable is None:
        raise ValueError("stable_growth_rate is required for two-stage implied growth")
    if lower is None or upper is None or lower >= upper:
        raise ValueError("two-stage implied growth bounds must satisfy lower_bound < upper_bound")

    def objective(growth_rate: float) -> float:
        return _two_stage_enterprise_value(
            fcff_anchor=fcff,
            wacc=discount_rate,
            high_growth_rate=growth_rate,
            high_growth_years=high_growth_years,
            stable_growth_rate=stable,
        ) - enterprise_value

    f_lower = objective(lower)
    f_upper = objective(upper)
    if f_lower == 0:
        return lower, 0
    if f_upper == 0:
        return upper, 0
    if f_lower * f_upper > 0:
        raise ValueError("two-stage implied growth bounds do not bracket the market enterprise value")

    iterations = 0
    while iterations < max_iterations:
        midpoint = (lower + upper) / 2.0
        f_mid = objective(midpoint)
        if abs(f_mid) <= tolerance or abs(upper - lower) <= tolerance:
            return midpoint, iterations + 1
        if f_lower * f_mid <= 0:
            upper = midpoint
            f_upper = f_mid
        else:
            lower = midpoint
            f_lower = f_mid
        iterations += 1

    return (lower + upper) / 2.0, iterations


def _resolve_implied_growth_model(payload: dict) -> tuple[bool, str]:
    config = payload.get("implied_growth")
    if config is None:
        return False, "one_stage"
    if not isinstance(config, dict):
        raise TypeError("payload.implied_growth must be an object when provided")
    if config.get("enabled") is False:
        return False, str(config.get("model") or "one_stage")
    return True, str(config.get("model") or "one_stage")


def build_implied_growth_output(payload: dict, valuation_result: dict) -> tuple[MarketInputsSummary, ImpliedGrowthSummary] | None:
    enabled, model = _resolve_implied_growth_model(payload)
    if not enabled:
        return None
    if not isinstance(valuation_result, dict):
        raise TypeError("valuation_result must be a dict")

    market_inputs = resolve_market_inputs(payload)
    if market_inputs.enterprise_value_market is None:
        return None

    fcff_anchor = _coerce_float(((valuation_result.get("fcff") or {}).get("anchor")))
    wacc = _coerce_float(((valuation_result.get("wacc_inputs") or {}).get("wacc")))
    if fcff_anchor is None:
        raise ValueError("implied growth requires fcff.anchor from the valuation result")
    if wacc is None or wacc <= 0:
        raise ValueError("implied growth requires a positive wacc from the valuation result")

    config = payload.get("implied_growth") or {}
    warnings: list[str] = []
    diagnostics: list[str] = []

    if model == "two_stage":
        stable_growth_rate = _pick_float(
            (config.get("stable_growth_rate"), "payload.implied_growth.stable_growth_rate"),
            (
                ((valuation_result.get("valuation") or {}).get("terminal_growth_rate_effective")),
                "valuation.terminal_growth_rate_effective",
            ),
            (
                ((payload.get("assumptions") or {}).get("terminal_growth_rate")),
                "payload.assumptions.terminal_growth_rate",
            ),
        )[0]
        if stable_growth_rate is None:
            stable_growth_rate = 0.03
            warnings.append("implied_growth_stable_growth_rate_missing_defaulted_to_0.03")

        high_growth_years = int(_coerce_float(config.get("high_growth_years")) or ((payload.get("assumptions") or {}).get("high_growth_years") or 5))
        lower_bound = _coerce_float(config.get("lower_bound"))
        upper_bound = _coerce_float(config.get("upper_bound"))
        tolerance = _coerce_float(config.get("tolerance")) or 1e-7
        lower_bound = -0.5 if lower_bound is None else lower_bound
        upper_bound = 1.0 if upper_bound is None else upper_bound

        implied_high_growth_rate, iterations = solve_two_stage_implied_high_growth_rate(
            fcff_anchor=fcff_anchor,
            wacc=wacc,
            enterprise_value_market=market_inputs.enterprise_value_market,
            stable_growth_rate=stable_growth_rate,
            high_growth_years=high_growth_years,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            tolerance=tolerance,
        )
        diagnostics.append("implied_growth_model:two_stage")
        return market_inputs, ImpliedGrowthSummary(
            enabled=True,
            model="two_stage",
            solver="bisection",
            success=True,
            enterprise_value_market=market_inputs.enterprise_value_market,
            fcff_anchor=fcff_anchor,
            wacc=wacc,
            one_stage=None,
            two_stage={
                "high_growth_rate": implied_high_growth_rate,
                "high_growth_years": high_growth_years,
                "terminal_growth_rate": stable_growth_rate,
            },
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            tolerance=tolerance,
            iterations=iterations,
            diagnostics=diagnostics,
            warnings=warnings,
        )

    implied_growth_rate = solve_one_stage_implied_growth(
        fcff_anchor=fcff_anchor,
        wacc=wacc,
        enterprise_value_market=market_inputs.enterprise_value_market,
    )
    if implied_growth_rate >= wacc:
        warnings.append("implied_growth_rate_at_or_above_wacc")
    if implied_growth_rate <= -1.0:
        warnings.append("implied_growth_rate_at_or_below_negative_one")
    diagnostics.append("implied_growth_model:one_stage")
    return market_inputs, ImpliedGrowthSummary(
        enabled=True,
        model="one_stage",
        solver="closed_form",
        success=True,
        enterprise_value_market=market_inputs.enterprise_value_market,
        fcff_anchor=fcff_anchor,
        wacc=wacc,
        one_stage={"growth_rate": implied_growth_rate},
        two_stage=None,
        diagnostics=diagnostics,
        warnings=warnings,
    )
