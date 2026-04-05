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

- an executable CLI and script entrypoint for structured DCF runs
- an agent-facing `SKILL.md` for OpenClaw-style runtimes
- provider-backed normalization from Yahoo Finance
- a default local cache for provider snapshots, plus a force-refresh path
- JSON examples and tests for downstream agent integration

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
├── scripts/
│   └── run_dcf.py
├── references/
│   └── methodology.md
└── fp_dcf/
    ├── __init__.py
    ├── cli.py
    ├── engine.py
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

## Executable Entry Points

This repository now includes a runnable valuation path:

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

You can also use the packaged CLI after installation:

```bash
fp-dcf --input examples/sample_input.json --pretty
```

The runner expects structured JSON input and emits structured JSON output suitable for OpenClaw-style skill execution.

If you only have a ticker and want the runner to fill missing valuation inputs from Yahoo Finance, start from:

```bash
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty
```

Yahoo-backed normalization uses a local cache by default so repeated runs do not re-fetch the same provider snapshot every time. The default cache path is:

```bash
~/.cache/fp-dcf
```

To force a fresh Yahoo pull and overwrite the cached snapshot for that ticker/request shape:

```bash
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty --refresh-provider
```

To override the cache directory:

```bash
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty --cache-dir /tmp/fp-dcf-cache
```

For a live Yahoo-backed smoke run, install the runtime deps and execute the same command. The output is date-sensitive and will change as Yahoo data changes.

## Structured Output Direction

The public contract is meant to be machine-readable first. A typical response shape looks like:

```json
{
  "ticker": "AAPL",
  "market": "US",
  "valuation_model": "steady_state_single_stage",
  "tax": {
    "effective_tax_rate": 0.187,
    "marginal_tax_rate": 0.21
  },
  "wacc_inputs": {
    "risk_free_rate": 0.043,
    "equity_risk_premium": 0.05,
    "beta": 1.08,
    "pre_tax_cost_of_debt": 0.032,
    "wacc": 0.0912624
  },
  "capital_structure": {
    "equity_weight": 0.92,
    "debt_weight": 0.08
  },
  "fcff": {
    "anchor": 106216000000.0,
    "anchor_method": "ebiat_plus_da_minus_capex_minus_delta_nwc",
    "delta_nwc_source": "OpNWC_delta"
  },
  "valuation": {
    "enterprise_value": 1785801405103.2935,
    "equity_value": 1739801405103.2935,
    "per_share_value": 112.24525194214796
  },
  "diagnostics": [
    "tax_rate_paths_are_separated",
    "valuation_model_steady_state_single_stage"
  ]
}
```

See [sample_input.json](./examples/sample_input.json) and [sample_output.json](./examples/sample_output.json) for a fuller example.
For provider-backed normalization from Yahoo, see [sample_input_yahoo.json](./examples/sample_input_yahoo.json).

## Installation

```bash
pip install -e .
```

Current base dependencies:

- `numpy`
- `pandas`
- `yfinance`

For local development and tests:

```bash
pip install -e .[dev]
```

To run the optional live Yahoo integration test:

```bash
FP_DCF_RUN_YAHOO_TESTS=1 pytest -q tests/test_yahoo_integration.py
```

## Near-Term Roadmap

1. Harden the Yahoo normalization path around edge-case statement coverage and stale fields.
2. Add more valuation-model tests around cash-flow fallback behavior and warning propagation.
3. Add cache freshness policy and optional TTL controls for provider snapshots.
4. Expand tests for tax isolation and delta-NWC fallback selection.
5. Add provider adapters and explicit financial-sector downgrade rules.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, checks, and PR expectations.

## Publishing Notes

Before publishing to GitHub, the remaining high-signal tasks are:

- choose a license
- initialize the Git repository
- add the first implementation modules
- add minimal tests
- decide whether the public repo is package-first, skill-first, or dual-mode
