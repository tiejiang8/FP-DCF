# FP-DCF

A first-principles DCF skill and valuation engine scaffold for LLM agents and quantitative research workflows.

`FP-DCF` is designed for one job: turning normalized public financial statements and market data into auditable `FCFF`, `WACC`, and intrinsic value estimates without mixing accounting shortcuts and valuation assumptions.

## Positioning

This repository is the public-facing extraction layer for a larger Yahoo/market-data-based DCF workflow. It is intentionally narrower than a full research platform:

- It focuses on valuation logic, input/output contracts, and LLM-friendly packaging.
- It does not try to be a portfolio optimizer, execution engine, or backtesting system.
- It is meant to sit upstream of downstream ranking, portfolio construction, or agent orchestration layers.

## Why FP-DCF

Most open-source DCF tools break down in the same places:

- They use one tax rate everywhere, even though `FCFF` and `WACC` usually need different tax assumptions.
- They rely on fragile working-capital fields that are often missing, mislabeled, or noisy across data providers.
- They discount historical cash flows as if they were future projections instead of estimating a normalized steady-state cash-flow anchor.

`FP-DCF` addresses those issues with explicit calculation rules and auditable diagnostics.

## Core Principles

### 1. Tax-Rate Separation

- `FCFF` should use the best available operating tax estimate, typically the reported effective tax rate from the statement set.
- `WACC` should apply a marginal tax assumption to the debt tax shield.
- If either rate is missing, the fallback source must be explicit in the output.

### 2. Robust Delta NWC Handling

The intended hierarchy is:

1. `OpNWC_delta`
2. `NWC_delta`
3. Derived operating working capital from current assets/current liabilities
4. Cash-flow statement fallback such as `ChangeInWorkingCapital`

The selected source should always be reported back to the caller.

### 3. Normalized FCFF Anchors

For steady-state single-stage DCF:

- Do not treat historical `FCFF` as future explicit forecast periods.
- Prefer a normalized steady-state anchor.
- Prefer `NOPAT + ROIC + reinvestment` when the required drivers are available.
- Fall back to normalized historical `FCFF` only when the operating-driver path is incomplete.

### 4. Market-Value-Aware WACC

The intended `WACC` path is:

- risk-free rate
- equity risk premium
- beta / cost of equity
- pre-tax cost of debt
- market-value-based equity and debt weights
- explicit marginal tax shield on debt

## Repository Status

This repository currently contains:

- a GitHub-ready README and project positioning
- an agent-facing `SKILL.md`
- a lightweight Python package scaffold for typed I/O contracts
- JSON examples for downstream OpenAI / MCP / custom-agent integration

Implementation extraction is the next step. The reference baseline is the local `dcf_mvp_yahoo` workflow, but this repository is being narrowed into a cleaner public skill/package boundary.

## Planned Scope

- normalized statement ingestion from public data providers
- `FCFF` calculation with auditable path selection
- `WACC` calculation with explicit assumption sources
- steady-state single-stage and two-stage DCF
- structured machine-readable output for LLM tools and batch pipelines
- tests around tax handling, working-capital fallback logic, and valuation stability

## Planned Non-Goals

- portfolio optimization
- trade execution
- factor ranking unrelated to valuation
- hiding assumptions behind opaque heuristics

## Repository Layout

```text
FP-DCF/
├── README.md
├── SKILL.md
├── pyproject.toml
├── .gitignore
├── examples/
│   ├── sample_input.json
│   └── sample_output.json
├── references/
│   └── methodology.md
└── fp_dcf/
    ├── __init__.py
    └── schemas.py
```

## Skill Workflow

The intended agent workflow is:

1. Normalize statements and metadata for a single company.
2. Estimate `FCFF` using a traceable tax and working-capital policy.
3. Estimate `WACC` using explicit capital-market assumptions.
4. Run the valuation model.
5. Return both the valuation and the diagnostics that explain how it was produced.

The agent guidance for that workflow lives in [SKILL.md](./SKILL.md).

## Structured Output Direction

The public contract is meant to be machine-readable first. A typical response shape looks like:

```json
{
  "ticker": "AAPL",
  "market": "US",
  "valuation_model": "steady_state_single_stage",
  "assumptions": {
    "effective_tax_rate": 0.187,
    "marginal_tax_rate": 0.21,
    "risk_free_rate": 0.043,
    "equity_risk_premium": 0.05,
    "beta": 1.08,
    "pre_tax_cost_of_debt": 0.032
  },
  "fcff": {
    "anchor": 104200000000.0,
    "anchor_method": "nopat_roic_reinvestment",
    "delta_nwc_source": "OpNWC_delta"
  },
  "valuation": {
    "enterprise_value": 1825000000000.0,
    "equity_value": 1779000000000.0,
    "per_share_value": 114.2
  },
  "diagnostics": [
    "wacc_uses_marginal_tax_rate",
    "fcff_uses_statement_effective_tax_rate"
  ]
}
```

See [sample_input.json](./examples/sample_input.json) and [sample_output.json](./examples/sample_output.json) for a fuller example.

## Installation

```bash
pip install -e .
```

Current base dependencies:

- `numpy`
- `pandas`
- `yfinance`

## Near-Term Roadmap

1. Extract the core `FCFF` logic into this package.
2. Extract the `WACC` and market-data utilities.
3. Add a stable Python API and CLI entrypoint.
4. Add tests for tax isolation and delta-NWC fallback selection.
5. Add provider adapters and explicit financial-sector downgrade rules.

## Publishing Notes

Before publishing to GitHub, the remaining high-signal tasks are:

- choose a license
- initialize the Git repository
- add the first implementation modules
- add minimal tests
- decide whether the public repo is package-first, skill-first, or dual-mode
