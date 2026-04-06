---
name: "fp-dcf"
description: "Estimate intrinsic value with a first-principles DCF from structured JSON or Yahoo-backed ticker input, and return auditable FCFF, WACC, and per-share value output."
metadata: {"openclaw":{"emoji":"📉","homepage":"https://github.com/tiejiang8/FP-DCF","requires":{"anyBins":["python3","python"]}}}
user-invocable: true
---

# FP-DCF

Version: `v0.2.0`

Use this skill when the task is to estimate intrinsic value from structured fundamentals and assumption inputs using a disciplined, auditable DCF workflow.

## Runtime Contract

This repository is executable when installed as a skill because it includes a concrete CLI entrypoint:

- Primary runner: `{baseDir}/scripts/run_dcf.py`
- Python module entrypoint: `python3 -m fp_dcf.cli`
- Sample input: `{baseDir}/examples/sample_input.json`
- Base Python dependencies for the default one-click path: `numpy`, `pandas`, `yfinance`, `matplotlib`

Preferred execution pattern:

1. Build a JSON payload that matches `{baseDir}/examples/sample_input.json`.
2. Write that payload to a temporary JSON file in the workspace.
3. Run one of:
   - `python3 {baseDir}/scripts/run_dcf.py --input /path/to/input.json --pretty`
   - `python {baseDir}/scripts/run_dcf.py --input /path/to/input.json --pretty`
4. Read the JSON output and present the result to the user.

If the runtime supports stdin piping, this also works:

```bash
python3 {baseDir}/scripts/run_dcf.py --pretty < /path/to/input.json
```

Yahoo-backed normalization uses a local provider cache by default. To force a fresh pull from Yahoo for the current request, run:

```bash
python3 {baseDir}/scripts/run_dcf.py --input /path/to/input.json --pretty --refresh-provider
```

If the runtime needs an isolated cache location, pass:

```bash
python3 {baseDir}/scripts/run_dcf.py --input /path/to/input.json --pretty --cache-dir /path/to/cache
```

The main runner already returns a compact sensitivity summary and auto-renders both SVG and PNG chart artifacts by default. If the user explicitly asks for a `WACC x Terminal Growth` chart or sensitivity table, keep using the same main runner so the valuation JSON and artifact paths come back in a single output:

```bash
python3 {baseDir}/scripts/run_dcf.py \
  --input /path/to/input.json \
  --output /path/to/output.json \
  --pretty
```

That one command will default the chart artifact paths to `/path/to/output.sensitivity.svg` and `/path/to/output.sensitivity.png`.

## Input Shape

The expected JSON object contains:

- `ticker`
- `market`
- `valuation_model`
- `assumptions`
- `fundamentals`

Minimum required values for a useful result:

- `assumptions.effective_tax_rate`
- `assumptions.marginal_tax_rate`
- `assumptions.risk_free_rate`
- `assumptions.equity_risk_premium`
- `assumptions.beta`
- `assumptions.pre_tax_cost_of_debt`
- `fundamentals.fcff_anchor` or `fundamentals.ebit`

If `fundamentals.fcff_anchor` is not supplied, the runner computes it from:

- `ebit`
- `da`
- `capex`
- `delta_nwc` or a fallback working-capital field

If those structured fields are mostly missing, the runner can auto-normalize them from Yahoo when:

- `provider` is set to `yahoo`, or
- the payload has a `ticker` but is missing core DCF inputs

The minimal provider-backed input shape is:

```json
{
  "ticker": "AAPL",
  "market": "US",
  "provider": "yahoo",
  "statement_frequency": "A",
  "valuation_model": "steady_state_single_stage",
  "assumptions": {
    "terminal_growth_rate": 0.03
  }
}
```

The payload can also drive normalization behavior through an optional `normalization` object:

- `normalization.provider`
- `normalization.use_cache`
- `normalization.refresh`
- `normalization.cache_dir`

The payload can also request sensitivity analysis through an optional `sensitivity` object:

- `sensitivity.enabled`
- `sensitivity.metric`
- `sensitivity.detail`
- `sensitivity.chart_path`
- `sensitivity.wacc_range_bps`
- `sensitivity.wacc_step_bps`
- `sensitivity.growth_range_bps`
- `sensitivity.growth_step_bps`

Sensitivity output is enabled by default. To disable it for a specific run:

- pass `--no-sensitivity`, or
- set `sensitivity.enabled=false`

Live Yahoo-backed runs are inherently date-sensitive. Do not hard-code expected valuation numbers when validating this path; validate the presence and plausibility of the returned fields instead.

## Core Rules

### Tax Policy

- Keep the operating tax estimate for `FCFF` separate from the marginal tax assumption used in `WACC`.
- If the statement-level tax rate is available, prefer it for `EBIAT/NOPAT`.
- If the marginal tax rate is manual or market-defaulted, expose that source in the output.
- Do not silently reuse one tax rate for both paths when the intended sources differ. If a fallback reuse happens, surface it in `warnings`.

### Working-Capital Policy

Use this fallback order and report which path was used:

1. `delta_nwc`
2. `op_nwc_delta`
3. `nwc_delta`
4. cash-flow working-capital change fields such as `change_in_working_capital`

If all paths fail, flag the result as degraded rather than pretending the estimate is fully reliable.

### FCFF Policy

- Prefer a normalized steady-state `FCFF` anchor for single-stage valuation.
- Prefer `NOPAT + ROIC + reinvestment` when the driver data is usable.
- Fall back to normalized historical `FCFF` only when the operating-driver path is incomplete.
- Do not discount historical realized `FCFF` as if it were a forward forecast.

### WACC Policy

- Use explicit sources for risk-free rate, ERP, beta, pre-tax debt cost, and capital weights.
- Prefer explicit capital weights from the input payload when available.
- Apply the marginal tax assumption only to the debt tax shield.
- Attach a warning when key inputs are manual, defaulted, stale, or missing.

### Sector Policy

- Financial institutions often produce unreliable `FCFF` under industrial-company DCF logic.
- When the company is bank-like, insurer-like, broker-like, or otherwise balance-sheet-driven, downgrade or exclude the result unless the workflow explicitly supports that sector.

## Output Requirements

Always return:

- valuation model used
- major assumptions with source labels
- `FCFF` anchor and anchor method
- working-capital source used
- `WACC` inputs and capital weights
- enterprise value, equity value, and per-share value when available
- provider cache status diagnostics when provider-backed normalization is used
- diagnostics, warnings, and degradation flags
- by default, return a compact sensitivity summary plus both chart file paths

## Execution Notes

- Use `{baseDir}` instead of guessing the install path.
- Prefer writing a JSON file and passing `--input` over hand-building one-line shell JSON.
- If the payload only contains `ticker/market` plus light assumptions, rely on provider-backed normalization instead of fabricating fundamentals.
- Use the default provider cache for repeated runs on the same ticker unless the user explicitly asks for fresh data.
- If the user asks for the latest market or statement snapshot, add `--refresh-provider` or set `normalization.refresh=true`.
- If the user asks for a valuation sensitivity table or heatmap, prefer the main runner with its default sensitivity output and auto-generated chart path over a separate second command.
- If the caller needs the full numeric heatmap grid in JSON, set `sensitivity.detail=true` instead of bloating the default output for every run.
- Only use `--sensitivity-chart-output` or `sensitivity.chart_path` when the caller explicitly wants to override the default artifact location.
- The default one-click path assumes `matplotlib` is installed, because PNG/SVG chart artifacts are rendered automatically.
- If the environment intentionally excludes `matplotlib`, disable sensitivity first with `--no-sensitivity` or `sensitivity.enabled=false` before running the main CLI.
- If `per_share_value` sensitivity is unavailable because `shares_out` is missing, try `--refresh-provider` first or switch the sensitivity metric to `equity_value`.
- If the user only gives high-level valuation preferences, ask for or derive the missing structured inputs before running the script.
- Read [references/methodology.md](./references/methodology.md) only when you need policy detail beyond this file.

## Reference Map

Read only what you need:

- [references/methodology.md](./references/methodology.md) for the valuation methodology
- [examples/sample_input.json](./examples/sample_input.json) for the intended input contract
- [examples/sample_output.json](./examples/sample_output.json) for the intended output contract

## Quality Bar

- Prefer explicit assumptions over hidden heuristics.
- Prefer auditable fallbacks over brittle elegance.
- Label degraded results clearly.
- Be conservative when provider data is incomplete or inconsistent.
- If a result depends heavily on terminal value, include that in the diagnostics.
