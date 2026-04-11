from __future__ import annotations

from fp_dcf import build_wacc_terminal_growth_sensitivity
from fp_dcf.plotting import _format_metric


def test_build_wacc_terminal_growth_sensitivity_matches_base_case():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "effective_tax_rate": 0.20,
            "marginal_tax_rate": 0.25,
            "risk_free_rate": 0.04,
            "equity_risk_premium": 0.05,
            "beta": 1.1,
            "pre_tax_cost_of_debt": 0.03,
            "equity_weight": 0.8,
            "debt_weight": 0.2,
            "terminal_growth_rate": 0.03,
        },
        "fundamentals": {
            "ebit": 100.0,
            "da": 10.0,
            "capex": 8.0,
            "delta_nwc": 5.0,
            "shares_out": 10.0,
            "net_debt": 50.0,
        },
    }

    out = build_wacc_terminal_growth_sensitivity(payload)

    assert out.metric == "per_share_value"
    assert len(out.wacc_values) == 5
    assert len(out.terminal_growth_values) == 5
    assert len(out.matrix) == 5
    assert out.base_wacc in out.wacc_values
    assert out.base_terminal_growth_rate in out.terminal_growth_values

    row = out.wacc_values.index(out.base_wacc)
    col = out.terminal_growth_values.index(out.base_terminal_growth_rate)
    assert abs(out.matrix[row][col] - out.base_metric_value) < 1e-9
    assert "sensitivity_heatmap:wacc_x_terminal_growth" in out.diagnostics


def test_build_wacc_terminal_growth_sensitivity_marks_invalid_cells():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "effective_tax_rate": 0.20,
            "marginal_tax_rate": 0.25,
            "risk_free_rate": 0.04,
            "equity_risk_premium": 0.05,
            "beta": 1.1,
            "pre_tax_cost_of_debt": 0.03,
            "equity_weight": 0.8,
            "debt_weight": 0.2,
            "terminal_growth_rate": 0.03,
        },
        "fundamentals": {
            "fcff_anchor": 80.0,
            "shares_out": 10.0,
            "net_debt": 10.0,
        },
    }

    out = build_wacc_terminal_growth_sensitivity(
        payload,
        wacc_values=[0.05, 0.06],
        terminal_growth_values=[0.04, 0.05, 0.06],
    )

    assert out.matrix[0][1] is None
    assert out.matrix[0][2] is None
    assert any(item.startswith("sensitivity_invalid_cells:") for item in out.diagnostics)


def test_build_wacc_terminal_growth_sensitivity_two_stage_uses_stage1_aliases_and_market_price():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "two_stage",
        "assumptions": {
            "effective_tax_rate": 0.21,
            "marginal_tax_rate": 0.21,
            "risk_free_rate": 0.03,
            "equity_risk_premium": 0.04,
            "beta": 1.0,
            "pre_tax_cost_of_debt": 0.03,
            "equity_weight": 0.7,
            "debt_weight": 0.3,
            "terminal_growth_rate": 0.03,
            "stage1_growth_rate": 0.12,
            "stage1_years": 3,
        },
        "fundamentals": {
            "fcff_anchor": 100.0,
            "shares_out": 10.0,
            "net_debt": 0.0,
        },
    }

    out = build_wacc_terminal_growth_sensitivity(payload, market_price=123.45)

    assert out.market_price == 123.45
    row = out.wacc_values.index(out.base_wacc)
    col = out.terminal_growth_values.index(out.base_terminal_growth_rate)
    assert abs(out.matrix[row][col] - out.base_metric_value) < 1e-9


def test_format_metric_includes_upside_vs_market_price_for_per_share_value():
    text = _format_metric(120.0, "per_share_value", "USD", market_price=100.0)

    assert text == "USD 120.0\n(+20.0%)"
