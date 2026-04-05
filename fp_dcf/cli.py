from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import run_valuation
from .normalize import normalize_payload
from .plotting import render_wacc_terminal_growth_heatmap
from .sensitivity import build_wacc_terminal_growth_sensitivity


def _load_payload(input_path: str) -> dict:
    if input_path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(input_path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must decode to an object")
    return payload


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _resolve_sensitivity_request(payload: dict, args: argparse.Namespace) -> dict | None:
    config = payload.get("sensitivity") or {}
    if not isinstance(config, dict):
        config = {}

    enabled = any(
        [
            args.sensitivity,
            args.sensitivity_metric is not None,
            args.sensitivity_chart_output is not None,
            args.sensitivity_title is not None,
            args.sensitivity_wacc_range_bps is not None,
            args.sensitivity_wacc_step_bps is not None,
            args.sensitivity_growth_range_bps is not None,
            args.sensitivity_growth_step_bps is not None,
            _truthy(config.get("enabled")),
            config.get("metric") not in (None, ""),
            config.get("chart_path") not in (None, ""),
        ]
    )
    if not enabled:
        return None

    return {
        "metric": args.sensitivity_metric or config.get("metric") or "per_share_value",
        "chart_path": args.sensitivity_chart_output or config.get("chart_path"),
        "title": args.sensitivity_title or config.get("title"),
        "wacc_range_bps": args.sensitivity_wacc_range_bps
        if args.sensitivity_wacc_range_bps is not None
        else int(config.get("wacc_range_bps") or 200),
        "wacc_step_bps": args.sensitivity_wacc_step_bps
        if args.sensitivity_wacc_step_bps is not None
        else int(config.get("wacc_step_bps") or 100),
        "growth_range_bps": args.sensitivity_growth_range_bps
        if args.sensitivity_growth_range_bps is not None
        else int(config.get("growth_range_bps") or 100),
        "growth_step_bps": args.sensitivity_growth_step_bps
        if args.sensitivity_growth_step_bps is not None
        else int(config.get("growth_step_bps") or 50),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a first-principles DCF valuation from JSON input.")
    parser.add_argument("--input", default="-", help="Path to the input JSON file. Use - to read from stdin.")
    parser.add_argument("--output", default="-", help="Path to write output JSON. Use - to write to stdout.")
    parser.add_argument(
        "--provider",
        choices=["yahoo"],
        default=None,
        help="Optionally enrich missing inputs using a provider before valuation.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Override the provider cache directory. Defaults to the local user cache path.",
    )
    parser.add_argument(
        "--refresh-provider",
        action="store_true",
        help="Force a fresh provider fetch and overwrite the cached snapshot for this request.",
    )
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="Include a WACC x terminal growth sensitivity grid in the output JSON.",
    )
    parser.add_argument(
        "--sensitivity-metric",
        choices=["per_share_value", "equity_value", "enterprise_value"],
        default=None,
        help="Metric to use when generating the optional sensitivity grid.",
    )
    parser.add_argument(
        "--sensitivity-chart-output",
        default=None,
        help="Optional output path for a rendered sensitivity heatmap artifact.",
    )
    parser.add_argument(
        "--sensitivity-title",
        default=None,
        help="Optional chart title override for the rendered sensitivity heatmap.",
    )
    parser.add_argument(
        "--sensitivity-wacc-range-bps",
        type=int,
        default=None,
        help="Basis-point range above and below base WACC for the optional sensitivity grid.",
    )
    parser.add_argument(
        "--sensitivity-wacc-step-bps",
        type=int,
        default=None,
        help="Basis-point step size for the optional WACC sensitivity axis.",
    )
    parser.add_argument(
        "--sensitivity-growth-range-bps",
        type=int,
        default=None,
        help="Basis-point range above and below base terminal growth for the optional sensitivity grid.",
    )
    parser.add_argument(
        "--sensitivity-growth-step-bps",
        type=int,
        default=None,
        help="Basis-point step size for the optional terminal growth sensitivity axis.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the output JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        payload = _load_payload(args.input)
        payload = normalize_payload(
            payload,
            provider_override=args.provider,
            cache_dir=args.cache_dir,
            force_refresh=args.refresh_provider,
        )
        result = run_valuation(payload).to_dict()

        sensitivity_request = _resolve_sensitivity_request(payload, args)
        if sensitivity_request is not None:
            sensitivity = build_wacc_terminal_growth_sensitivity(
                payload,
                metric=sensitivity_request["metric"],
                wacc_range_bps=sensitivity_request["wacc_range_bps"],
                wacc_step_bps=sensitivity_request["wacc_step_bps"],
                growth_range_bps=sensitivity_request["growth_range_bps"],
                growth_step_bps=sensitivity_request["growth_step_bps"],
            )
            result["sensitivity"] = sensitivity.to_dict()

            chart_path = sensitivity_request["chart_path"]
            if chart_path:
                rendered_path = render_wacc_terminal_growth_heatmap(
                    sensitivity,
                    Path(chart_path).expanduser().resolve(),
                    title=sensitivity_request["title"],
                )
                artifacts = dict(result.get("artifacts") or {})
                artifacts["sensitivity_heatmap_path"] = str(rendered_path)
                result["artifacts"] = artifacts

        text = json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False)
        if args.output == "-":
            sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))
        else:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
    except Exception as exc:  # pragma: no cover - exercised via CLI smoke test
        sys.stderr.write(f"fp-dcf error: {exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
