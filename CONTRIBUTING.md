# Contributing to FP-DCF

Thanks for contributing to `FP-DCF`.

This repository is intended to become a clean, public-facing extraction of a first-principles DCF workflow for LLM agents and quantitative research use cases. The project values explicit assumptions, auditable fallbacks, and small, reviewable changes.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

## Running Checks

```bash
ruff check .
pytest -q
```

## Contribution Guidelines

- Keep changes scoped and intentional.
- Prefer explicit assumption sources over hidden heuristics.
- Label degraded or fallback behavior clearly.
- Add or update tests when changing contracts, schemas, or valuation logic.
- Update documentation when public behavior changes.

## Pull Requests

Before opening a PR, please make sure:

- the branch is up to date with `main`
- lint and tests pass locally
- the README or methodology docs are updated when needed
- new fallback behavior is explained in code or docs

## Areas That Need Help

- extracting `FCFF` logic from the reference workflow into this package
- extracting `WACC` and market-data utilities
- adding stable provider interfaces
- expanding schema coverage for structured agent outputs
- adding tests around tax separation and working-capital fallback selection
