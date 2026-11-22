"""Four hardcoded, deterministic scenarios, each defined as an ASCII map.

Legend: ``.`` plain, ``:`` sand, ``m`` mud, ``~`` water, ``s`` slippery, ``#`` hazard,
``R`` restricted (plain terrain), ``K`` keycard (plain), ``S`` start, ``G`` goal.
Coordinates are ``(x, y)`` with ``y = 0`` the top row. A goal inside a restricted
room is marked ``G`` and listed explicitly as restricted.
"""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType

from domain.models import Grid, Pos, Problem, State

TERRAIN_COST: MappingProxyType[str, float] = MappingProxyType(
    {"plain": 1.0, "sand": 2.0, "mud": 4.0, "water": 8.0, "slippery": 1.5}
)

_TERRAIN_CHARS = {".": "plain", ":": "sand", "m": "mud", "~": "water", "s": "slippery"}

OPEN_FIELD_MAP = """
S . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . G
"""

U_TRAP_MAP = """
. # # # # # # # # .
. . . . . . . . # .
. . . . . . . . # .
. . . . . . . . # .
. . . . . . . . # .
S . . . . . . . # G
. # # # # # # # # .
. . . . . . . . . .
. . . . . . . . . .
. . . . . . . . . .
"""

WEIGHTED_MAP = """
. . . . m m m . . G
. m m . m m m . m m
. m m . . . . . m m
. m m m m m m m m m
. m m m m m m m m m
s s s s s s s s s s
. m ~ m m m m m m m
. m m m m m m : : m
. m m m m m m : : m
S m m m m m m m m m
"""

KEY_DOOR_MAP = """
S . . . . . . . . R R G
. . . . . . . . . R R R
. . . . . . . . . R R R
. . . . . . . . . . . .
. . . . . . . . . . . .
~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ :
~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ :
. . . . . . . . . . . .
. . . . . . . . . . . .
. . . . . . . . . . . .
. . . . . . . . . . . .
K . . . . . . . . . . .
"""


def parse_map(text: str, extra_restricted: frozenset[Pos] = frozenset()) -> Grid:
    """Parse an ASCII map (space-separated cells) into a `Grid`."""
    rows = [line.split() for line in text.strip().splitlines()]
    height, width = len(rows), len(rows[0])
    if any(len(r) != width for r in rows):
        raise ValueError("ragged map")
    terrain: dict[Pos, str] = {}
    hazards: set[Pos] = set()
    restricted: set[Pos] = set(extra_restricted)
    items: dict[Pos, str] = {}
    start: Pos | None = None
    goal: Pos | None = None
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            pos = (x, y)
            terrain[pos] = _TERRAIN_CHARS.get(ch, "plain")
            if ch == "#":
                hazards.add(pos)
            elif ch == "R":
                restricted.add(pos)
            elif ch == "K":
                items[pos] = "keycard"
            elif ch == "S":
                start = pos
            elif ch == "G":
                goal = pos
            elif ch not in _TERRAIN_CHARS:
                raise ValueError(f"unknown map symbol {ch!r} at {pos}")
    if start is None or goal is None:
        raise ValueError("map needs both S and G")
    return Grid(
        width=width,
        height=height,
        terrain=terrain,
        hazards=frozenset(hazards),
        restricted=frozenset(restricted),
        items=items,
        start=start,
        goal=goal,
    )


def _problem(grid: Grid) -> Problem:
    return Problem(
        grid=grid,
        terrain_cost=dict(TERRAIN_COST),
        initial=State(pos=grid.start),
        goal_pos=grid.goal,
    )


def open_field() -> Problem:
    """S1: 8x8 all-plain baseline."""
    return _problem(parse_map(OPEN_FIELD_MAP))


def u_trap() -> Problem:
    """S2: hazard U whose mouth faces the start; the only way round is south."""
    return _problem(parse_map(U_TRAP_MAP))


def weighted() -> Problem:
    """S3: every 18-move path crosses mud; a 22-move plain road dips around a ridge."""
    return _problem(parse_map(WEIGHTED_MAP))


def key_door() -> Problem:
    """S4: goal in a keycard-locked room; a water river with a far sand bridge."""
    return _problem(parse_map(KEY_DOOR_MAP, extra_restricted=frozenset({(11, 0)})))


SCENARIOS: MappingProxyType[str, Callable[[], Problem]] = MappingProxyType(
    {
        "open_field": open_field,
        "u_trap": u_trap,
        "weighted": weighted,
        "key_door": key_door,
    }
)
