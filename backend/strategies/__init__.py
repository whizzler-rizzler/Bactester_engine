"""Strategy registry.

Each strategy exposes a `name`, a pydantic `Params` model, and a
`build(params)` factory returning a Strategy instance. The registry below is
what the API uses to list strategies and validate incoming params.
"""
from __future__ import annotations

from backend.strategies.base import Strategy
from backend.strategies import ladder_bot

REGISTRY: dict[str, dict] = {
    ladder_bot.NAME: {
        "name": ladder_bot.NAME,
        "description": ladder_bot.DESCRIPTION,
        "params_model": ladder_bot.LadderBotParams,
        "build": ladder_bot.build,
        "defaults": ladder_bot.LadderBotParams().model_dump(),
        "schema": ladder_bot.LadderBotParams.model_json_schema(),
    },
}


def list_strategies() -> list[dict]:
    return [
        {
            "name": v["name"],
            "description": v["description"],
            "defaults": v["defaults"],
            "schema": v["schema"],
        }
        for v in REGISTRY.values()
    ]


def build_strategy(name: str, raw_params: dict) -> tuple[Strategy, dict]:
    if name not in REGISTRY:
        raise KeyError(f"Unknown strategy: {name}")
    entry = REGISTRY[name]
    params = entry["params_model"](**raw_params)
    return entry["build"](params), params.model_dump()


__all__ = ["REGISTRY", "list_strategies", "build_strategy", "Strategy"]
