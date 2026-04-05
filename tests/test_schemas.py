from fp_dcf import ValuationOutput


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
