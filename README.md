# FP-DCF

[English](./README.md) | [简体中文](./README.zh-CN.md)

A first-principles DCF engine for LLM agents and quantitative research workflows.

FP-DCF turns normalized public-company data into auditable `FCFF`, `WACC`, valuation, implied-growth, and sensitivity outputs without hiding accounting and valuation assumptions behind opaque shortcuts.

> Repository workflow note: GitHub submissions for this project do not use a separate feature-branch workflow. Commit and publish on the designated branch directly unless the maintainer explicitly says otherwise.

![Sample sensitivity heatmap](./examples/sample_output.sensitivity.png)

## Quickstart

Install and run the sample in one go:

```bash
python3 -m pip install .
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

This returns structured JSON and, by default, auto-renders `png/svg` sensitivity heatmaps.

## Who this is for

* agent / tool workflows that need machine-readable valuation output
* quantitative and discretionary research pipelines
* users who care about auditable `FCFF -> WACC -> DCF` logic
* downstream systems that need diagnostics, warnings, and source labels

## Not for

* portfolio optimization
* trade execution
* backtesting platforms
* black-box one-number valuation tools
* factor ranking systems unrelated to valuation

## Why FP-DCF

Unlike many open-source DCF scripts, FP-DCF:

* separates operating tax for `FCFF` from marginal tax for `WACC`
* uses an explicit `Delta NWC` hierarchy instead of hard-coding one noisy field
* supports traceable FCFF path selection (`EBIAT` vs `CFO`)
* supports normalized anchor modes (`latest`, `manual`, `three_period_average`, `reconciled_average`)
* emits diagnostics, warnings, and source labels in structured output

## What you get

* structured valuation JSON
* implied growth (`one_stage` / `two_stage`)
* `WACC x Terminal Growth` sensitivity heatmaps
* Yahoo-backed normalization with local cache
* machine-readable diagnostics for downstream tools

## Sample output shape

```json
{
  "fcff": {
    "selected_path": "ebiat",
    "anchor_mode": "latest"
  },
  "valuation": {
    "enterprise_value": 1785801405103.29,
    "per_share_value": 112.25
  },
  "implied_growth": {
    "model": "one_stage",
    "one_stage": {
      "growth_rate": 0.0594
    }
  },
  "sensitivity": {
    "metric": "per_share_value"
  }
}
```

See also:

* [sample_input.json](./examples/sample_input.json)
* [sample_output.json](./examples/sample_output.json)
* [Methodology](./references/methodology.md)
* [简体中文](./README.zh-CN.md)

## Positioning

This repository is the public-facing extraction layer for a larger Yahoo / market-data-based DCF workflow. It is intentionally narrower than a full research platform:

* It focuses on valuation logic, input / output contracts, and LLM-friendly packaging.
* It does not try to be a portfolio optimizer, execution engine, or backtesting system.
* It is meant to sit upstream of downstream ranking, portfolio construction, or agent orchestration layers.

## Core principles

### 1. Tax-rate separation

* `FCFF` should use the best available operating tax estimate, typically the reported effective tax rate from the statement set.
* `WACC` should apply a marginal tax assumption to the debt tax shield.
* If either rate is missing, the fallback source must be explicit in the output.

### 2. Robust Delta NWC handling

The intended hierarchy is:

1. `delta_nwc`
2. `OpNWC_delta`
3. `NWC_delta`
4. derived operating working capital from current assets / current liabilities
5. cash-flow statement fallback such as `ChangeInWorkingCapital`

The selected source should always be reported back to the caller.

### 3. Normalized FCFF anchors

For steady-state single-stage DCF:

* do not treat historical `FCFF` as future explicit forecast periods
* prefer a normalized steady-state anchor
* prefer `NOPAT + ROIC + reinvestment` when the required drivers are available
* fall back to normalized historical `FCFF` only when the operating-driver path is incomplete
* `assumptions.fcff_anchor_mode` defaults to `latest` and also supports `manual`, `three_period_average`, and `reconciled_average`
* Yahoo-backed normalization exposes only the minimal historical series needed for those modes, using `date:value` dictionaries

### 4. Market-value-aware WACC

The intended `WACC` path is:

* risk-free rate
* equity risk premium
* beta / cost of equity
* pre-tax cost of debt
* market-value-based equity and debt weights
* explicit marginal tax shield on debt

## Executable entry points

Run with a complete structured input:

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

Or use the packaged CLI after installation:

```bash
fp-dcf --input examples/sample_input.json --pretty
```

If you only have a ticker and want the runner to fill missing valuation inputs from Yahoo Finance, start from:

```bash
cat > /tmp/fp_dcf_yahoo_input.json <<'JSON'
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
JSON

python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty
```

## Sensitivity heatmap

FP-DCF attaches a compact `WACC x Terminal Growth` sensitivity summary to the main valuation JSON by default and auto-renders chart artifacts in the same run.

CLI example:

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --pretty
```

That single command will:

* write the valuation JSON to `/tmp/aapl_output.json`
* attach a compact `sensitivity` summary to the JSON
* auto-render the heatmap to `/tmp/aapl_output.sensitivity.svg`
* auto-render a display-friendly PNG to `/tmp/aapl_output.sensitivity.png`

If you want to override the default chart path, you can still do that from the CLI:

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --sensitivity-chart-output /tmp/aapl_sensitivity.svg \
  --pretty
```

Or drive the override from the input payload:

```json
{
  "sensitivity": {
    "metric": "per_share_value",
    "chart_path": "/tmp/aapl_sensitivity.svg",
    "wacc_range_bps": 200,
    "wacc_step_bps": 100,
    "growth_range_bps": 100,
    "growth_step_bps": 50
  }
}
```

If you need the full numeric grid in JSON, opt in from the payload:

```json
{
  "sensitivity": {
    "detail": true
  }
}
```

If you want to disable sensitivity for a specific run, use:

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --no-sensitivity --pretty
```

Or in the payload:

```json
{
  "sensitivity": {
    "enabled": false
  }
}
```

Default heatmap settings:

* `metric=per_share_value`
* WACC range: base case `+/- 200 bps`
* terminal growth range: base case `+/- 100 bps`

Invalid cells where terminal growth is greater than or equal to WACC are left blank and reported in the diagnostics.

## Implied growth

The main CLI can also append a structured implied-growth block without changing the core `run_valuation()` behavior.

Input contract:

* `payload.market_inputs.enterprise_value_market`, or
* `payload.market_inputs.market_price` + `shares_out` + `net_debt`
* `payload.implied_growth.model`: `one_stage` or `two_stage`

One-stage example:

```json
{
  "market_inputs": {
    "market_price": 225.0
  },
  "implied_growth": {
    "model": "one_stage"
  }
}
```

Two-stage example:

```json
{
  "market_inputs": {
    "enterprise_value_market": 3500000000000.0
  },
  "implied_growth": {
    "model": "two_stage",
    "high_growth_years": 5,
    "stable_growth_rate": 0.03,
    "lower_bound": 0.0,
    "upper_bound": 0.25
  }
}
```

The output appends:

* `market_inputs`: resolved market EV / equity value / price / shares / net debt with sources
* `implied_growth`: structured solver output

For `one_stage`, FP-DCF uses a closed-form implied growth solution. For `two_stage`, it solves the implied high-growth rate via bisection while keeping the stable growth rate fixed.

If implied growth is enabled but the required market inputs are incomplete, the CLI skips the implied-growth block instead of failing the main valuation run.

## Provider cache

Yahoo-backed normalization uses a local cache by default so repeated runs do not re-fetch the same provider snapshot every time.

Default cache path:

```bash
~/.cache/fp-dcf
```

To force a fresh Yahoo pull and overwrite the cached snapshot for that request shape:

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --refresh-provider
```

To override the cache directory:

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --cache-dir /tmp/fp-dcf-cache
```

You can also control normalization behavior from the JSON payload:

```json
{
  "normalization": {
    "provider": "yahoo",
    "use_cache": true,
    "refresh": false,
    "cache_dir": "/tmp/fp-dcf-cache"
  }
}
```

Provider-backed runs also emit cache diagnostics such as:

* `provider_cache_miss:yahoo`
* `provider_cache_hit:yahoo`
* `provider_cache_refresh:yahoo`

## Structured output direction

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
    "debt_weight": 0.08,
    "source": "yahoo:market_value_using_total_debt"
  },
  "fcff": {
    "anchor": 106216000000.0,
    "anchor_method": "ebiat_plus_da_minus_capex_minus_delta_nwc",
    "selected_path": "ebiat",
    "anchor_ebiat_path": 106216000000.0,
    "anchor_cfo_path": null,
    "ebiat_path_available": true,
    "cfo_path_available": false,
    "after_tax_interest": null,
    "after_tax_interest_source": null,
    "reconciliation_gap": null,
    "reconciliation_gap_pct": null,
    "anchor_mode": "latest",
    "anchor_observation_count": 1,
    "delta_nwc_source": "OpNWC_delta"
  },
  "valuation": {
    "enterprise_value": 1785801405103.2935,
    "equity_value": 1739801405103.2935,
    "per_share_value": 112.24525194214796
  },
  "market_inputs": {
    "enterprise_value_market": 3533500000000.0,
    "enterprise_value_market_source": "derived_from_market_price_shares_out_and_net_debt",
    "equity_value_market": 3487500000000.0,
    "market_price": 225.0,
    "shares_out": 15500000000.0,
    "net_debt": 46000000000.0
  },
  "implied_growth": {
    "enabled": true,
    "model": "one_stage",
    "solver": "closed_form",
    "success": true,
    "enterprise_value_market": 3533500000000.0,
    "fcff_anchor": 106216000000.0,
    "wacc": 0.0912624,
    "one_stage": {
      "growth_rate": 0.05941663866081859
    },
    "two_stage": null
  },
  "diagnostics": [
    "tax_rate_paths_are_separated",
    "fcff_path_selector_only_ebiat_available",
    "fcff_path_selected:ebiat",
    "valuation_model_steady_state_single_stage"
  ]
}
```

See [sample_input.json](./examples/sample_input.json) and [sample_output.json](./examples/sample_output.json) for fuller examples.

## Repository layout

```text
FP-DCF/
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── pyproject.toml
├── .gitignore
├── examples/
│   ├── sample_input.json
│   ├── sample_output.json
│   └── sample_output.sensitivity.png
├── scripts/
│   ├── plot_sensitivity.py
│   └── run_dcf.py
├── references/
│   └── methodology.md
├── tests/
└── fp_dcf/
```

## Installation

```bash
python3 -m pip install .
```

Current base dependencies:

* `numpy`
* `pandas`
* `yfinance`
* `matplotlib`

`matplotlib` is a base dependency because the main CLI renders `png/svg` sensitivity charts by default.

The legacy `.[viz]` extra still works as a backward-compatible alias:

```bash
python3 -m pip install .[viz]
```

For local development and tests:

```bash
python3 -m pip install --upgrade pip
pip install -e .[dev]
```

To run the optional live Yahoo integration test:

```bash
FP_DCF_RUN_YAHOO_TESTS=1 pytest -q tests/test_yahoo_integration.py
```

## Current limitations

* Yahoo-backed normalization depends on provider field quality and availability.
* The provider cache does not yet support TTL or staleness policies.
* Financial-sector companies are not yet handled by a dedicated valuation path.
* Yahoo is the only live normalization provider currently implemented.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, checks, and the repository's no-extra-branch GitHub submission workflow.
