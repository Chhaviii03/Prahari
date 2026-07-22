"""Basic repository smoke tests (requires running Postgres)."""

from __future__ import annotations

import pytest

from app.db.repositories import ZoneRepository


@pytest.mark.asyncio
async def test_list_zones(db_session):
    repo = ZoneRepository(db_session)
    zones = await repo.list_zones("vsp_1")
    assert len(zones) >= 6
    assert any(z.id == "C-12" for z in zones)
