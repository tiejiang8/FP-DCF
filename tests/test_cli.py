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
    assert payload["sensitivity"]["metric"] == "per_share_value"
    assert "grid" not in payload["sensitivity"]
    assert payload["artifacts"]["sensitivity_heatmap_path"] == str(output_path.with_name("out.sensitivity.png"))
    assert payload["artifacts"]["sensitivity_heatmap_svg_path"] == str(output_path.with_name("out.sensitivity.svg"))
    assert output_path.with_name("out.sensitivity.svg").exists()
    assert output_path.with_name("out.sensitivity.png").exists()


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
            "--no-sensitivity",
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

    calls = {"rendered": []}

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
        calls["rendered"].append(str(output_path_arg))
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
    assert payload["artifacts"]["sensitivity_heatmap_path"] == str(chart_path.with_suffix(".png").resolve())
    assert payload["artifacts"]["sensitivity_heatmap_svg_path"] == str(chart_path.resolve())
    assert calls == {
        "metric": "per_share_value",
        "rendered": [
            str(chart_path.resolve()),
            str(chart_path.with_suffix(".png").resolve()),
        ],
    }


def test_cli_generates_default_chart_path_when_not_supplied(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text('{"ticker":"AAPL","market":"US"}', encoding="utf-8")

    calls = {"rendered": []}

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        return payload

    class _FakeResult:
        def to_dict(self):
            return {
                "ticker": "AAPL",
                "market": "US",
                "valuation_model": "steady_state_single_stage",
                "valuation": {"enterprise_value": 1.0, "per_share_value": 1.0},
            }

    def fake_build(payload, **kwargs):
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
        calls["rendered"].append(str(output_path_arg))
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

    expected_svg_path = output_path.with_name("out.sensitivity.svg")
    expected_png_path = output_path.with_name("out.sensitivity.png")

    assert rc == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifacts"]["sensitivity_heatmap_path"] == str(expected_png_path)
    assert payload["artifacts"]["sensitivity_heatmap_svg_path"] == str(expected_svg_path)
    assert calls == {
        "rendered": [
            str(expected_svg_path),
            str(expected_png_path),
        ],
    }


def test_cli_can_disable_default_sensitivity(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text('{"ticker":"AAPL","market":"US"}', encoding="utf-8")

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
    assert "sensitivity" not in payload


def test_cli_auto_falls_back_sensitivity_metric_when_per_share_unavailable(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text('{"ticker":"AAPL","market":"US"}', encoding="utf-8")

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

    calls = {"metrics": []}

    def fake_build(payload, **kwargs):
        metric = kwargs["metric"]
        calls["metrics"].append(metric)
        if metric == "per_share_value":
            raise ValueError("Unable to compute sensitivity metric 'per_share_value'")
        return SensitivityHeatmapOutput(
            ticker="AAPL",
            market="US",
            valuation_model="steady_state_single_stage",
            metric=metric,
            metric_label="Equity Value" if metric == "equity_value" else "Enterprise Value",
            currency="USD",
            base_wacc=0.09,
            base_terminal_growth_rate=0.03,
            base_metric_value=100.0,
            wacc_values=[0.08, 0.09],
            terminal_growth_values=[0.02, 0.03],
            matrix=[[90.0, 100.0], [80.0, 90.0]],
            diagnostics=[],
        )

    monkeypatch.setattr(cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(cli, "run_valuation", lambda payload: _FakeResult())
    monkeypatch.setattr(cli, "build_wacc_terminal_growth_sensitivity", fake_build)

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
    assert payload["sensitivity"]["metric"] == "equity_value"
    assert "sensitivity_metric_auto_fallback:equity_value" in payload["sensitivity"]["diagnostics"]
    assert calls["metrics"] == ["per_share_value", "equity_value"]


def test_cli_can_include_detailed_sensitivity_grid_via_payload(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "out.json"
    input_path.write_text(
        json.dumps(
            {
                "ticker": "AAPL",
                "market": "US",
                "sensitivity": {"detail": True},
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
                "valuation": {"enterprise_value": 1.0, "per_share_value": 1.0},
                "diagnostics": ["valuation_model_steady_state_single_stage"],
                "warnings": [],
            }

    def fake_build(payload, **kwargs):
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
            diagnostics=[
                "valuation_model_steady_state_single_stage",
                "sensitivity_heatmap:wacc_x_terminal_growth",
            ],
            warnings=[],
        )

    def fake_render(heatmap, output_path_arg, *, title=None):
        Path(output_path_arg).write_text("chart", encoding="utf-8")
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
    assert payload["sensitivity"]["grid"]["wacc_values"] == [0.08, 0.09]
    assert payload["sensitivity"]["diagnostics"] == ["sensitivity_heatmap:wacc_x_terminal_growth"]
