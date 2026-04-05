from __future__ import annotations

from copy import deepcopy


def _has_core_inputs(payload: dict) -> bool:
    fundamentals = payload.get("fundamentals") or {}
    assumptions = payload.get("assumptions") or {}
    has_anchor = ("fcff_anchor" in fundamentals) or ("ebit" in fundamentals)
    has_wacc_inputs = any(
        key in assumptions
        for key in (
            "risk_free_rate",
            "equity_risk_premium",
            "beta",
            "pre_tax_cost_of_debt",
        )
    )
    return bool(has_anchor and has_wacc_inputs)


def normalize_payload(payload: dict, provider_override: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    out = deepcopy(payload)
    provider = provider_override
    if provider is None:
        provider = out.get("provider")
    if provider is None:
        provider = (out.get("normalization") or {}).get("provider")

    if provider is None and not _has_core_inputs(out):
        provider = "yahoo"

    if provider is None:
        return out

    provider_name = str(provider).strip().lower()
    if provider_name == "yahoo":
        from .providers.yahoo import enrich_payload_from_yahoo

        return enrich_payload_from_yahoo(out)

    raise ValueError(f"Unsupported provider: {provider}")
