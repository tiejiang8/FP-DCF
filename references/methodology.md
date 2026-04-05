# FP-DCF Methodology

This document defines the intended public methodology for `FP-DCF`.

## Objective

`FP-DCF` is designed to compute intrinsic value from public-company statements using a disciplined `FCFF -> WACC -> DCF` pipeline that is robust to imperfect retail-market data providers.

## FCFF Policy

### Operating Tax

- Preferred source: reported statement-level effective tax rate.
- Fallback source: explicit market default or user-provided override.
- Requirement: the output must state which source was used.

### Delta NWC Hierarchy

Use the first reliable source in this order:

1. `OpNWC_delta`
2. `NWC_delta`
3. derived operating NWC from current assets/current liabilities, excluding non-operating cash and short-term debt when possible
4. cash-flow fallback such as `ChangeInWorkingCapital`

This is intentionally more conservative than hard-coding a single balance-sheet formula.

### FCFF Construction

Preferred paths:

- `EBIAT + D&A - CapEx - DeltaNWC`
- `CFO + after-tax interest - CapEx`

If both paths exist, the engine should expose which path was selected and why.

## WACC Policy

The intended `WACC` contract contains:

- risk-free rate
- equity risk premium
- beta
- cost of equity
- pre-tax cost of debt
- marginal tax rate
- equity weight
- debt weight

The debt tax shield should use the marginal tax assumption, not the operating tax estimate used in `FCFF`.

## Valuation Models

### Steady-State Single-Stage DCF

Recommended when the business is mature or the user wants a normalized base-case valuation.

Policy:

- estimate a steady-state `FCFF` anchor
- grow one period forward
- compute terminal enterprise value from `FCFF_1 / (WACC - g)`
- avoid treating historical realized `FCFF` as a forward explicit forecast series

### Two-Stage DCF

Recommended when a higher-growth period is material and defendable.

Policy:

- explicit high-growth stage
- stable terminal stage
- `g_stable < WACC`

## Reliability Flags

The engine should emit diagnostics when:

- tax inputs are defaulted
- shares outstanding are stale or missing
- debt cost is defaulted
- working-capital inputs are missing or degraded
- the result is dominated by terminal value
- the company appears financial-like under an industrial DCF workflow

## Public Contract Direction

The public interface should be machine-readable first and include:

- assumptions
- source labels
- diagnostics
- degradation flags
- valuation outputs

Human-readable reports can be layered on top, but they should not replace the structured contract.

