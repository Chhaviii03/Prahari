"""Coke-oven gas + maintenance demo scenario — loaded from seed/scenarios/*.json."""

from __future__ import annotations

from app.seed.loader import ScenarioEvent, seed_data


def get_active_scenario():
    return seed_data.active_scenario


def get_scenario_at_offset(offset: int) -> ScenarioEvent | None:
    return seed_data.get_event_at_offset(offset)


def list_scenarios():
    return seed_data.list_scenarios()


def set_scenario(scenario_id: str):
    return seed_data.set_active_scenario(scenario_id)


def reload_seed():
    seed_data.reload()
