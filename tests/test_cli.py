from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fp_dcf import cli


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


def test_cli_passes_cache_options_to_normalizer(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text('{"ticker":"AAPL","market":"US"}', encoding="utf-8")

    calls = {}

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        calls["provider_override"] = provider_override
        calls["cache_dir"] = cache_dir
        calls["force_refresh"] = force_refresh
        return payload

    class _FakeResult:
        def to_dict(self):
            return {
                "ticker": "AAPL",
                "valuation_model": "steady_state_single_stage",
                "valuation": {"enterprise_value": 1.0},
            }

    monkeypatch.setattr(cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(cli, "run_valuation", lambda payload: _FakeResult())

    rc = cli.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--provider",
            "yahoo",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--refresh-provider",
        ]
    )

    assert rc == 0
    assert calls == {
        "provider_override": "yahoo",
        "cache_dir": str(tmp_path / "cache"),
        "force_refresh": True,
    }
