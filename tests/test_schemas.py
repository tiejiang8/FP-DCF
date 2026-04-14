from fp_dcf import (
    MarketImpliedGrowthInput,
    MarketImpliedGrowthOutput,
    SensitivityHeatmapOutput,
    ValuationOutput,
    ValuationSummary,
)


def test_valuation_output_defaults_are_stable():
    result = ValuationOutput(
        ticker="AAPL",
        market="US",
        valuation_model="steady_state_single_stage",
    )

    assert result.ticker == "AAPL"
    assert result.market == "US"
    assert result.valuation_model == "steady_state_single_stage"
    assert result.requested_valuation_model is None
    assert result.effective_valuation_model is None
    assert result.degraded is False
    assert result.degradation_reasons == []
    assert result.tax.effective_tax_rate is None
    assert result.wacc_inputs.wacc is None
    assert result.capital_structure.equity_weight is None
    assert result.fcff.anchor is None
    assert result.valuation.enterprise_value is None
    assert result.market_implied_growth is None
    assert result.diagnostics == []
    assert result.warnings == []


def test_market_implied_growth_input_defaults_are_stable():
    result = MarketImpliedGrowthInput()

    assert result.enabled is False
    assert result.lower_bound == -0.5
    assert result.upper_bound == 0.5
    assert result.solver == "auto"
    assert result.tolerance == 1e-6
    assert result.max_iterations == 100


def test_market_implied_growth_output_serializes_fields():
    summary = MarketImpliedGrowthOutput(
        enabled=True,
        success=True,
        valuation_model="two_stage",
        solved_field="stage1_growth_rate",
        solved_value=0.1362,
        solver_used="bisection",
        lower_bound=0.0,
        upper_bound=0.4,
        iterations=37,
        residual=0.000001,
        market_price=258.86,
        market_enterprise_value=3867000000000.0,
        base_case_per_share_value=150.85,
        base_case_enterprise_value=3867000000000.0,
        message="Market-implied growth solved successfully.",
    )

    payload = summary.to_dict()

    assert payload["enabled"] is True
    assert payload["success"] is True
    assert payload["valuation_model"] == "two_stage"
    assert payload["solved_field"] == "stage1_growth_rate"
    assert payload["solver_used"] == "bisection"
    assert payload["solved_value"] == 0.1362
    assert payload["market_price"] == 258.86
    assert payload["base_case_per_share_value"] == 150.85


def test_sensitivity_heatmap_output_defaults_are_stable():
    result = SensitivityHeatmapOutput(
        ticker="AAPL",
        market="US",
        valuation_model="steady_state_single_stage",
        metric="per_share_value",
        metric_label="Per Share Value",
    )

    assert result.ticker == "AAPL"
    assert result.market == "US"
    assert result.metric == "per_share_value"
    assert result.base_wacc is None
    assert result.market_price is None
    assert result.wacc_values == []
    assert result.matrix == []
    assert result.diagnostics == []


def test_sensitivity_heatmap_summary_omits_grid_by_default():
    result = SensitivityHeatmapOutput(
        ticker="AAPL",
        market="US",
        valuation_model="steady_state_single_stage",
        metric="per_share_value",
        metric_label="Per Share Value",
        base_wacc=0.09,
        base_terminal_growth_rate=0.03,
        base_metric_value=100.0,
        market_price=110.0,
        wacc_values=[0.08, 0.09],
        terminal_growth_values=[0.02, 0.03],
        matrix=[[90.0, 100.0], [80.0, 90.0]],
        diagnostics=["a", "b"],
        warnings=["x"],
    )

    summary = result.to_summary_dict(exclude_diagnostics={"a"})

    assert "grid" not in summary
    assert summary["market_price"] == 110.0
    assert summary["wacc_axis"] == {"min": 0.08, "max": 0.09, "points": 2}
    assert summary["terminal_growth_axis"] == {"min": 0.02, "max": 0.03, "points": 2}
    assert summary["diagnostics"] == ["b"]


def test_valuation_summary_serializes_three_stage_fields():
    summary = ValuationSummary(
        enterprise_value=123.0,
        present_value_stage1=20.0,
        present_value_stage2=30.0,
        present_value_terminal=73.0,
        terminal_value=100.0,
        explicit_forecast_years=7,
        stage1_years=4,
        stage2_years=3,
        stage2_decay_mode="linear",
    )

    data = summary.__dict__ if hasattr(summary, "__dict__") else {
        "enterprise_value": summary.enterprise_value,
        "present_value_stage1": summary.present_value_stage1,
        "present_value_stage2": summary.present_value_stage2,
        "present_value_terminal": summary.present_value_terminal,
        "terminal_value": summary.terminal_value,
        "explicit_forecast_years": summary.explicit_forecast_years,
        "stage1_years": summary.stage1_years,
        "stage2_years": summary.stage2_years,
        "stage2_decay_mode": summary.stage2_decay_mode,
    }

    assert data["present_value_stage2"] == 30.0
    assert data["terminal_value"] == 100.0
    assert data["explicit_forecast_years"] == 7
    assert data["stage1_years"] == 4
    assert data["stage2_years"] == 3
    assert data["stage2_decay_mode"] == "linear"


def test_valuation_output_serializes_requested_and_effective_models():
    result = ValuationOutput(
        ticker="AAPL",
        market="US",
        valuation_model="three_stage",
        requested_valuation_model="three_stage",
        effective_valuation_model="three_stage",
        degraded=True,
        degradation_reasons=["degraded_due_to_default_capital_structure"],
        market_implied_growth=MarketImpliedGrowthOutput(
            enabled=True,
            success=True,
            valuation_model="three_stage",
            solved_field="stage1_growth_rate",
            solved_value=0.12,
            solver_used="bisection",
            lower_bound=-0.5,
            upper_bound=0.5,
            iterations=12,
            residual=0.0,
            market_price=123.0,
            market_enterprise_value=1000.0,
            base_case_per_share_value=10.0,
            base_case_enterprise_value=1000.0,
            message="Market-implied growth solved successfully.",
        ),
        valuation=ValuationSummary(
            present_value_stage2=12.0,
            terminal_value=34.0,
            explicit_forecast_years=5,
            stage1_years=3,
            stage2_years=2,
            stage2_decay_mode="linear",
        ),
    )

    payload = result.to_dict()

    assert payload["valuation_model"] == "three_stage"
    assert payload["requested_valuation_model"] == "three_stage"
    assert payload["effective_valuation_model"] == "three_stage"
    assert payload["degraded"] is True
    assert payload["degradation_reasons"] == ["degraded_due_to_default_capital_structure"]
    assert payload["market_implied_growth"]["enabled"] is True
    assert payload["market_implied_growth"]["solved_field"] == "stage1_growth_rate"
    assert payload["valuation"]["present_value_stage2"] == 12.0
    assert payload["valuation"]["terminal_value"] == 34.0
    assert payload["valuation"]["explicit_forecast_years"] == 5


def test_valuation_output_omits_market_implied_growth_when_absent():
    result = ValuationOutput(
        ticker="AAPL",
        market="US",
        valuation_model="two_stage",
    )

    payload = result.to_dict()

    assert "market_implied_growth" not in payload
