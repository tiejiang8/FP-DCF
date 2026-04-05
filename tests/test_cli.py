from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fp_dcf import cli
from fp_dcf import SensitivityHeatmapOutput


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


def test_cli_embeds_sensitivity_and_artifact_path(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    chart_path = tmp_path / "heatmap.svg"
    input_path.write_text(
        json.dumps(
            {
                "ticker": "AAPL",
                "market": "US",
                "sensitivity": {
                    "enabled": True,
                    "chart_path": str(chart_path),
                },
            }
        ),
        encoding="utf-8",
    )

    calls = {}

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        return payload

    class _FakeResult:
        def to_dict(self):
            return {
                "ticker": "AAPL",
                "market": "US",
                "valuation_model": "steady_state_single_stage",
                "valuation": {"enterprise_value": 1.0},
            }

    def fake_build(payload, **kwargs):
        calls["metric"] = kwargs["metric"]
        return SensitivityHeatmapOutput(
            ticker="AAPL",
            market="US",
            valuation_model="steady_state_single_stage",
            metric="per_share_value",
            metric_label="Per Share Value",
            currency="USD",
            base_wacc=0.09,
            base_terminal_growth_rate=0.03,
            base_metric_value=100.0,
            wacc_values=[0.08, 0.09],
            terminal_growth_values=[0.02, 0.03],
            matrix=[[90.0, 100.0], [80.0, 90.0]],
        )

    def fake_render(heatmap, output_path_arg, *, title=None):
        calls["rendered"] = str(output_path_arg)
        Path(output_path_arg).write_text("<svg/>", encoding="utf-8")
        return Path(output_path_arg)

    monkeypatch.setattr(cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(cli, "run_valuation", lambda payload: _FakeResult())
    monkeypatch.setattr(cli, "build_wacc_terminal_growth_sensitivity", fake_build)
    monkeypatch.setattr(cli, "render_wacc_terminal_growth_heatmap", fake_render)

    rc = cli.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--pretty",
        ]
    )

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["sensitivity"]["base_metric_value"] == 100.0
    assert payload["artifacts"]["sensitivity_heatmap_path"] == str(chart_path.resolve())
    assert calls == {
        "metric": "per_share_value",
        "rendered": str(chart_path.resolve()),
    }
