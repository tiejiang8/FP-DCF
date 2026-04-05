from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


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
    assert payload["valuation"]["enterprise_value"] > 0
