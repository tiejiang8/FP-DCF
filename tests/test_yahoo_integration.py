from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_fetch_yahoo_snapshot_exposes_ocf_and_interest_paid(monkeypatch):
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
                    "Interest Expense": 15.0,
                }
            }
        )
        balance_sheet = pd.DataFrame(
            {
                report_date: {
                    "Cash And Cash Equivalents": 40.0,
                    "Total Debt": 80.0,
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
                    "Interest Paid Supplemental Data": 14.0,
                }
            }
        )
        quarterly_financials = pd.DataFrame()
        quarterly_balance_sheet = pd.DataFrame()
        quarterly_cashflow = pd.DataFrame()
        fast_info = {"shares": 10.0, "lastPrice": 25.0}

        def get_shares_full(self, start=None, end=None):
            return pd.Series([10.0], index=[report_date])

        def history(self, period="1mo", interval="1d", auto_adjust=False):
            return pd.DataFrame({"Adj Close": [25.0]}, index=[report_date])

        def get_info(self):
            return {"currency": "USD"}

    monkeypatch.setattr(yahoo.yf, "Ticker", lambda symbol: FakeTicker())
    monkeypatch.setattr(yahoo, "_fetch_riskfree_rate", lambda market: (0.04, "yahoo:^TNX"))
    monkeypatch.setattr(yahoo, "_compute_beta", lambda symbol, benchmark: 1.1)

    snapshot = yahoo.fetch_yahoo_snapshot("TEST", market="US", statement_frequency="A")

    assert snapshot["fundamentals"]["ocf"] == 120.0
    assert snapshot["fundamentals"]["interest_paid"] == 14.0
    assert snapshot["fundamentals"]["interest_expense"] == 15.0


@pytest.mark.integration
def test_yahoo_provider_live_smoke(tmp_path: Path):
    if os.getenv("FP_DCF_RUN_YAHOO_TESTS") != "1":
        pytest.skip("Set FP_DCF_RUN_YAHOO_TESTS=1 to run live Yahoo integration tests.")

    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text(
        json.dumps(
            {
                "ticker": "AAPL",
                "market": "US",
                "provider": "yahoo",
                "statement_frequency": "A",
                "valuation_model": "steady_state_single_stage",
                "assumptions": {
                    "terminal_growth_rate": 0.03,
                },
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "run_dcf.py"),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--pretty",
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "AAPL"
    assert payload["market"] == "US"
    assert payload["diagnostics"][0].startswith("provider_normalization:yahoo:")
    assert payload["wacc_inputs"]["risk_free_rate"] is not None
    assert payload["wacc_inputs"]["beta"] is not None
    assert payload["fcff"]["anchor"] is not None
    assert payload["fcff"]["selected_path"] in {"cfo", "ebiat", "manual_anchor"}
    assert "anchor_ebiat_path" in payload["fcff"]
    assert "anchor_cfo_path" in payload["fcff"]
    assert payload["valuation"]["enterprise_value"] > 0
