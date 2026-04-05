---
name: "fp-dcf"
description: "Use when the user needs a first-principles DCF valuation, wants to audit FCFF/WACC assumptions, or needs structured valuation output for LLM or MCP workflows. Prioritize tax-rate separation, robust working-capital handling, and auditable diagnostics."
---

# FP-DCF

Use this skill when the task is to estimate intrinsic value from public financial statements and market data using a disciplined, auditable DCF workflow.

## Quick Start

1. Gather ticker, market, statement frequency, and the target valuation mode.
2. Normalize the statement inputs into a consistent schema.
3. Build `FCFF` with explicit tax and working-capital logic.
4. Build `WACC` with explicit market assumptions and capital weights.
5. Run the selected DCF model.
6. Return the valuation together with source-aware diagnostics.

## Core Rules

### Tax Policy

- Keep the operating tax estimate for `FCFF` separate from the marginal tax assumption used in `WACC`.
- If the statement-level tax rate is available, prefer it for `EBIAT/NOPAT`.
- If the marginal tax rate is manual or market-defaulted, expose that source in the output.
- Do not silently reuse one tax rate for both paths when the intended sources differ.

### Working-Capital Policy

Use this fallback order and report which path was used:

1. `OpNWC_delta`
2. `NWC_delta`
3. Derived operating working capital from current assets/current liabilities
4. Cash-flow working-capital change fields such as `ChangeInWorkingCapital`

If all paths fail, flag the result as degraded rather than pretending the estimate is fully reliable.

### FCFF Policy

- Prefer a normalized steady-state `FCFF` anchor for single-stage valuation.
- Prefer `NOPAT + ROIC + reinvestment` when the driver data is usable.
- Fall back to normalized historical `FCFF` only when the operating-driver path is incomplete.
- Do not discount historical realized `FCFF` as if it were a forward forecast.

### WACC Policy

- Use explicit sources for risk-free rate, ERP, beta, pre-tax debt cost, and capital weights.
- Prefer market-value capital structure when price and shares-outstanding data are available.
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
- diagnostics, warnings, and degradation flags

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
