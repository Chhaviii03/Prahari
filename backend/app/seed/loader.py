"""Load all demo data from seed/*.json files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models.schemas import HistoricalReference, RegulatoryCitation, UserRole

SEED_DIR = Path(__file__).resolve().parents[3] / "seed"


@dataclass
class ScenarioEvent:
    offset_minutes: int
    description: str
    updates: dict[str, Any]
    baseline_alert: bool
    prahari_alert: bool
    prahari_crs: float | None = None
    prahari_motif: str | None = None


@dataclass
class LoadedScenario:
    id: str
    name: str
    description: str
    zone_id: str
    load_at_offset_minutes: int
    duration_minutes: int
    scorecard: dict[str, Any]
    events: list[ScenarioEvent]
    evidence: dict[str, Any]


class SeedData:
  def __init__(self, seed_dir: Path | None = None):
    self.seed_dir = seed_dir or SEED_DIR
    self._config: dict[str, Any] = {}
    self._plant: dict[str, Any] = {}
    self._motifs: list[dict[str, Any]] = []
    self._users: list[dict[str, Any]] = []
    self._regulatory: list[dict[str, Any]] = []
    self._incidents: list[dict[str, Any]] = []
    self._scenarios: dict[str, LoadedScenario] = {}
    self._active_scenario_id: str = "coke-oven"
    self.reload()

  def reload(self) -> None:
    self._config = self._read_json("config.json")
    self._plant = self._read_json(self._config.get("plant_file", "plant.json"))
    motifs_data = self._read_json(self._config.get("motifs_file", "motifs.json"))
    self._motifs = motifs_data.get("motifs", [])
    users_data = self._read_json(self._config.get("users_file", "users.json"))
    self._users = users_data.get("users", [])
    reg_data = self._read_json(self._config.get("regulatory_file", "regulatory.json"))
    self._regulatory = reg_data.get("citations", [])
    inc_data = self._read_json(self._config.get("incidents_file", "incidents.json"))
    self._incidents = inc_data.get("incidents", [])
    self._scenarios = {}
    scenarios_dir = self.seed_dir / "scenarios"
    if scenarios_dir.exists():
      for path in sorted(scenarios_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        self._scenarios[data["id"]] = self._parse_scenario(data)
    self._active_scenario_id = self._config.get("active_scenario", "coke-oven")

  def _read_json(self, filename: str) -> dict[str, Any]:
    path = self.seed_dir / filename
    if not path.exists():
      return {}
    return json.loads(path.read_text(encoding="utf-8"))

  def _parse_scenario(self, data: dict[str, Any]) -> LoadedScenario:
    events = [
      ScenarioEvent(
        offset_minutes=e["offset_minutes"],
        description=e["description"],
        updates=e.get("updates", {}),
        baseline_alert=e.get("baseline_alert", False),
        prahari_alert=e.get("prahari_alert", False),
        prahari_crs=e.get("prahari_crs"),
        prahari_motif=e.get("prahari_motif"),
      )
      for e in data.get("events", [])
    ]
    return LoadedScenario(
      id=data["id"],
      name=data["name"],
      description=data.get("description", ""),
      zone_id=data.get("zone_id", "C-12"),
      load_at_offset_minutes=data.get("load_at_offset_minutes", -40),
      duration_minutes=data.get("duration_minutes", 120),
      scorecard=data.get("scorecard", {}),
      events=events,
      evidence=data.get("evidence", {}),
    )

  @property
  def plant(self) -> dict[str, Any]:
    return self._plant

  @property
  def motifs(self) -> list[dict[str, Any]]:
    return self._motifs

  @property
  def users(self) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for u in self._users:
      entry = {k: v for k, v in u.items() if k != "username"}
      entry["role"] = UserRole(u["role"])
      result[u["username"]] = entry
    return result

  @property
  def regulatory_corpus(self) -> list[RegulatoryCitation]:
    return [RegulatoryCitation(**c) for c in self._regulatory]

  @property
  def historical_incidents(self) -> list[HistoricalReference]:
    return [HistoricalReference(**i) for i in self._incidents]

  @property
  def active_scenario(self) -> LoadedScenario:
    return self._scenarios.get(self._active_scenario_id) or next(iter(self._scenarios.values()))

  def set_active_scenario(self, scenario_id: str) -> LoadedScenario:
    if scenario_id not in self._scenarios:
      raise KeyError(f"Unknown scenario: {scenario_id}. Available: {list(self._scenarios.keys())}")
    self._active_scenario_id = scenario_id
    return self._scenarios[scenario_id]

  def list_scenarios(self) -> list[dict[str, str]]:
    return [
      {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "zone_id": s.zone_id,
        "active": s.id == self._active_scenario_id,
      }
      for s in self._scenarios.values()
    ]

  def get_scenario(self, scenario_id: str | None = None) -> LoadedScenario:
    if scenario_id:
      return self._scenarios[scenario_id]
    return self.active_scenario

  def get_event_at_offset(self, offset: int, scenario_id: str | None = None) -> ScenarioEvent | None:
    scenario = self.get_scenario(scenario_id) if scenario_id else self.active_scenario
    applicable = [e for e in scenario.events if e.offset_minutes <= offset]
    return applicable[-1] if applicable else None


seed_data = SeedData()
