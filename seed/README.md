# PRAHARI Seed Data

All demo content lives here as **JSON files**. Edit these files to change what appears on the dashboard — no code changes needed.

## Quick start

1. Edit a scenario file in `scenarios/`
2. Set `active_scenario` in `config.json` to match the scenario `id`
3. Restart the backend (or call `POST /v1/demo/reload-seed`)
4. Click **Load Demo** on the dashboard

## File layout

| File | What it controls |
|------|------------------|
| `config.json` | Which scenario is active by default |
| `plant.json` | Plant name, zones, map layout, evacuation routes |
| `motifs.json` | Compound hazard patterns (P3 risk engine) |
| `users.json` | Demo login accounts |
| `regulatory.json` | OISD / Factory Act / DGMS citations |
| `incidents.json` | Historical precedent for evidence packages |
| `scenarios/*.json` | Full demo timelines + evidence templates |

## Switching scenarios

**Option A — config file**

```json
// seed/config.json
{ "active_scenario": "h2s-leak" }
```

**Option B — API**

```http
POST /v1/demo/load-scenario?scenario=h2s-leak
```

## Scenario file structure

Each file in `scenarios/` contains:

- `zone_id` — which zone the hazard plays out in
- `load_at_offset_minutes` — which timeline step loads when you click "Load Demo"
- `events[]` — timeline steps (sensor readings, permits, workers)
- `evidence` — narratives, agent text, root causes, recommendations (supports `{zone_id}`, `{ch4_lel}`, `{occupancy}` placeholders)
- `scorecard` — metrics shown on the Demo Scorecard page

## Example: change CH₄ level

Open `scenarios/coke-oven.json`, find the event at `offset_minutes: -40`, and edit:

```json
"updates": { "ch4_lel": 12.0, ... }
```

Save, reload seed, load demo again.

## Adding a new scenario

1. Copy `scenarios/coke-oven.json` → `scenarios/my-scenario.json`
2. Change `"id": "my-scenario"`
3. Edit events and evidence
4. Set `"active_scenario": "my-scenario"` in `config.json`
