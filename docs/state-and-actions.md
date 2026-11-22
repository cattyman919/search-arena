# State, actions, and the problem

Defined in [`domain/models.py`](../domain/models.py).

## Grid (static world)

```python
@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    terrain: dict[Pos, str]      # "plain" | "sand" | "mud" | "water" | "slippery"
    hazards: frozenset[Pos]      # impassable
    restricted: frozenset[Pos]   # need the keycard
    items: dict[Pos, str]        # Pos -> "keycard"
    start: Pos
    goal: Pos
```

Coordinates are `(x, y)` with `y = 0` the **top** row (same as the ASCII maps and the plots).
Helpers: `terrain_at(pos)` (defaults to `"plain"`) and `in_bounds(pos)`.

## State (abstract search state)

```python
@dataclass(frozen=True)
class State:
    pos: Pos
    inventory: frozenset[str] = frozenset()
    mode: Mode = "normal"          # "normal" | "speed" | "swim"
```

The state contains **everything the rules depend on**. `inventory` matters for
`RESTRICTED_ZONE`, `mode` for `SLIPPERY_MODE` and `WATER_SWIM`. Because the dataclass is frozen
and its fields are hashable, states can be used directly as keys in `visited`, `best_g` and
`parent` dictionaries.

The state space size is `cells × 3 modes × 2^items`. On KeyDoor that is 144 × 3 × 2 = 864
states — small enough that every strategy finishes in milliseconds.

## Actions

```python
@dataclass(frozen=True)
class Action:
    kind: Literal["move", "pickup", "toggle_mode"]
    dx: int = 0
    dy: int = 0
    new_mode: Mode | None = None
```

| Action | Effect | Cost | Generated when |
|---|---|---|---|
| `move` | `pos += (dx, dy)`, cardinal only | `terrain_cost[terrain_at(target)]` | rule layer allows it |
| `pickup` | adds the item at `pos` to `inventory` | 0 | an item is here and not yet held |
| `toggle_mode` | `normal → speed → swim → normal` | 0 | always |

## Terrain costs

| Terrain | Cost | ASCII | Notes |
|---|---|---|---|
| plain | 1.0 | `.` | |
| slippery | 1.5 | `s` | only enterable in `normal` mode |
| sand | 2.0 | `:` | |
| mud | 4.0 | `m` | |
| water | 8.0 | `~` | only enterable in `swim` mode |

Other map symbols: `#` hazard, `R` restricted (plain), `K` keycard (plain), `S` start, `G` goal.

## Problem and goal test

```python
@dataclass(frozen=True)
class Problem:
    grid: Grid
    terrain_cost: dict[str, float]
    initial: State
    goal_pos: Pos
```

Goal test: `state.pos == problem.goal_pos`. Inventory and mode are irrelevant at the goal — the
rules already force a pickup when the goal is in a restricted zone.

## Modes

`speed` has no cost benefit in this version; it only makes slippery tiles impassable. It exists
so the `SLIPPERY_MODE` rule has something to block and so mode switching is a real part of the
state. See [design-decisions.md](design-decisions.md).
