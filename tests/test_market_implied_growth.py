from __future__ import annotations

import pytest

from fp_dcf.market_implied_growth import (
    reject_removed_market_implied_blocks,
    resolve_market_implied_growth_input,
    resolve_market_inputs,
)


def test_resolve_market_implied_growth_input_defaults_when_enabled():
    request = resolve_market_implied_growth_input(
        {
            "market_implied_growth": {
                "enabled": True,
            }
        }
    )

    assert request is not None
    assert request.enabled is True
    assert request.lower_bound == -0.5
    assert request.upper_bound == 0.5
    assert request.solver == "auto"
    assert request.tolerance == 1e-6
    assert request.max_iterations == 100


def test_reject_removed_market_implied_blocks_raises_for_legacy_keys():
    with pytest.raises(ValueError, match="`implied_growth` has been removed"):
        reject_removed_market_implied_blocks({"implied_growth": {}})

    with pytest.raises(ValueError, match="`market_implied_stage1_growth` has been removed"):
        reject_removed_market_implied_blocks({"market_implied_stage1_growth": {}})


def test_resolve_market_inputs_derives_market_enterprise_value_from_price():
    summary = resolve_market_inputs(
        {
            "market_inputs": {
                "market_price": 9.5,
            },
            "fundamentals": {
                "shares_out": 100.0,
                "net_debt": 50.0,
            },
        }
    )

    assert summary.market_price == 9.5
    assert summary.shares_out == 100.0
    assert summary.net_debt == 50.0
    assert summary.equity_value_market == pytest.approx(950.0)
    assert summary.enterprise_value_market == pytest.approx(1000.0)
    assert summary.enterprise_value_market_source == "derived_from_market_price_shares_out_and_net_debt"
