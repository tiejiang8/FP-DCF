from __future__ import annotations

import json
from pathlib import Path

from fp_dcf import SensitivityHeatmapOutput
from fp_dcf import sensitivity_cli


def test_sensitivity_cli_writes_json_and_renders_chart(tmp_path: Path, monkeypatch):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "heatmap.svg"
    json_path = tmp_path / "heatmap.json"
    input_path.write_text('{"ticker":"AAPL","market":"US"}', encoding="utf-8")

    calls = {}

    def fake_normalize_payload(payload, provider_override=None, *, cache_dir=None, force_refresh=None):
        calls["provider_override"] = provider_override
        calls["cache_dir"] = cache_dir
        calls["force_refresh"] = force_refresh
        return payload

    def fake_build(payload, **kwargs):
        calls["metric"] = kwargs["metric"]
        calls["wacc_range_bps"] = kwargs["wacc_range_bps"]
        calls["growth_range_bps"] = kwargs["growth_range_bps"]
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
        calls["render_output"] = str(output_path_arg)
        calls["title"] = title
        Path(output_path_arg).write_text("<svg/>", encoding="utf-8")

    monkeypatch.setattr(sensitivity_cli, "normalize_payload", fake_normalize_payload)
    monkeypatch.setattr(sensitivity_cli, "build_wacc_terminal_growth_sensitivity", fake_build)
    monkeypatch.setattr(sensitivity_cli, "render_wacc_terminal_growth_heatmap", fake_render)

    rc = sensitivity_cli.main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--json-output",
            str(json_path),
            "--provider",
            "yahoo",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--refresh-provider",
            "--metric",
            "per_share_value",
            "--wacc-range-bps",
            "300",
            "--growth-range-bps",
            "150",
            "--title",
            "Test Heatmap",
            "--pretty",
        ]
    )

    assert rc == 0
    assert calls == {
        "provider_override": "yahoo",
        "cache_dir": str(tmp_path / "cache"),
        "force_refresh": True,
        "metric": "per_share_value",
        "wacc_range_bps": 300,
        "growth_range_bps": 150,
        "render_output": str(output_path),
        "title": "Test Heatmap",
    }
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["ticker"] == "AAPL"
    assert payload["base_metric_value"] == 100.0
    assert output_path.read_text(encoding="utf-8") == "<svg/>"


def test_sensitivity_cli_parser_accepts_akshare_baostock_provider():
    parser = sensitivity_cli.build_parser()
    args = parser.parse_args(["--provider", "akshare_baostock"])
    assert args.provider == "akshare_baostock"
