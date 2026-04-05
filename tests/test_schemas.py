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
