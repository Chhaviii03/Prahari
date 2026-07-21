"""Digital Twin - Platform 2 with simple linear forecasting."""

from __future__ import annotations

from datetime import datetime

from app.models.schemas import PlantTopology, ZoneState


PLANT_ZONES = [
    {"zone_id": "C-10", "name": "Coke Oven Battery A", "zone_class": "PROCESS", "geo": {"x": 80, "y": 60, "level": "G"}},
    {"zone_id": "C-11", "name": "Coke Oven Battery B", "zone_class": "PROCESS", "geo": {"x": 120, "y": 60, "level": "G"}},
    {"zone_id": "C-12", "name": "Gas Line Maintenance Zone", "zone_class": "CONFINED_SPACE", "geo": {"x": 160, "y": 90, "level": "G"}},
    {"zone_id": "C-13", "name": "Melt Shop Entry", "zone_class": "PROCESS", "geo": {"x": 200, "y": 120, "level": "G"}},
    {"zone_id": "C-14", "name": "Storage Yard", "zone_class": "OPEN", "geo": {"x": 60, "y": 140, "level": "G"}},
    {"zone_id": "C-15", "name": "Control Room Annex", "zone_class": "ADMIN", "geo": {"x": 240, "y": 50, "level": "G"}},
]


def _linear_forecast(values: list[float], steps: int = 24) -> tuple[list[float], int | None]:
    """Simple linear extrapolation (Holt-style, explainable)."""
    if len(values) < 2:
        v = values[-1] if values else 0
        return [v], None

    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n)) or 1
    slope = num / den
    intercept = y_mean - slope * x_mean

    trajectory = [round(max(0, intercept + slope * (n + i)), 2) for i in range(steps)]
    threshold_eta = None
    for i, v in enumerate(trajectory):
        if v >= 100:
            threshold_eta = (i + 1) * 5
            break
        if v >= 20 and threshold_eta is None:
            threshold_eta = (i + 1) * 5

    return trajectory, threshold_eta


class DigitalTwin:
    def __init__(self, plant_id: str = "vsp_1", plant_name: str = "Visakhapatnam Steel Plant"):
        self.plant_id = plant_id
        self.plant_name = plant_name
        self.zones: dict[str, ZoneState] = {}
        self.history: dict[str, list[tuple[datetime, float]]] = {}
        self._init_zones()

    def _init_zones(self) -> None:
        for z in PLANT_ZONES:
            self.zones[z["zone_id"]] = ZoneState(
                zone_id=z["zone_id"],
                name=z["name"],
                zone_class=z["zone_class"],
                geo=z["geo"],
            )
            self.history[z["zone_id"]] = []

    def update_zone(self, zone_id: str, **kwargs) -> ZoneState:
        zone = self.zones[zone_id]
        data = zone.model_dump()
        data.update(kwargs)
        updated = ZoneState(**data)
        self.zones[zone_id] = updated

        if "ch4_lel" in kwargs:
            self.history[zone_id].append((datetime.utcnow(), kwargs["ch4_lel"]))

        return updated

    def forecast_ch4(self, zone_id: str, horizon_minutes: int = 120) -> dict:
        history = self.history.get(zone_id, [])
        current = self.zones[zone_id].ch4_lel

        if len(history) < 2:
            if current < 1:
                return {"trajectory": [current], "threshold_eta": None, "confidence": 0.3}
            rate = 0.4
            eta = int((100 - current) / rate * 5) if current < 100 else 0
            return {"trajectory": [current], "threshold_eta": eta, "confidence": 0.6}

        values = [v for _, v in history[-20:]]
        steps = min(horizon_minutes // 5, 24)
        trajectory, threshold_eta = _linear_forecast(values, steps)

        return {
            "trajectory": trajectory,
            "threshold_eta": threshold_eta,
            "confidence": 0.86 if len(values) >= 5 else 0.6,
        }

    def refresh_forecasts(self) -> None:
        for zone_id, zone in self.zones.items():
            if zone.ch4_lel > 0 or len(self.history.get(zone_id, [])) > 0:
                fc = self.forecast_ch4(zone_id)
                self.update_zone(zone_id, forecast_eta_minutes=fc.get("threshold_eta"))

    def get_topology(self) -> PlantTopology:
        return PlantTopology(plant_id=self.plant_id, name=self.plant_name, zones=list(self.zones.values()))

    def get_zone(self, zone_id: str) -> ZoneState | None:
        return self.zones.get(zone_id)

    def get_heatmap_data(self) -> dict:
        workers = []
        permits = []
        for zone in self.zones.values():
            for i in range(zone.occupancy):
                workers.append({
                    "worker_id": f"W-{zone.zone_id}-{i+1}",
                    "zone_id": zone.zone_id,
                    "x": zone.geo.get("x", 0) + (i * 8),
                    "y": zone.geo.get("y", 0) + 10,
                    "name": f"Worker {i+1}",
                })
            for p in zone.active_permits:
                permits.append({"permit_id": p, "zone_id": zone.zone_id, "status": "ACTIVE", "type": p.split("-")[0] if "-" in p else "PERMIT"})
            for p in zone.scheduled_permits:
                permits.append({"permit_id": p, "zone_id": zone.zone_id, "status": "SCHEDULED", "type": p.split("-")[0] if "-" in p else "PERMIT"})

        return {
            "plant_id": self.plant_id,
            "zones": list(self.zones.values()),
            "workers": workers,
            "permits": permits,
            "evacuation_routes": [
                {"from_zone": "C-12", "route": [{"x": 160, "y": 90}, {"x": 140, "y": 60}, {"x": 100, "y": 40}]},
            ],
        }
