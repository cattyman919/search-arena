"""Heuristics for informed search, with their admissibility arguments."""

from __future__ import annotations

from collections.abc import Callable

from domain.models import Pos, Problem, State


def manhattan(a: Pos, b: Pos) -> int:
    """Manhattan (L1) distance between two cells."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def h_admissible(state: State, problem: Problem) -> float:
    """min_step_cost * manhattan(pos, goal).

    Every move costs at least min_step_cost (1.0) and at least manhattan(pos, goal) moves
    remain, so this never overestimates: admissible (and consistent).
    """
    return min(problem.terrain_cost.values()) * manhattan(state.pos, problem.goal_pos)


def h_inadmissible(state: State, problem: Problem) -> float:
    """max_step_cost * manhattan(pos, goal).

    Assumes every remaining step costs as much as water (8.0). On plain terrain this
    overestimates by up to 8x, so it is NOT admissible and A* may return a costlier path.
    """
    return max(problem.terrain_cost.values()) * manhattan(state.pos, problem.goal_pos)


def h_keydoor(state: State, problem: Problem) -> float:
    """Admissible heuristic that accounts for fetching the keycard.

    With the keycard: min_step * manhattan(pos, goal). Without it, the agent must visit
    the key first: min_step * (manhattan(pos, key) + manhattan(key, goal)) is a lower
    bound on any route that passes the key. Falls back to `h_admissible` if the grid has
    no keycard.
    """
    keys = sorted(p for p, item in problem.grid.items.items() if item == "keycard")
    if "keycard" in state.inventory or not keys:
        return h_admissible(state, problem)
    step = min(problem.terrain_cost.values())
    legs = min(manhattan(state.pos, k) + manhattan(k, problem.goal_pos) for k in keys)
    return step * legs


def select_heuristic(scenario: str, kind: str) -> Callable[[State, Problem], float]:
    """Map the UI toggle ("admissible" / "inadmissible") to a heuristic function.

    On ``key_door`` the admissible choice is `h_keydoor`; elsewhere `h_admissible`.
    """
    if kind == "inadmissible":
        return h_inadmissible
    if kind != "admissible":
        raise ValueError(f"unknown heuristic {kind!r}")
    return h_keydoor if scenario == "key_door" else h_admissible
