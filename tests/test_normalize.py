from __future__ import annotations

from contextlib import contextmanager
import sys
import types
from pathlib import Path

import pytest

from fp_dcf import normalize_payload


@contextmanager
def _noop_session():
    yield


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


def _install_fake_akshare_baostock_provider(fetch_values: list[dict] | None = None):
    fake_provider = types.ModuleType("fp_dcf.providers.akshare_baostock")
    state = {"fetch_calls": 0}

    def fake_fetch(ticker_symbol, *, market="CN", statement_frequency="A"):
        state["fetch_calls"] += 1
        if fetch_values:
            snapshot = fetch_values[min(state["fetch_calls"] - 1, len(fetch_values) - 1)]
        else:
            snapshot = {
                "provider": "akshare_baostock",
                "normalized_symbol": str(ticker_symbol).upper(),
                "assumptions": {"risk_free_rate": 0.025, "beta": 0.9},
                "fundamentals": {"ebit": 120.0},
            }
        out = dict(snapshot)
        out.setdefault("provider", "akshare_baostock")
        out.setdefault("normalized_symbol", str(ticker_symbol).upper())
        out.setdefault("assumptions", {})
        out.setdefault("fundamentals", {})
        return out

    def fake_enrich(payload, *, snapshot=None):
        out = dict(payload)
        provider_snapshot = snapshot or fake_fetch(payload.get("ticker"))
        out["provider"] = provider_snapshot.get("provider", "akshare_baostock")
        out["normalized_symbol"] = provider_snapshot.get("normalized_symbol")
        out["assumptions"] = dict(provider_snapshot.get("assumptions", {}))
        out["fundamentals"] = dict(provider_snapshot.get("fundamentals", {}))
        out["_prefill_diagnostics"] = [
            f"provider_normalization:akshare_baostock:{payload.get('statement_frequency', 'A')}"
        ]
        return out

    fake_provider.fetch_akshare_baostock_snapshot = fake_fetch
    fake_provider.enrich_payload_from_akshare_baostock = fake_enrich
    sys.modules["fp_dcf.providers.akshare_baostock"] = fake_provider
    return state


def _patch_real_akshare_baostock_provider(
    monkeypatch,
    *,
    stock_info_rows: list[dict] | None = None,
    balance_sheet_fields: dict | None = None,
):
    pd = pytest.importorskip("pandas")

    from fp_dcf.providers import akshare_baostock as provider

    report_date = pd.Timestamp("2025-12-31")
    income_statement = pd.DataFrame(
        [
            {
                "报告日": report_date,
                "类型": "合并期末",
                "营业利润": 100.0,
                "利息费用": 10.0,
                "利润总额": 100.0,
                "所得税费用": 20.0,
            }
        ]
    )
    balance_row = {
        "报告日": report_date,
        "类型": "合并期末",
        "货币资金": 80.0,
        "短期借款": 20.0,
        "长期借款": 80.0,
        "流动资产合计": 200.0,
        "流动负债合计": 120.0,
        "交易性金融资产": 10.0,
    }
    if balance_sheet_fields:
        balance_row.update(balance_sheet_fields)
    balance_sheet = pd.DataFrame([balance_row])
    cash_flow_statement = pd.DataFrame(
        [
            {
                "报告日": report_date,
                "类型": "合并期末",
                "经营活动产生的现金流量净额": 120.0,
                "购建固定资产、无形资产和其他长期资产所支付的现金": 18.0,
                "支付利息、手续费及佣金的现金": 9.0,
            }
        ]
    )
    stock_info = pd.DataFrame(stock_info_rows or [])

    monkeypatch.setattr(provider, "pd", pd)
    monkeypatch.setattr(provider, "bs", object())
    monkeypatch.setattr(provider, "np", object())
    monkeypatch.setattr(provider, "_baostock_session", _noop_session)
    monkeypatch.setattr(provider, "_latest_close", lambda symbol: 100.0)
    monkeypatch.setattr(provider, "_compute_beta", lambda symbol, benchmark: 1.1)

    class FakeAk:
        @staticmethod
        def stock_financial_report_sina(*, stock: str, symbol: str):
            if symbol == "利润表":
                return income_statement
            if symbol == "资产负债表":
                return balance_sheet
            if symbol == "现金流量表":
                return cash_flow_statement
            raise AssertionError(symbol)

        @staticmethod
        def stock_individual_info_em(*, symbol: str):
            assert symbol == "600519"
            return stock_info

    monkeypatch.setattr(provider, "ak", FakeAk)
    return provider


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


def test_normalize_payload_supports_explicit_akshare_baostock_provider(tmp_path: Path):
    _install_fake_akshare_baostock_provider()
    try:
        out = normalize_payload(
            {"ticker": "600519.SH", "market": "CN", "provider": "akshare_baostock"},
            cache_dir=tmp_path,
        )
    finally:
        sys.modules.pop("fp_dcf.providers.akshare_baostock", None)

    assert out["provider"] == "akshare_baostock"
    assert out["assumptions"]["risk_free_rate"] == 0.025
    assert out["fundamentals"]["ebit"] == 120.0
    assert "provider_normalization:akshare_baostock:A" in out["_prefill_diagnostics"]
    assert "provider_cache_miss:akshare_baostock" in out["_prefill_diagnostics"]


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


def test_normalize_payload_falls_back_from_yahoo_to_akshare_baostock_for_cn(tmp_path: Path):
    fake_yahoo = types.ModuleType("fp_dcf.providers.yahoo")

    def fake_fetch_yahoo(ticker_symbol, *, market="CN", statement_frequency="A"):
        raise RuntimeError("yfinance unreachable")

    fake_yahoo.fetch_yahoo_snapshot = fake_fetch_yahoo
    fake_yahoo.enrich_payload_from_yahoo = lambda payload, *, snapshot=None: payload
    sys.modules["fp_dcf.providers.yahoo"] = fake_yahoo
    _install_fake_akshare_baostock_provider()
    try:
        out = normalize_payload({"ticker": "600519.SH", "market": "CN"}, cache_dir=tmp_path)
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)
        sys.modules.pop("fp_dcf.providers.akshare_baostock", None)

    assert out["provider"] == "akshare_baostock"
    assert "provider_fallback:yahoo->akshare_baostock" in out["_prefill_diagnostics"]
    assert "provider_cache_miss:akshare_baostock" in out["_prefill_diagnostics"]
    assert "yahoo_unavailable_used_akshare_baostock_fallback" in out["_prefill_warnings"]


def test_normalize_payload_does_not_fall_back_from_yahoo_for_us(tmp_path: Path):
    fake_yahoo = types.ModuleType("fp_dcf.providers.yahoo")

    def fake_fetch_yahoo(ticker_symbol, *, market="US", statement_frequency="A"):
        raise RuntimeError("yfinance unreachable")

    fake_yahoo.fetch_yahoo_snapshot = fake_fetch_yahoo
    fake_yahoo.enrich_payload_from_yahoo = lambda payload, *, snapshot=None: payload
    sys.modules["fp_dcf.providers.yahoo"] = fake_yahoo
    try:
        with pytest.raises(RuntimeError, match="yfinance unreachable"):
            normalize_payload({"ticker": "AAPL", "market": "US"}, cache_dir=tmp_path)
    finally:
        sys.modules.pop("fp_dcf.providers.yahoo", None)


@pytest.mark.parametrize(
    ("item_name", "raw_value", "expected_shares_out", "expected_unit"),
    [
        ("总股本", 10.0, 10.0, "股"),
        ("总股本(万股)", 10.0, 100000.0, "万股"),
        ("总股本（亿股）", 10.0, 1000000000.0, "亿股"),
    ],
)
def test_akshare_baostock_resolves_shares_out_from_stock_info_aliases(
    monkeypatch,
    item_name,
    raw_value,
    expected_shares_out,
    expected_unit,
):
    provider = _patch_real_akshare_baostock_provider(
        monkeypatch,
        stock_info_rows=[{"item": item_name, "value": raw_value}],
    )

    snapshot = provider.fetch_akshare_baostock_snapshot("600519.SH", market="CN", statement_frequency="A")

    assert snapshot["fundamentals"]["shares_out"] == pytest.approx(expected_shares_out)
    assert snapshot["fundamentals"]["shares_out_source"] == "akshare:stock_individual_info_em"
    assert snapshot["fundamentals"]["shares_out_raw_field"] == item_name
    assert snapshot["fundamentals"]["shares_out_raw_unit"] == expected_unit


@pytest.mark.parametrize("field_name", ["股本", "实收资本(或股本)"])
def test_akshare_baostock_falls_back_to_balance_sheet_share_capital(monkeypatch, field_name):
    provider = _patch_real_akshare_baostock_provider(
        monkeypatch,
        stock_info_rows=[],
        balance_sheet_fields={field_name: 10.0},
    )

    snapshot = provider.fetch_akshare_baostock_snapshot("600519.SH", market="CN", statement_frequency="A")

    assert snapshot["fundamentals"]["shares_out"] == 10.0
    assert snapshot["fundamentals"]["shares_out_source"] == "akshare:balance_sheet_share_capital"
    assert snapshot["fundamentals"]["shares_out_raw_field"] == field_name
    assert snapshot["fundamentals"]["shares_out_raw_unit"] == "股"


def test_akshare_baostock_marks_shares_out_unresolved_when_all_paths_fail(monkeypatch):
    provider = _patch_real_akshare_baostock_provider(
        monkeypatch,
        stock_info_rows=[],
        balance_sheet_fields={},
    )

    snapshot = provider.fetch_akshare_baostock_snapshot("600519.SH", market="CN", statement_frequency="A")
    out = provider.enrich_payload_from_akshare_baostock(
        {"ticker": "600519.SH", "market": "CN"},
        snapshot=snapshot,
    )

    assert snapshot["fundamentals"]["shares_out"] is None
    assert "shares_out_unresolved_akshare_baostock" in snapshot["diagnostics"]
    assert "shares_out_unresolved_akshare_baostock" in out["_prefill_diagnostics"]
    assert (
        "capital_structure_source_unavailable_due_to_missing_shares_out"
        in out["_prefill_diagnostics"]
    )


def test_yahoo_snapshot_uses_total_debt_for_capital_structure_weights(monkeypatch):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("yfinance")

    from fp_dcf.providers import yahoo

    report_date = pd.Timestamp("2025-12-31")

    class FakeTicker:
        financials = pd.DataFrame(
            {
                report_date: {
                    "Operating Income": 100.0,
                    "Tax Provision": 20.0,
                    "Income Before Tax": 100.0,
                    "Interest Expense": 10.0,
                }
            }
        )
        balance_sheet = pd.DataFrame(
            {
                report_date: {
                    "Cash And Cash Equivalents": 80.0,
                    "Total Debt": 100.0,
                    "Total Current Assets": 200.0,
                    "Total Current Liabilities": 120.0,
                    "Current Debt": 20.0,
                    "Short Term Investments": 10.0,
                }
            }
        )
        cashflow = pd.DataFrame(
            {
                report_date: {
                    "Operating Cash Flow": 120.0,
                    "Depreciation And Amortization": 12.0,
                    "Capital Expenditures": -18.0,
                    "Interest Paid Supplemental Data": 9.0,
                }
            }
        )
        quarterly_financials = pd.DataFrame()
        quarterly_balance_sheet = pd.DataFrame()
        quarterly_cashflow = pd.DataFrame()
        fast_info = {"shares": 10.0, "lastPrice": 10.0}

        def get_shares_full(self, start=None, end=None):
            return pd.Series([10.0], index=[report_date])

        def history(self, period="1mo", interval="1d", auto_adjust=False):
            return pd.DataFrame({"Adj Close": [10.0]}, index=[report_date])

        def get_info(self):
            return {"currency": "USD"}

    monkeypatch.setattr(yahoo.yf, "Ticker", lambda symbol: FakeTicker())
    monkeypatch.setattr(yahoo, "_fetch_riskfree_rate", lambda market: (0.04, "yahoo:^TNX"))
    monkeypatch.setattr(yahoo, "_compute_beta", lambda symbol, benchmark: 1.1)

    snapshot = yahoo.fetch_yahoo_snapshot("TEST", market="US", statement_frequency="A")

    assert snapshot["fundamentals"]["net_debt"] == 20.0
    assert snapshot["assumptions"]["equity_weight"] == pytest.approx(0.5)
    assert snapshot["assumptions"]["debt_weight"] == pytest.approx(0.5)
    assert snapshot["assumptions"]["capital_structure_source"] == "yahoo:market_value_using_total_debt"


def test_yahoo_enrich_warns_when_capital_structure_falls_back_to_net_debt():
    from fp_dcf.providers.yahoo import enrich_payload_from_yahoo

    out = enrich_payload_from_yahoo(
        {"ticker": "TEST", "market": "US"},
        snapshot={
            "provider": "yahoo",
            "normalized_symbol": "TEST",
            "fundamentals": {"net_debt": 30.0},
            "assumptions": {
                "equity_weight": 0.7692307692,
                "debt_weight": 0.2307692308,
                "capital_structure_source": "yahoo:market_value_using_net_debt_fallback",
            },
        },
    )

    assert out["assumptions"]["capital_structure_source"] == "yahoo:market_value_using_net_debt_fallback"
    assert "yahoo_total_debt_unavailable_used_net_debt_for_capital_structure" in out["_prefill_warnings"]
