from __future__ import annotations

import math

from Py4GWCoreLib import Agent


def overcast_from_energy_caps(
    full_energy: float,
    effective_energy: float,
    second_full_energy: float,
    wrapper_full_energy: float,
) -> tuple[float, float] | None:
    """Derive Overcast from the player's measured full and usable energy caps."""
    values = (
        full_energy,
        effective_energy,
        second_full_energy,
        wrapper_full_energy,
    )
    if not all(math.isfinite(float(value)) for value in values):
        return None
    full = float(full_energy)
    effective = float(effective_energy)
    if full <= 0.0 or effective > full + 1.0:
        return None
    if abs(full - float(second_full_energy)) > 1.0:
        return None
    if abs(full - float(wrapper_full_energy)) > 1.0:
        return None
    return max(0.0, full - effective), effective


def read_player_overcast_state(player_id: int) -> tuple[float, float] | None:
    """Read the map-agent energy cap; never substitute the known-zero wrapper."""
    try:
        from Py4GWCoreLib.Context import GWContext

        world = GWContext.World.GetContext()
        map_agents = world.map_agents if world is not None else None
        if map_agents is None or player_id <= 0 or player_id >= len(map_agents):
            return None
        record = map_agents[player_id]
        return overcast_from_energy_caps(
            record.max_energy2,
            record.h0010,
            record.max_energy,
            Agent.GetMaxEnergy(player_id),
        )
    except (AttributeError, IndexError, TypeError, ValueError):
        return None
