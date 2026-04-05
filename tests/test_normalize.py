from __future__ import annotations

import sys
import types
from pathlib import Path

from fp_dcf import normalize_payload


def _install_fake_yahoo_provider(fetch_values: list[dict] | None = None):
    fake_provider = types.ModuleType("fp_dcf.providers.yahoo")
    state = {"fetch_calls": 0}

    def fake_fetch(ticker_symbol, *, market="US", statement_frequency="A"):
        state["fetch_calls"] += 1
        if fetch_values:
            snapshot = fetch_values[min(state["fetch_calls"] - 1, len(fetch_values) - 1)]
        else:
            snapshot = {
                "provider": "yahoo",
                "normalized_symbol": str(ticker_symbol).upper(),
                "assumptions": {"risk_free_rate": 0.04, "beta": 1.1},
                "fundamentals": {"ebit": 100.0},
            }
        out = dict(snapshot)
        out.setdefault("provider", "yahoo")
        out.setdefault("normalized_symbol", str(ticker_symbol).upper())
        out.setdefault("assumptions", {})
        out.setdefault("fundamentals", {})
        return out

    def fake_enrich(payload, *, snapshot=None):
        out = dict(payload)
        provider_snapshot = snapshot or fake_fetch(payload.get("ticker"))
        out["provider"] = provider_snapshot.get("provider", "yahoo")
        out["normalized_symbol"] = provider_snapshot.get("normalized_symbol")
        out["assumptions"] = dict(provider_snapshot.get("assumptions", {}))
        out["fundamentals"] = dict(provider_snapshot.get("fundamentals", {}))
        out["_prefill_diagnostics"] = [f"provider_normalization:yahoo:{payload.get('statement_frequency', 'A')}"]
        return out

    fake_provider.fetch_yahoo_snapshot = fake_fetch
    fake_provider.enrich_payload_from_yahoo = fake_enrich
    sys.modules["fp_dcf.providers.yahoo"] = fake_provider
    return state


def test_normalize_payload_uses_yahoo_provider_when_core_inputs_missing(tmp_path: Path):
    _install_fake_yahoo_provider()
    try:
        out = normalize_payload({"ticker": "AAPL", "market": "US"}, cache_dir=tmp_path)
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)

    assert out["provider"] == "yahoo"
    assert out["assumptions"]["risk_free_rate"] == 0.04
    assert out["fundamentals"]["ebit"] == 100.0
    assert "provider_normalization:yahoo:A" in out["_prefill_diagnostics"]
    assert "provider_cache_miss:yahoo" in out["_prefill_diagnostics"]


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


def test_normalize_payload_uses_provider_cache_by_default(tmp_path: Path):
    state = _install_fake_yahoo_provider(
        fetch_values=[
            {
                "provider": "yahoo",
                "normalized_symbol": "AAPL",
                "assumptions": {"risk_free_rate": 0.04, "beta": 1.1},
                "fundamentals": {"ebit": 100.0},
            },
            {
                "provider": "yahoo",
                "normalized_symbol": "AAPL",
                "assumptions": {"risk_free_rate": 0.05, "beta": 1.2},
                "fundamentals": {"ebit": 200.0},
            },
        ]
    )
    payload = {"ticker": "AAPL", "market": "US"}
    try:
        out_first = normalize_payload(payload, cache_dir=tmp_path)
        out_second = normalize_payload(payload, cache_dir=tmp_path)
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)

    assert state["fetch_calls"] == 1
    assert out_first["fundamentals"]["ebit"] == 100.0
    assert out_second["fundamentals"]["ebit"] == 100.0
    assert "provider_cache_miss:yahoo" in out_first["_prefill_diagnostics"]
    assert "provider_cache_hit:yahoo" in out_second["_prefill_diagnostics"]


def test_normalize_payload_force_refresh_bypasses_cached_snapshot(tmp_path: Path):
    state = _install_fake_yahoo_provider(
        fetch_values=[
            {
                "provider": "yahoo",
                "normalized_symbol": "AAPL",
                "assumptions": {"risk_free_rate": 0.04, "beta": 1.1},
                "fundamentals": {"ebit": 100.0},
            },
            {
                "provider": "yahoo",
                "normalized_symbol": "AAPL",
                "assumptions": {"risk_free_rate": 0.05, "beta": 1.2},
                "fundamentals": {"ebit": 200.0},
            },
        ]
    )
    payload = {"ticker": "AAPL", "market": "US"}
    try:
        out_first = normalize_payload(payload, cache_dir=tmp_path)
        out_second = normalize_payload(payload, cache_dir=tmp_path, force_refresh=True)
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)

    assert state["fetch_calls"] == 2
    assert out_first["fundamentals"]["ebit"] == 100.0
    assert out_second["fundamentals"]["ebit"] == 200.0
    assert "provider_cache_refresh:yahoo" in out_second["_prefill_diagnostics"]
