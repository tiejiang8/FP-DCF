from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import run_valuation
from .normalize import normalize_payload


def _load_payload(input_path: str) -> dict:
    if input_path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(input_path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must decode to an object")
    return payload


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
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the output JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        payload = _load_payload(args.input)
        payload = normalize_payload(payload, provider_override=args.provider)
        result = run_valuation(payload).to_dict()
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
