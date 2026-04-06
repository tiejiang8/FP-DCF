from __future__ import annotations

import json
from pathlib import Path

import pytest

from fp_dcf import cli
from fp_dcf.implied_growth import (
    build_implied_growth_output,
    solve_one_stage_implied_growth,
    solve_two_stage_implied_high_growth_rate,
)


def test_one_stage_implied_growth_closed_form_solver():
    implied_growth_rate = solve_one_stage_implied_growth(
        fcff_anchor=100.0,
        wacc=0.10,
        enterprise_value_market=1600.0,
    )

    assert implied_growth_rate == pytest.approx(0.0352941176)


def test_two_stage_implied_high_growth_rate_bisection_solver():
    fcff_anchor = 100.0
    wacc = 0.10
    stable_growth_rate = 0.03
    high_growth_years = 5
    expected_high_growth_rate = 0.12

    fcff_t = fcff_anchor
    enterprise_value_market = 0.0
    for year in range(1, high_growth_years + 1):
        fcff_t = fcff_t * (1.0 + expected_high_growth_rate)
        enterprise_value_market += fcff_t / ((1.0 + wacc) ** year)
    terminal_value = (fcff_t * (1.0 + stable_growth_rate)) / (wacc - stable_growth_rate)
    enterprise_value_market += terminal_value / ((1.0 + wacc) ** high_growth_years)

    implied_high_growth_rate, iterations = solve_two_stage_implied_high_growth_rate(
        fcff_anchor=fcff_anchor,
        wacc=wacc,
        enterprise_value_market=enterprise_value_market,
        stable_growth_rate=stable_growth_rate,
        high_growth_years=high_growth_years,
        lower_bound=0.0,
        upper_bound=0.2,
    )

    assert implied_high_growth_rate == pytest.approx(expected_high_growth_rate, abs=1e-5)
    assert iterations > 0


def test_build_implied_growth_output_derives_market_enterprise_value():
    payload = {
        "fundamentals": {
            "shares_out": 100.0,
            "net_debt": 50.0,
        },
        "market_inputs": {
            "market_price": 9.5,
        },
        "implied_growth": {},
    }
    valuation_result = {
        "fcff": {"anchor": 100.0},
        "wacc_inputs": {"wacc": 0.10},
        "valuation": {"terminal_growth_rate_effective": 0.03},
    }

    market_inputs, implied_growth = build_implied_growth_output(payload, valuation_result)

    assert market_inputs.enterprise_value_market == 1000.0
    assert market_inputs.enterprise_value_market_source == "derived_from_market_price_shares_out_and_net_debt"
    assert implied_growth.model == "one_stage"
    assert implied_growth.one_stage is not None
    assert implied_growth.one_stage["growth_rate"] == pytest.approx(0.0)
    assert implied_growth.two_stage is None


def test_build_implied_growth_output_returns_nested_two_stage_contract():
    fcff_anchor = 100.0
    wacc = 0.10
    stable_growth_rate = 0.03
    high_growth_years = 5
    expected_high_growth_rate = 0.12

    fcff_t = fcff_anchor
    enterprise_value_market = 0.0
    for year in range(1, high_growth_years + 1):
        fcff_t = fcff_t * (1.0 + expected_high_growth_rate)
        enterprise_value_market += fcff_t / ((1.0 + wacc) ** year)
    terminal_value = (fcff_t * (1.0 + stable_growth_rate)) / (wacc - stable_growth_rate)
    enterprise_value_market += terminal_value / ((1.0 + wacc) ** high_growth_years)

    payload = {
        "market_inputs": {
            "enterprise_value_market": enterprise_value_market,
        },
        "implied_growth": {
            "model": "two_stage",
            "high_growth_years": high_growth_years,
            "stable_growth_rate": stable_growth_rate,
            "lower_bound": 0.0,
            "upper_bound": 0.2,
        },
    }
    valuation_result = {
        "fcff": {"anchor": fcff_anchor},
        "wacc_inputs": {"wacc": wacc},
        "valuation": {"terminal_growth_rate_effective": stable_growth_rate},
    }

    market_inputs, implied_growth = build_implied_growth_output(payload, valuation_result)

    assert market_inputs.enterprise_value_market == pytest.approx(enterprise_value_market)
    assert implied_growth.model == "two_stage"
    assert implied_growth.one_stage is None
    assert implied_growth.two_stage is not None
    assert implied_growth.two_stage["high_growth_rate"] == pytest.approx(expected_high_growth_rate, abs=1e-5)
    assert implied_growth.two_stage["high_growth_years"] == high_growth_years
    assert implied_growth.two_stage["terminal_growth_rate"] == stable_growth_rate


def test_cli_embeds_implied_growth_result(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text(
        json.dumps(
            {
                "ticker": "AAPL",
                "market": "US",
                "market_inputs": {
                    "market_price": 9.5,
                },
                "implied_growth": {
                    "model": "one_stage",
                },
                "fundamentals": {
                    "shares_out": 100.0,
                    "net_debt": 50.0,
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        return payload

    class _FakeResult:
        def to_dict(self):
            return {
                "ticker": "AAPL",
                "market": "US",
                "valuation_model": "steady_state_single_stage",
                "fcff": {"anchor": 100.0},
                "wacc_inputs": {"wacc": 0.10},
                "valuation": {"enterprise_value": 1.0, "terminal_growth_rate_effective": 0.03},
                "diagnostics": [],
                "warnings": [],
            }

    monkeypatch.setattr(cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(cli, "run_valuation", lambda payload: _FakeResult())

    rc = cli.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--no-sensitivity",
            "--pretty",
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["market_inputs"]["enterprise_value_market"] == 1000.0
    assert payload["implied_growth"]["model"] == "one_stage"
    assert payload["implied_growth"]["solver"] == "closed_form"
    assert payload["implied_growth"]["one_stage"]["growth_rate"] == pytest.approx(0.0)
    assert payload["implied_growth"]["two_stage"] is None


def test_cli_skips_implied_growth_when_market_inputs_are_missing(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text(
        json.dumps(
            {
                "ticker": "AAPL",
                "market": "US",
                "implied_growth": {
                    "model": "one_stage",
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        return payload

    class _FakeResult:
        def to_dict(self):
            return {
                "ticker": "AAPL",
                "market": "US",
                "valuation_model": "steady_state_single_stage",
                "fcff": {"anchor": 100.0},
                "wacc_inputs": {"wacc": 0.10},
                "valuation": {"enterprise_value": 1.0, "terminal_growth_rate_effective": 0.03},
                "diagnostics": [],
                "warnings": [],
            }

    monkeypatch.setattr(cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(cli, "run_valuation", lambda payload: _FakeResult())

    rc = cli.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--no-sensitivity",
            "--pretty",
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "market_inputs" not in payload
    assert "implied_growth" not in payload
