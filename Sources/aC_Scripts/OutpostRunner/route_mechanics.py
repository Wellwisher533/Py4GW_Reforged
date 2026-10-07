from __future__ import annotations

import math
from typing import Any
from typing import cast

PORTAL_EXTENSION_DISTANCE = 450.0


def _xy(data: dict[str, Any], key: str) -> tuple[float, float]:
    value = data[key]
    return float(value[0]), float(value[1])


def segment_steps(segment: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return ordered movement steps, preserving legacy path-only routes."""

    declared = segment.get("steps")
    if isinstance(declared, (list, tuple)):
        declared_steps = cast(list[object] | tuple[object, ...], declared)
        steps: list[dict[str, Any]] = []
        for step in declared_steps:
            if not isinstance(step, dict):
                raise TypeError("OutpostRunner route steps must be dictionaries")
            steps.append(cast(dict[str, Any], step).copy())
        return tuple(steps)
    path = list(segment.get("path", []))
    return ({"type": "path", "path": path},) if path else ()


def extended_portal_path(
    points: list[tuple[float, float]],
    extension_distance: float = PORTAL_EXTENSION_DISTANCE,
    approach_origin: tuple[float, float] | None = None,
) -> list[tuple[float, float]]:
    """Add a forward point beyond a captured portal edge when heading is known."""

    route = [(float(x), float(y)) for x, y in points]
    if not route:
        return route
    if len(route) >= 2:
        previous, endpoint = route[-2], route[-1]
    elif approach_origin is not None:
        previous = (float(approach_origin[0]), float(approach_origin[1]))
        endpoint = route[-1]
    else:
        return route
    dx = endpoint[0] - previous[0]
    dy = endpoint[1] - previous[1]
    length = math.hypot(dx, dy)
    if length <= 1.0:
        return route
    scale = float(extension_distance) / length
    return [
        *route,
        (endpoint[0] + dx * scale, endpoint[1] + dy * scale),
    ]


def register_outpost_departure(
    bot: Any,
    points: list[tuple[float, float]],
    target_map_id: int,
    step_name: str,
) -> None:
    """Register an outpost exit through the public movement owner."""

    bot.Move.FollowPathAndExitMap(
        extended_portal_path(points),
        target_map_id=target_map_id,
        step_name=step_name,
    )


def register_botting_segment(
    bot: Any,
    route_name: str,
    segment_index: int,
    segment: dict[str, Any],
    target_map_id: int = 0,
    resume_key_prefix: str = "",
) -> bool:
    """Register one shared movement segment and report whether it owns map travel."""

    steps = segment_steps(segment)
    owns_map_travel = False
    for step_index, step in enumerate(steps, start=1):
        step_type = str(step.get("type", "")).strip().lower()
        label = str(step.get("name") or f"{route_name} segment {segment_index + 1} step {step_index}")
        resume_key = f"{resume_key_prefix}:segment:{segment_index}:step:{step_index}" if resume_key_prefix else None
        if step_type == "path":
            points = list(step.get("path", []))
            if not points:
                continue
            if target_map_id and step_index == len(steps):
                portal_path = (
                    [*points, _xy(segment, "portal_exit_xy")]
                    if "portal_exit_xy" in segment
                    else extended_portal_path(points)
                )
                exit_kwargs: dict[str, Any] = {
                    "target_map_id": target_map_id,
                    "step_name": label,
                }
                if resume_key is not None:
                    exit_kwargs["resume_key"] = resume_key
                bot.Move.FollowPathAndExitMap(portal_path, **exit_kwargs)
                owns_map_travel = True
            else:
                path_kwargs: dict[str, Any] = {"step_name": label}
                if resume_key is not None:
                    path_kwargs["resume_key"] = resume_key
                bot.Move.FollowAutoPath(points, **path_kwargs)
            continue
        if step_type == "direct_path":
            points = list(step.get("path", []))
            if points:
                bot.Move.FollowPath(points, step_name=label)
            continue
        raise ValueError(
            f"Unsupported OutpostRunner route step type: {step_type!r}; "
            "shared interaction steps must use a public Py4GWCoreLib owner"
        )
    return owns_map_travel
