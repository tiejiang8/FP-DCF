from __future__ import annotations

from contextlib import contextmanager

import pytest


@contextmanager
def _noop_session():
    yield


def test_fetch_akshare_baostock_snapshot_exposes_cn_fundamentals_and_weights(monkeypatch):
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
    balance_sheet = pd.DataFrame(
        [
            {
                "报告日": report_date,
                "类型": "合并期末",
                "货币资金": 80.0,
                "短期借款": 20.0,
                "长期借款": 80.0,
                "流动资产合计": 200.0,
                "流动负债合计": 120.0,
                "交易性金融资产": 10.0,
            }
        ]
    )
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
    stock_info = pd.DataFrame(
        [
            {"item": "总股本", "value": 10.0},
            {"item": "股票代码", "value": "600519"},
        ]
    )

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

    snapshot = provider.fetch_akshare_baostock_snapshot("600519.SH", market="CN", statement_frequency="A")

    assert snapshot["provider"] == "akshare_baostock"
    assert snapshot["normalized_symbol"] == "600519.SH"
    assert snapshot["currency"] == "CNY"
    assert snapshot["fundamentals"]["ebit"] == 100.0
    assert snapshot["fundamentals"]["ocf"] == 120.0
    assert snapshot["fundamentals"]["interest_paid"] == 9.0
    assert snapshot["fundamentals"]["interest_expense"] == 10.0
    assert snapshot["fundamentals"]["total_debt"] == 100.0
    assert snapshot["fundamentals"]["net_debt"] == 20.0
    assert snapshot["fundamentals"]["shares_out"] == 10.0
    assert snapshot["assumptions"]["risk_free_rate"] == 0.025
    assert snapshot["assumptions"]["beta"] == 1.1
    assert snapshot["assumptions"]["pre_tax_cost_of_debt"] == pytest.approx(0.1)
    assert snapshot["assumptions"]["equity_weight"] == pytest.approx(1000.0 / 1100.0)
    assert snapshot["assumptions"]["debt_weight"] == pytest.approx(100.0 / 1100.0)
    assert snapshot["assumptions"]["capital_structure_source"] == "akshare_baostock:market_value_using_total_debt"


def test_fetch_akshare_baostock_snapshot_rejects_non_cn_market():
    from fp_dcf.providers import akshare_baostock as provider

    with pytest.raises(ValueError, match="market=CN only"):
        provider.fetch_akshare_baostock_snapshot("AAPL", market="US", statement_frequency="A")


def test_fetch_akshare_baostock_snapshot_falls_back_to_share_capital_when_stock_info_unavailable(monkeypatch):
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
    balance_sheet = pd.DataFrame(
        [
            {
                "报告日": report_date,
                "类型": "合并期末",
                "货币资金": 80.0,
                "短期借款": 20.0,
                "长期借款": 80.0,
                "流动资产合计": 200.0,
                "流动负债合计": 120.0,
                "交易性金融资产": 10.0,
                "实收资本(或股本)": 10.0,
            }
        ]
    )
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
            raise RuntimeError("upstream disconnected")

    monkeypatch.setattr(provider, "ak", FakeAk)

    snapshot = provider.fetch_akshare_baostock_snapshot("600519.SH", market="CN", statement_frequency="A")

    assert snapshot["fundamentals"]["shares_out"] == 10.0


def test_akshare_baostock_enrich_warns_when_capital_structure_falls_back_to_net_debt():
    from fp_dcf.providers.akshare_baostock import enrich_payload_from_akshare_baostock

    out = enrich_payload_from_akshare_baostock(
        {"ticker": "600519.SH", "market": "CN"},
        snapshot={
            "provider": "akshare_baostock",
            "normalized_symbol": "600519.SH",
            "fundamentals": {"net_debt": 30.0},
            "assumptions": {
                "equity_weight": 0.7692307692,
                "debt_weight": 0.2307692308,
                "capital_structure_source": "akshare_baostock:market_value_using_net_debt_fallback",
            },
        },
    )

    assert out["assumptions"]["capital_structure_source"] == "akshare_baostock:market_value_using_net_debt_fallback"
    assert (
        "akshare_baostock_total_debt_unavailable_used_net_debt_for_capital_structure"
        in out["_prefill_warnings"]
    )
