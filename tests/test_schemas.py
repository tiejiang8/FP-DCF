from fp_dcf import SensitivityHeatmapOutput, ValuationOutput, ValuationSummary


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
    assert result.tax.effective_tax_rate is None
    assert result.wacc_inputs.wacc is None
    assert result.capital_structure.equity_weight is None
    assert result.fcff.anchor is None
    assert result.valuation.enterprise_value is None
    assert result.diagnostics == []
    assert result.warnings == []


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
        wacc_values=[0.08, 0.09],
        terminal_growth_values=[0.02, 0.03],
        matrix=[[90.0, 100.0], [80.0, 90.0]],
        diagnostics=["a", "b"],
        warnings=["x"],
    )

    summary = result.to_summary_dict(exclude_diagnostics={"a"})

    assert "grid" not in summary
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
        degraded=False,
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
    assert payload["degraded"] is False
    assert payload["valuation"]["present_value_stage2"] == 12.0
    assert payload["valuation"]["terminal_value"] == 34.0
    assert payload["valuation"]["explicit_forecast_years"] == 5
