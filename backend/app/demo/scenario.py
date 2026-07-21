"""Coke-oven gas + maintenance demo scenario (§6.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScenarioEvent:
    offset_minutes: int
    description: str
    updates: dict[str, Any]
    baseline_alert: bool
    prahari_alert: bool
    prahari_crs: float | None = None
    prahari_motif: str | None = None


COKE_OVEN_SCENARIO: list[ScenarioEvent] = [
    ScenarioEvent(
        offset_minutes=-110,
        description="CH₄ drifting up (~2-4% LEL); SCADA silent",
        updates={"ch4_lel": 2.5, "maintenance_active": False, "occupancy": 0},
        baseline_alert=False,
        prahari_alert=True,
        prahari_crs=35,
        prahari_motif="MAINT-GAS-OCCUPIED",
    ),
    ScenarioEvent(
        offset_minutes=-75,
        description="Scheduled maintenance job active in-zone",
        updates={
            "ch4_lel": 4.2,
            "maintenance_active": True,
            "active_permits": ["PTW-2231-HOTWORK"],
            "occupancy": 0,
        },
        baseline_alert=False,
        prahari_alert=True,
        prahari_crs=58,
        prahari_motif="MAINT-GAS-OCCUPIED",
    ),
    ScenarioEvent(
        offset_minutes=-40,
        description="Crew in zone; CH₄ ~8% LEL — still under 10% alarm",
        updates={
            "ch4_lel": 8.0,
            "maintenance_active": True,
            "active_permits": ["PTW-2231-HOTWORK"],
            "scheduled_permits": ["PTW-2240-CONFINED_ENTRY"],
            "occupancy": 3,
            "equipment_fault": True,
        },
        baseline_alert=False,
        prahari_alert=True,
        prahari_crs=86,
        prahari_motif="CS-HOTWORK-GAS",
    ),
    ScenarioEvent(
        offset_minutes=-10,
        description="Gas approaching flammable range; no coordinated response",
        updates={
            "ch4_lel": 15.0,
            "maintenance_active": True,
            "active_permits": ["PTW-2231-HOTWORK"],
            "scheduled_permits": ["PTW-2240-CONFINED_ENTRY"],
            "occupancy": 3,
            "equipment_fault": True,
        },
        baseline_alert=False,
        prahari_alert=True,
        prahari_crs=92,
        prahari_motif="CS-HOTWORK-GAS",
    ),
    ScenarioEvent(
        offset_minutes=0,
        description="T-0: Ignition → explosion (without intervention)",
        updates={
            "ch4_lel": 45.0,
            "maintenance_active": True,
            "active_permits": ["PTW-2231-HOTWORK"],
            "scheduled_permits": ["PTW-2240-CONFINED_ENTRY"],
            "occupancy": 3,
        },
        baseline_alert=True,
        prahari_alert=True,
        prahari_crs=98,
        prahari_motif="CS-HOTWORK-GAS",
    ),
]

SCENARIO_DURATION = 120  # minutes from -110 to +10


def get_scenario_at_offset(offset: int) -> ScenarioEvent | None:
    """Get the latest scenario event at or before the given offset."""
    applicable = [e for e in COKE_OVEN_SCENARIO if e.offset_minutes <= offset]
    return applicable[-1] if applicable else None
