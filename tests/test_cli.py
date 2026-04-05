from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_cli_runs_against_sample_input(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    input_path = repo_root / "examples" / "sample_input.json"
    output_path = tmp_path / "out.json"

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
    assert payload["valuation_model"] == "steady_state_single_stage"
    assert payload["valuation"]["enterprise_value"] > 0
