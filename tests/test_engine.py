from fp_dcf import run_valuation


def test_run_valuation_single_stage_from_fundamentals():
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

    out = run_valuation(payload)

    assert out.fcff.anchor == 77.0
    assert out.tax.effective_tax_rate == 0.20
    assert out.tax.marginal_tax_rate == 0.25
    assert out.wacc_inputs.wacc is not None
    assert out.valuation.enterprise_value is not None
    assert out.valuation.per_share_value is not None
    assert "tax_rate_paths_are_separated" in out.diagnostics


def test_run_valuation_two_stage_clamps_stable_growth_when_needed():
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
            "terminal_growth_rate": 0.20,
            "high_growth_rate": 0.12,
            "high_growth_years": 3,
        },
        "fundamentals": {
            "fcff_anchor": 100.0,
            "shares_out": 10.0,
            "net_debt": 0.0,
        },
    }

    out = run_valuation(payload)

    assert out.valuation.terminal_growth_rate_effective is not None
    assert out.valuation.terminal_growth_rate_effective < out.wacc_inputs.wacc
    assert "stable_growth_rate_clamped_below_wacc" in out.warnings
