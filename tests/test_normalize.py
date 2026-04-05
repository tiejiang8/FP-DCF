from __future__ import annotations

import sys
import types

from fp_dcf import normalize_payload


def test_normalize_payload_uses_yahoo_provider_when_core_inputs_missing():
    fake_provider = types.ModuleType("fp_dcf.providers.yahoo")

    def fake_enrich(payload):
        out = dict(payload)
        out["provider"] = "yahoo"
        out["assumptions"] = {"risk_free_rate": 0.04, "beta": 1.1}
        out["fundamentals"] = {"ebit": 100.0}
        out["_prefill_diagnostics"] = ["provider_normalization:yahoo:A"]
        return out

    fake_provider.enrich_payload_from_yahoo = fake_enrich
    sys.modules["fp_dcf.providers.yahoo"] = fake_provider
    try:
        out = normalize_payload({"ticker": "AAPL", "market": "US"})
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)

    assert out["provider"] == "yahoo"
    assert out["assumptions"]["risk_free_rate"] == 0.04
    assert out["fundamentals"]["ebit"] == 100.0
    assert "provider_normalization:yahoo:A" in out["_prefill_diagnostics"]


def test_normalize_payload_skips_provider_when_core_inputs_present():
    payload = {
        "ticker": "AAPL",
        "market": "US",
        "assumptions": {
            "risk_free_rate": 0.04,
            "equity_risk_premium": 0.05,
            "beta": 1.0,
            "pre_tax_cost_of_debt": 0.03,
        },
        "fundamentals": {"ebit": 100.0},
    }

    out = normalize_payload(payload)

    assert out == payload
