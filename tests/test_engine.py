import pytest

from fp_dcf import run_valuation
from fp_dcf.engine import _build_three_stage_growth_schedule


def _three_stage_payload(**assumption_overrides):
    assumptions = {
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
        "stage2_end_growth_rate": 0.06,
        "stage2_years": 2,
        "stage2_decay_mode": "linear",
    }
    assumptions.update(assumption_overrides)
    return {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "three_stage",
        "assumptions": assumptions,
        "fundamentals": {
            "fcff_anchor": 100.0,
            "shares_out": 10.0,
            "net_debt": 0.0,
        },
    }


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
    assert out.fcff.anchor_method == "ebiat_plus_da_minus_capex_minus_delta_nwc"
    assert out.fcff.selected_path == "ebiat"
    assert out.fcff.anchor_ebiat_path == 77.0
    assert out.fcff.anchor_cfo_path is None
    assert out.fcff.ebiat_path_available is True
    assert out.fcff.cfo_path_available is False
    assert out.fcff.after_tax_interest is None
    assert out.fcff.after_tax_interest_source is None
    assert out.fcff.anchor_mode == "latest"
    assert out.fcff.anchor_observation_count == 1
    assert out.fcff.reconciliation_gap is None
    assert out.tax.effective_tax_rate == 0.20
    assert out.tax.marginal_tax_rate == 0.25
    assert out.wacc_inputs.wacc is not None
    assert out.valuation.enterprise_value is not None
    assert out.valuation.per_share_value is not None
    assert "fcff_path_selected:ebiat" in out.diagnostics
    assert "tax_rate_paths_are_separated" in out.diagnostics


def test_run_valuation_prefers_cfo_path_and_reports_reconciliation_gap():
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
            "ocf": 70.0,
            "interest_paid": 20.0,
            "da": 10.0,
            "capex": 8.0,
            "delta_nwc": 5.0,
            "shares_out": 10.0,
            "net_debt": 50.0,
        },
    }

    out = run_valuation(payload)

    assert out.fcff.anchor == 78.0
    assert out.fcff.anchor_method == "cfo_plus_after_tax_interest_minus_capex"
    assert out.fcff.selected_path == "cfo"
    assert out.fcff.anchor_ebiat_path == 77.0
    assert out.fcff.anchor_cfo_path == 78.0
    assert out.fcff.ebiat_path_available is True
    assert out.fcff.cfo_path_available is True
    assert out.fcff.after_tax_interest == pytest.approx(16.0)
    assert out.fcff.after_tax_interest_source == "interest_paid"
    assert out.fcff.anchor_mode == "latest"
    assert out.fcff.anchor_observation_count == 1
    assert out.fcff.reconciliation_gap == pytest.approx(1.0)
    assert out.fcff.reconciliation_gap_pct == pytest.approx(1.0 / 78.0)
    assert "fcff_path_selector_preferred_cfo" in out.diagnostics
    assert "fcff_path_selected:cfo" in out.diagnostics


def test_run_valuation_respects_fcff_preferred_path_when_both_paths_are_available():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "fcff_preferred_path": "ebiat",
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
            "ocf": 70.0,
            "interest_paid": 20.0,
            "da": 10.0,
            "capex": 8.0,
            "delta_nwc": 5.0,
            "shares_out": 10.0,
            "net_debt": 50.0,
        },
    }

    out = run_valuation(payload)

    assert out.fcff.selected_path == "ebiat"
    assert out.fcff.anchor == 77.0
    assert out.fcff.anchor_ebiat_path == 77.0
    assert out.fcff.anchor_cfo_path == 78.0
    assert "fcff_path_selector_preferred_ebiat" in out.diagnostics


def test_run_valuation_warns_when_interest_expense_proxies_interest_paid():
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
            "ocf": 70.0,
            "interest_expense": 20.0,
            "capex": 8.0,
            "shares_out": 10.0,
            "net_debt": 50.0,
        },
    }

    out = run_valuation(payload)

    assert out.fcff.anchor == 78.0
    assert out.fcff.selected_path == "cfo"
    assert out.fcff.after_tax_interest == pytest.approx(16.0)
    assert out.fcff.after_tax_interest_source == "interest_expense_proxy"
    assert "interest_paid_missing_used_interest_expense_proxy" in out.warnings
    assert "fcff_path_selector_only_cfo_available" in out.diagnostics


def test_run_valuation_warns_when_fcff_reconciliation_gap_is_large():
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
            "ocf": 95.0,
            "interest_paid": 20.0,
            "da": 10.0,
            "capex": 8.0,
            "delta_nwc": 5.0,
            "shares_out": 10.0,
            "net_debt": 50.0,
        },
    }

    out = run_valuation(payload)

    assert out.fcff.reconciliation_gap_pct is not None
    assert abs(out.fcff.reconciliation_gap_pct) > 0.10
    assert "fcff_reconciliation_gap_pct_above_0.10" in out.warnings


def test_run_valuation_supports_explicit_latest_fcff_anchor_mode():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "fcff_anchor_mode": "latest",
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
    assert out.fcff.anchor_mode == "latest"
    assert out.fcff.anchor_observation_count == 1


def test_run_valuation_supports_three_period_average_fcff_anchor_mode():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "fcff_anchor_mode": "three_period_average",
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
            "shares_out": 10.0,
            "net_debt": 50.0,
            "historical_series": {
                "ebit": {
                    "2023-12-31": 130.0,
                    "2024-12-31": 140.0,
                    "2025-12-31": 150.0,
                },
                "ocf": {
                    "2023-12-31": 100.0,
                    "2024-12-31": 110.0,
                    "2025-12-31": 120.0,
                },
                "da": {
                    "2023-12-31": 10.0,
                    "2024-12-31": 10.0,
                    "2025-12-31": 10.0,
                },
                "capex": {
                    "2023-12-31": 20.0,
                    "2024-12-31": 20.0,
                    "2025-12-31": 20.0,
                },
                "delta_nwc": {
                    "2023-12-31": 5.0,
                    "2024-12-31": 5.0,
                    "2025-12-31": 5.0,
                },
                "interest_paid": {
                    "2023-12-31": 10.0,
                    "2024-12-31": 10.0,
                    "2025-12-31": 10.0,
                },
            },
        },
    }

    out = run_valuation(payload)

    assert out.fcff.anchor == pytest.approx(98.0)
    assert out.fcff.anchor_method == "cfo_plus_after_tax_interest_minus_capex_three_period_average"
    assert out.fcff.selected_path == "cfo"
    assert out.fcff.anchor_cfo_path == pytest.approx(98.0)
    assert out.fcff.anchor_ebiat_path == pytest.approx(97.0)
    assert out.fcff.anchor_mode == "three_period_average"
    assert out.fcff.anchor_observation_count == 3
    assert out.fcff.reconciliation_gap == pytest.approx(1.0)
    assert out.fcff.reconciliation_gap_pct == pytest.approx(1.0 / 98.0)


def test_run_valuation_supports_reconciled_average_fcff_anchor_mode():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "fcff_anchor_mode": "reconciled_average",
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
            "shares_out": 10.0,
            "net_debt": 50.0,
            "historical_series": {
                "ebit": {
                    "2023-12-31": 130.0,
                    "2024-12-31": 140.0,
                    "2025-12-31": 150.0,
                },
                "ocf": {
                    "2023-12-31": 100.0,
                    "2024-12-31": 110.0,
                    "2025-12-31": 120.0,
                },
                "da": {
                    "2023-12-31": 10.0,
                    "2024-12-31": 10.0,
                    "2025-12-31": 10.0,
                },
                "capex": {
                    "2023-12-31": 20.0,
                    "2024-12-31": 20.0,
                    "2025-12-31": 20.0,
                },
                "delta_nwc": {
                    "2023-12-31": 5.0,
                    "2024-12-31": 5.0,
                    "2025-12-31": 5.0,
                },
                "interest_paid": {
                    "2023-12-31": 10.0,
                    "2024-12-31": 10.0,
                    "2025-12-31": 10.0,
                },
            },
        },
    }

    out = run_valuation(payload)

    assert out.fcff.anchor == pytest.approx(97.5)
    assert out.fcff.anchor_method == "reconciled_average_of_cfo_and_ebiat_paths"
    assert out.fcff.selected_path == "reconciled"
    assert out.fcff.anchor_cfo_path == pytest.approx(98.0)
    assert out.fcff.anchor_ebiat_path == pytest.approx(97.0)
    assert out.fcff.anchor_mode == "reconciled_average"
    assert out.fcff.anchor_observation_count == 3
    assert out.fcff.reconciliation_gap == pytest.approx(1.0)
    assert out.fcff.reconciliation_gap_pct == pytest.approx(1.0 / 97.5)


def test_run_valuation_three_period_average_falls_back_to_latest_when_history_missing():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "fcff_anchor_mode": "three_period_average",
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
    assert out.fcff.selected_path == "ebiat"
    assert out.fcff.anchor_mode == "latest"
    assert out.fcff.anchor_observation_count == 1
    assert "fcff_anchor_mode_three_period_average_history_unavailable_fallback_to_latest" in out.warnings


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
    assert out.fcff.selected_path == "manual_anchor"
    assert out.fcff.anchor_mode == "manual"
    assert "stable_growth_rate_clamped_below_wacc" in out.warnings


def test_run_valuation_two_stage_accepts_stage1_aliases():
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

    out = run_valuation(payload)

    assert out.valuation_model == "two_stage"
    assert out.requested_valuation_model == "two_stage"
    assert out.effective_valuation_model == "two_stage"
    assert out.valuation.present_value_stage1 is not None
    assert out.valuation.present_value_terminal is not None
    assert out.valuation.explicit_forecast_years == 3
    assert "valuation_model_two_stage" in out.diagnostics


def test_run_valuation_preserves_provider_sources():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "_prefill_diagnostics": ["provider_normalization:yahoo:A"],
        "_prefill_warnings": ["yahoo_beta_unavailable_engine_default_will_apply"],
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "effective_tax_rate": 0.21,
            "effective_tax_rate_source": "yahoo:tax_rate",
            "marginal_tax_rate": 0.21,
            "marginal_tax_rate_source": "market_default",
            "risk_free_rate": 0.043,
            "risk_free_rate_source": "yahoo:^TNX",
            "equity_risk_premium": 0.05,
            "equity_risk_premium_source": "market_default",
            "pre_tax_cost_of_debt": 0.03,
            "pre_tax_cost_of_debt_source": "yahoo:interest_expense_over_total_debt",
            "equity_weight": 0.9,
            "debt_weight": 0.1,
            "capital_structure_source": "yahoo:market_value_using_total_debt",
            "terminal_growth_rate": 0.03,
        },
        "fundamentals": {
            "fcff_anchor": 100.0,
            "delta_nwc_source": "op_nwc_delta",
            "shares_out": 10.0,
            "net_debt": 0.0,
        },
    }

    out = run_valuation(payload)

    assert out.tax.effective_tax_rate_source == "yahoo:tax_rate"
    assert out.tax.marginal_tax_rate_source == "market_default"
    assert out.wacc_inputs.risk_free_rate_source == "yahoo:^TNX"
    assert out.wacc_inputs.pre_tax_cost_of_debt_source == "yahoo:interest_expense_over_total_debt"
    assert out.capital_structure.source == "yahoo:market_value_using_total_debt"
    assert out.fcff.selected_path == "manual_anchor"
    assert out.fcff.anchor_mode == "manual"
    assert "provider_normalization:yahoo:A" in out.diagnostics
    assert "yahoo_beta_unavailable_engine_default_will_apply" in out.warnings


def test_run_valuation_preserves_capital_structure_fallback_warning():
    payload = {
        "ticker": "TEST",
        "market": "US",
        "_prefill_warnings": ["yahoo_total_debt_unavailable_used_net_debt_for_capital_structure"],
        "valuation_model": "steady_state_single_stage",
        "assumptions": {
            "effective_tax_rate": 0.21,
            "marginal_tax_rate": 0.21,
            "risk_free_rate": 0.043,
            "equity_risk_premium": 0.05,
            "beta": 1.0,
            "pre_tax_cost_of_debt": 0.03,
            "equity_weight": 0.8,
            "debt_weight": 0.2,
            "capital_structure_source": "yahoo:market_value_using_net_debt_fallback",
            "terminal_growth_rate": 0.03,
        },
        "fundamentals": {
            "fcff_anchor": 100.0,
            "net_debt": 10.0,
            "shares_out": 10.0,
        },
    }

    out = run_valuation(payload)

    assert out.capital_structure.source == "yahoo:market_value_using_net_debt_fallback"
    assert "yahoo_total_debt_unavailable_used_net_debt_for_capital_structure" in out.warnings


def test_run_valuation_three_stage_basic():
    out = run_valuation(_three_stage_payload())

    assert out.requested_valuation_model == "three_stage"
    assert out.effective_valuation_model == "three_stage"
    assert out.valuation_model == "three_stage"
    assert out.degraded is False
    assert "valuation_model_three_stage" in out.diagnostics
    assert out.valuation.present_value_stage1 is not None
    assert out.valuation.present_value_stage2 is not None
    assert out.valuation.present_value_terminal is not None
    assert out.valuation.terminal_value is not None
    assert out.valuation.explicit_forecast_years == 5
    assert out.valuation.stage1_years == 3
    assert out.valuation.stage2_years == 2
    assert out.valuation.stage2_decay_mode == "linear"
    assert out.valuation.enterprise_value == pytest.approx(
        (out.valuation.present_value_stage1 or 0.0)
        + (out.valuation.present_value_stage2 or 0.0)
        + (out.valuation.present_value_terminal or 0.0)
    )


def test_run_valuation_three_stage_linear_decay_schedule():
    schedule, stage1_years, stage2_years, decay_mode = _build_three_stage_growth_schedule(
        stage1_growth_rate=0.10,
        stage1_years=2,
        stage2_end_growth_rate=0.04,
        stage2_years=3,
        stage2_decay_mode="linear",
    )

    assert stage1_years == 2
    assert stage2_years == 3
    assert decay_mode == "linear"
    assert schedule[:2] == pytest.approx([0.10, 0.10])
    assert schedule[2:] == pytest.approx([0.08, 0.06, 0.04])

    out = run_valuation(
        _three_stage_payload(
            stage1_growth_rate=0.10,
            stage1_years=2,
            stage2_end_growth_rate=0.04,
            stage2_years=3,
        )
    )

    assert out.valuation.explicit_forecast_years == 5


def test_run_valuation_three_stage_clamps_terminal_growth_below_wacc():
    out = run_valuation(
        _three_stage_payload(
            terminal_growth_rate=0.08,
            stage2_end_growth_rate=0.09,
        )
    )

    assert out.valuation.terminal_growth_rate == pytest.approx(0.08)
    assert out.valuation.terminal_growth_rate_effective is not None
    assert out.valuation.terminal_growth_rate_effective < out.wacc_inputs.wacc
    assert "terminal_growth_rate_clamped_below_wacc" in out.warnings


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"stage2_end_growth_rate": None}, "Missing assumptions.stage2_end_growth_rate"),
        ({"stage2_years": None}, "Missing assumptions.stage2_years"),
    ],
)
def test_run_valuation_three_stage_missing_required_params_errors(overrides, message):
    with pytest.raises(ValueError, match=message):
        run_valuation(_three_stage_payload(**overrides))


def test_run_valuation_unknown_model_errors():
    payload = _three_stage_payload()
    payload["valuation_model"] = "foo_bar"

    with pytest.raises(ValueError, match="unsupported valuation_model"):
        run_valuation(payload)
