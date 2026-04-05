from fp_dcf import SensitivityHeatmapOutput, ValuationOutput


def test_valuation_output_defaults_are_stable():
    result = ValuationOutput(
        ticker="AAPL",
        market="US",
        valuation_model="steady_state_single_stage",
    )

    assert result.ticker == "AAPL"
    assert result.market == "US"
    assert result.valuation_model == "steady_state_single_stage"
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
