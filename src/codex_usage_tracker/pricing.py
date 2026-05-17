"""Local-only pricing and efficiency helpers for aggregate usage rows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codex_usage_tracker.paths import DEFAULT_PRICING_PATH

PRICING_TEMPLATE = {
    "_comment": (
        "Fill in current prices in USD per 1 million tokens. The tracker does "
        "not fetch pricing and leaves this file local-only."
    ),
    "models": {
        "replace-with-model-name": {
            "input_per_million": 0.0,
            "cached_input_per_million": 0.0,
            "output_per_million": 0.0,
        }
    },
}


@dataclass(frozen=True)
class PricingConfig:
    """Parsed local model pricing config."""

    path: Path
    models: dict[str, dict[str, float]]
    loaded: bool
    error: str | None = None

    def rates_for(self, model: object) -> dict[str, float] | None:
        if not isinstance(model, str) or not model:
            return None
        return self.models.get(model)


def load_pricing_config(path: Path = DEFAULT_PRICING_PATH) -> PricingConfig:
    """Load optional local pricing without contacting external services."""

    if not path.exists():
        return PricingConfig(path=path, models={}, loaded=False)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        models = _parse_models(raw)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return PricingConfig(path=path, models={}, loaded=False, error=str(exc))
    return PricingConfig(path=path, models=models, loaded=True)


def write_pricing_template(path: Path = DEFAULT_PRICING_PATH, force: bool = False) -> Path:
    """Write a local pricing template for user-maintained cost estimates."""

    if path.exists() and not force:
        raise FileExistsError(f"Pricing config already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(PRICING_TEMPLATE, indent=2) + "\n", encoding="utf-8")
    return path


def annotate_rows_with_efficiency(
    rows: list[dict[str, Any]],
    pricing: PricingConfig | None = None,
    *,
    model_field: str = "model",
) -> list[dict[str, Any]]:
    """Return copied rows with local cost estimates and efficiency flags."""

    config = pricing or load_pricing_config()
    annotated: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        model = copy.get(model_field)
        cost = estimate_cost_usd(copy, config, model=model)
        savings = estimate_cache_savings_usd(copy, config, model=model)
        copy["estimated_cost_usd"] = cost
        copy["estimated_cache_savings_usd"] = savings
        copy["efficiency_flags"] = efficiency_flags(copy)
        annotated.append(copy)
    return annotated


def estimate_cost_usd(
    row: dict[str, Any], pricing: PricingConfig, *, model: object | None = None
) -> float | None:
    """Estimate call cost from aggregate tokens and local model rates."""

    rates = pricing.rates_for(model if model is not None else row.get("model"))
    if not rates:
        return None

    input_rate = rates.get("input_per_million")
    cached_rate = rates.get("cached_input_per_million", input_rate)
    output_rate = rates.get("output_per_million")
    if input_rate is None or cached_rate is None or output_rate is None:
        return None

    cached_input = _number(row.get("cached_input_tokens"))
    uncached_input = _number(row.get("uncached_input_tokens"))
    if uncached_input <= 0:
        uncached_input = max(_number(row.get("input_tokens")) - cached_input, 0.0)
    output_tokens = _number(row.get("output_tokens"))

    return (
        (uncached_input * input_rate)
        + (cached_input * cached_rate)
        + (output_tokens * output_rate)
    ) / 1_000_000


def estimate_cache_savings_usd(
    row: dict[str, Any], pricing: PricingConfig, *, model: object | None = None
) -> float | None:
    """Estimate local cache savings when cached input has a lower configured rate."""

    rates = pricing.rates_for(model if model is not None else row.get("model"))
    if not rates:
        return None
    input_rate = rates.get("input_per_million")
    cached_rate = rates.get("cached_input_per_million")
    if input_rate is None or cached_rate is None or cached_rate >= input_rate:
        return None
    return (_number(row.get("cached_input_tokens")) * (input_rate - cached_rate)) / 1_000_000


def efficiency_flags(row: dict[str, Any]) -> list[str]:
    """Generate aggregate-only signals worth reviewing."""

    flags: list[str] = []
    total_tokens = _number(row.get("total_tokens"))
    output_tokens = _number(row.get("output_tokens"))
    input_tokens = _number(row.get("input_tokens"))
    context = _number(row.get("context_window_percent"))
    cache = _number(row.get("cache_ratio"))
    reasoning = _number(row.get("reasoning_output_ratio"))
    cost = row.get("estimated_cost_usd")

    if context >= 0.8:
        flags.append("high context use")
    elif context >= 0.5:
        flags.append("elevated context use")
    if reasoning >= 0.75 and output_tokens >= 100:
        flags.append("high reasoning share")
    if input_tokens >= 10_000 and cache < 0.1:
        flags.append("low cache reuse")
    if total_tokens >= 20_000 and output_tokens <= 100:
        flags.append("expensive low-output call")
    if isinstance(cost, int | float) and cost >= 1:
        flags.append("high estimated cost")
    return flags


def _parse_models(raw: object) -> dict[str, dict[str, float]]:
    if not isinstance(raw, dict):
        raise ValueError("pricing config must be a JSON object")
    model_payload = raw.get("models", raw)
    if not isinstance(model_payload, dict):
        raise ValueError("pricing config 'models' must be an object")

    models: dict[str, dict[str, float]] = {}
    for model, rates in model_payload.items():
        if not isinstance(model, str):
            continue
        if model.startswith("_"):
            continue
        if not isinstance(rates, dict):
            continue
        parsed = {
            "input_per_million": _required_rate(rates, "input_per_million", model),
            "cached_input_per_million": _optional_rate(
                rates, "cached_input_per_million"
            ),
            "output_per_million": _required_rate(rates, "output_per_million", model),
        }
        if parsed["cached_input_per_million"] is None:
            parsed["cached_input_per_million"] = parsed["input_per_million"]
        models[model] = {key: float(value) for key, value in parsed.items()}
    return models


def _required_rate(rates: dict[str, Any], key: str, model: str) -> float:
    value = _optional_rate(rates, key)
    if value is None:
        raise ValueError(f"missing {key} for model {model}")
    return value


def _optional_rate(rates: dict[str, Any], key: str) -> float | None:
    value = rates.get(key)
    if value is None:
        return None
    parsed = _number(value)
    if parsed < 0:
        raise ValueError(f"{key} cannot be negative")
    return parsed


def _number(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0
