from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path


_PROVIDER_CACHE_VERSION = 3


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


def _normalize_bool(value, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base).expanduser() / "fp-dcf"
    return Path.home() / ".cache" / "fp-dcf"


def _resolve_cache_dir(cache_dir: str | os.PathLike[str] | None) -> Path:
    if cache_dir is None:
        return _default_cache_dir()
    return Path(cache_dir).expanduser()


def _provider_cache_key(provider_name: str, payload: dict) -> dict[str, str | int]:
    return {
        "cache_version": _PROVIDER_CACHE_VERSION,
        "provider": provider_name,
        "ticker": str(payload.get("ticker") or "").strip().upper(),
        "market": str(payload.get("market") or "US").strip().upper(),
        "statement_frequency": str(payload.get("statement_frequency") or "A").strip().upper(),
    }


def _provider_cache_path(
    provider_name: str,
    payload: dict,
    cache_dir: str | os.PathLike[str] | None,
) -> Path:
    cache_root = _resolve_cache_dir(cache_dir)
    cache_key = _provider_cache_key(provider_name, payload)
    digest = hashlib.sha256(
        json.dumps(cache_key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return cache_root / "providers" / provider_name / f"{digest}.json"


def _load_provider_snapshot(cache_path: Path) -> dict | None:
    if not cache_path.exists():
        return None
    try:
        raw = cache_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    snapshot = payload.get("snapshot")
    return snapshot if isinstance(snapshot, dict) else None


def _write_provider_snapshot(cache_path: Path, snapshot: dict) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "cache_version": _PROVIDER_CACHE_VERSION,
        "snapshot": snapshot,
    }
    text = json.dumps(envelope, sort_keys=True, ensure_ascii=False)
    tmp_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
    tmp_path.write_text(text + "\n", encoding="utf-8")
    tmp_path.replace(cache_path)


def _append_prefill_diagnostic(payload: dict, diagnostic: str) -> None:
    diagnostics = list(payload.get("_prefill_diagnostics", []))
    if diagnostic not in diagnostics:
        diagnostics.append(diagnostic)
    payload["_prefill_diagnostics"] = diagnostics


def _append_prefill_warning(payload: dict, warning: str) -> None:
    warnings = list(payload.get("_prefill_warnings", []))
    if warning not in warnings:
        warnings.append(warning)
    payload["_prefill_warnings"] = warnings


def _is_cn_fallback_candidate(payload: dict) -> bool:
    market = str(payload.get("market") or "").strip().upper()
    ticker = str(payload.get("ticker") or "").strip().upper()
    if market == "CN":
        return True
    return ticker.endswith((".SS", ".SH", ".SZ", ".BJ"))


def _provider_handlers(provider_name: str):
    if provider_name == "yahoo":
        from .providers.yahoo import enrich_payload_from_yahoo, fetch_yahoo_snapshot

        return fetch_yahoo_snapshot, enrich_payload_from_yahoo

    if provider_name == "akshare_baostock":
        from .providers.akshare_baostock import (
            enrich_payload_from_akshare_baostock,
            fetch_akshare_baostock_snapshot,
        )

        return fetch_akshare_baostock_snapshot, enrich_payload_from_akshare_baostock

    raise ValueError(f"Unsupported provider: {provider_name}")


def _normalize_with_provider(
    provider_name: str,
    payload: dict,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
    force_refresh: bool | None = None,
) -> dict:
    normalization = payload.get("normalization") or {}
    if not isinstance(normalization, dict):
        normalization = {}

    fetch_snapshot, enrich_payload = _provider_handlers(provider_name)

    use_cache = _normalize_bool(normalization.get("use_cache"), default=True)
    effective_cache_dir = cache_dir or normalization.get("cache_dir")
    should_refresh = (
        force_refresh
        if force_refresh is not None
        else _normalize_bool(normalization.get("refresh"), default=False)
    )

    snapshot = None
    cache_status = "bypass"
    cache_path = _provider_cache_path(provider_name, payload, effective_cache_dir)
    if use_cache and not should_refresh:
        snapshot = _load_provider_snapshot(cache_path)
        if snapshot is not None:
            cache_status = "hit"

    if snapshot is None:
        snapshot = fetch_snapshot(
            payload.get("ticker"),
            market=payload.get("market", "US"),
            statement_frequency=payload.get("statement_frequency") or "A",
        )
        if use_cache:
            _write_provider_snapshot(cache_path, snapshot)
            cache_status = "refresh" if should_refresh else "miss"

    normalized = enrich_payload(payload, snapshot=snapshot)
    if use_cache:
        _append_prefill_diagnostic(normalized, f"provider_cache_{cache_status}:{provider_name}")
    elif should_refresh:
        _append_prefill_diagnostic(
            normalized,
            f"provider_cache_disabled_explicit_refresh:{provider_name}",
        )
    return normalized


def normalize_payload(
    payload: dict,
    provider_override: str | None = None,
    *,
    cache_dir: str | os.PathLike[str] | None = None,
    force_refresh: bool | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")

    out = deepcopy(payload)
    normalization = out.get("normalization") or {}
    if not isinstance(normalization, dict):
        normalization = {}
    provider = provider_override
    if provider is None:
        provider = out.get("provider")
    if provider is None:
        provider = normalization.get("provider")

    if provider is None and not _has_core_inputs(out):
        provider = "yahoo"

    if provider is None:
        return out

    provider_name = str(provider).strip().lower()
    try:
        return _normalize_with_provider(
            provider_name,
            out,
            cache_dir=cache_dir,
            force_refresh=force_refresh,
        )
    except Exception as exc:
        if provider_name != "yahoo" or not _is_cn_fallback_candidate(out):
            raise

        try:
            normalized = _normalize_with_provider(
                "akshare_baostock",
                out,
                cache_dir=cache_dir,
                force_refresh=force_refresh,
            )
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Yahoo normalization failed ({exc}) and akshare_baostock fallback failed ({fallback_exc})"
            ) from fallback_exc

        _append_prefill_diagnostic(normalized, "provider_fallback:yahoo->akshare_baostock")
        _append_prefill_warning(normalized, "yahoo_unavailable_used_akshare_baostock_fallback")
        return normalized
