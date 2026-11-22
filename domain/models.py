"""Core data model: grid, abstract state, actions, and the search problem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Pos = tuple[int, int]
Mode = Literal["normal", "speed", "swim"]
ActionKind = Literal["move", "pickup", "toggle_mode"]

MODE_CYCLE: tuple[Mode, ...] = ("normal", "speed", "swim")


def next_mode(mode: Mode) -> Mode:
    """Return the mode after `mode` in the cycle normal -> speed -> swim -> normal."""
    return MODE_CYCLE[(MODE_CYCLE.index(mode) + 1) % len(MODE_CYCLE)]


@dataclass(frozen=True)
class Grid:
    """Static world layout. Cells missing from `terrain` are treated as plain."""

    width: int
    height: int
    terrain: dict[Pos, str]
    hazards: frozenset[Pos]
    restricted: frozenset[Pos]
    items: dict[Pos, str]
    start: Pos
    goal: Pos

    def terrain_at(self, pos: Pos) -> str:
        """Terrain type of `pos` (defaults to "plain")."""
        return self.terrain.get(pos, "plain")

    def in_bounds(self, pos: Pos) -> bool:
        """True if `pos` lies inside the grid."""
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height


@dataclass(frozen=True)
class State:
    """Abstract search state: position plus everything the rules depend on."""

    pos: Pos
    inventory: frozenset[str] = frozenset()
    mode: Mode = "normal"


@dataclass(frozen=True)
class Action:
    """An agent action. Moves are cardinal only (|dx| + |dy| == 1)."""

    kind: ActionKind
    dx: int = 0
    dy: int = 0
    new_mode: Mode | None = None


@dataclass(frozen=True)
class Problem:
    """A search problem: grid, terrain cost table, initial state, and goal cell."""

    grid: Grid
    terrain_cost: dict[str, float]
    initial: State
    goal_pos: Pos
