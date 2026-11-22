# Search Arena

Search Arena puts five search strategies side by side on the same small grid worlds: BFS, DFS,
Uniform-Cost Search, Greedy Best-First and A\*. A\* runs with either an admissible or an
inadmissible heuristic. The agent's world is symbolic. A state is an abstract triple
`(pos, inventory, mode)`, and legal moves are decided by five declarative constraint rules that
can explain why an action was blocked. Everything is local, deterministic and hardcoded, with no
network, database or LLM calls, so every number in this README can be reproduced exactly.

## How it maps to the lecture

- **Abstract state representation:** `State(pos, inventory, mode)` in
  [`domain/models.py`](domain/models.py). The KeyDoor scenario can't be solved without it.
- **Declarative constraint rules:** five independent `(state, action) -> verdict` rules in
  [`reasoning/rules.py`](reasoning/rules.py), evaluated in a fixed order and logged with reasons.
- **Search strategies:** BFS, DFS, UCS, Greedy and A\* in
  [`reasoning/search.py`](reasoning/search.py), all sharing one successor function.
- **Admissibility:** `h_admissible`, `h_inadmissible` and `h_keydoor` in
  [`reasoning/heuristics.py`](reasoning/heuristics.py), each with its argument in the docstring.
- **Optimality:** `annotate_optimality` in [`reasoning/trace.py`](reasoning/trace.py) compares
  every path cost with the UCS cost.

## Setup

Requires [uv](https://docs.astral.sh/uv/). uv fetches Python 3.12 if needed.

```bash
uv sync                        # or: make install
uv run streamlit run app.py    # or: make run
uv run pytest -q               # or: make test
```

Other targets: `make lint` (ruff), `make typecheck` (mypy), `make check` (lint, types and tests),
`make format`, `make clean`. Run `make` on its own to list them.

## Architecture

```text
search-arena/
  app.py                  Streamlit UI: sidebar + 4 tabs (Arena, Metrics, Heuristics, Explainer)
  domain/
    models.py             Grid, State, Action, Problem (frozen dataclasses)
    scenarios.py          4 ASCII-defined scenarios + SCENARIOS registry
  reasoning/
    rules.py              5 constraint rules, eval_rules / allowed, RuleLog
    heuristics.py         manhattan, h_admissible, h_inadmissible, h_keydoor
    search.py             successors, bfs, dfs, ucs, greedy, astar (+ safety caps)
    trace.py              SearchTrace, run(), annotate_optimality()
  viz/
    grid_render.py        render_grid() -> matplotlib Figure
  tests/                  rules, heuristics, search, trace (pytest)

  app.py ──> reasoning.trace.run ──> reasoning.search ──> reasoning.rules ──> domain.models
     │                                      └──> reasoning.heuristics
     └──> viz.grid_render ──> domain + reasoning.trace
```

## State model

```python
@dataclass(frozen=True)
class State:
    pos: tuple[int, int]
    inventory: frozenset[str] = frozenset()  # e.g. {"keycard"}
    mode: Literal["normal", "speed", "swim"] = "normal"


@dataclass(frozen=True)
class Action:
    kind: Literal["move", "pickup", "toggle_mode"]
    dx: int = 0  # move: one of the 4 cardinal directions
    dy: int = 0
    new_mode: Mode | None = None  # toggle_mode: normal -> speed -> swim -> normal
```

A move costs the terrain cost of the target cell: plain 1, slippery 1.5, sand 2, mud 4, water 8.
`pickup` and `toggle_mode` cost 0. The goal test is `state.pos == goal`.

## Rules

Rules are evaluated in this order, and the first block wins.

| Rule | Trigger | Effect |
|---|---|---|
| `WALL_BOUNDS` | `move` | blocks if the target is outside the grid: *"blocked: out of bounds"* |
| `HAZARD` | `move` into a hazard | blocks: *"blocked: hazard tile"* |
| `SLIPPERY_MODE` | `move` into slippery | allowed only in `normal`: *"blocked: SlipperyTile unsafe in SpeedMode"* |
| `WATER_SWIM` | `move` into water | allowed only in `swim`: *"blocked: water requires SwimMode"* |
| `RESTRICTED_ZONE` | `move` into restricted | needs the keycard: *"blocked: RestrictedZone requires KeyCard"* |

`RuleLog` keeps full-run `counts` and `blocked_counts` for every rule. It stores at most 500 entries:
up to 80 blocks and 20 sample passes per rule, so one noisy rule can't crowd out the others.

## Heuristics

- `h_admissible = min_step_cost × manhattan = 1.0 × manhattan`. Every step costs at least 1.0
  and at least `manhattan` steps remain, so it never overestimates.
- `h_inadmissible = max_step_cost × manhattan = 8.0 × manhattan`. It prices every step as water,
  so on plain terrain it overestimates by up to 8× and A\* can return a costlier path.
- `h_keydoor = manhattan(pos, key) + manhattan(key, goal)` until the key is held, then
  `manhattan(pos, goal)`. Any real route has to pass the key first, so this is still a lower bound,
  and a tighter one. It is the admissible heuristic used on KeyDoor.

## Search strategies

- **BFS:** FIFO queue. Minimizes the number of actions, not the cost.
- **DFS:** LIFO stack with a depth cap of 500. Explores successors in their fixed order, so its
  paths are reproducible but usually long.
- **UCS:** priority on `g`, skipping stale entries. Optimal, and the reference for "Optimal".
- **Greedy:** priority on `h` only. Fast, but may be suboptimal and can be lured into traps.
- **A\*:** priority on `f = g + h`, with ties broken by lower `h` and then insertion order. The
  goal test happens on pop, so the result is optimal when `h` is admissible.

Every strategy stops when a goal state is popped. Each enforces a 200k expansion cap, a 100k
frontier cap and a 5 s wall-clock guard, returns `stats["aborted"] = "cap_exceeded"` instead of
hanging, and returns:

```python
@dataclass
class SearchTrace:
    algorithm: str  # "BFS", "DFS", "UCS", "Greedy", "A* (admissible)", ...
    scenario: str
    path: list[State]  # empty if no solution
    expanded: list[State]  # expansion order (drives the animation)
    frontier_sizes: list[int]
    rule_log: RuleLog
    stats: dict  # expanded, generated, path_cost, path_len, max_frontier,
    # runtime_ms, optimal, aborted
```

## Scenarios

All four maps are ASCII strings in [`domain/scenarios.py`](domain/scenarios.py).

**Open Field (8×8).** All plain, from `(0,0)` to `(7,7)`. This is the baseline: BFS, UCS, Greedy
and both A\* variants reach the same cost of 14. Expansion counts still differ (UCS 190, BFS 183,
A\* 15). DFS wanders to a cost of 56.

**U-Trap (10×10).** A hazard U whose mouth faces the start, with the only way round to the south.
Manhattan distance pulls the search into the cup. Greedy fills it before escaping (118
expansions), while A\* with the admissible heuristic charges for the distance already walked and
needs only 85 (1.4× fewer). Both find the optimal cost of 13. A simple U on a uniform 10×10 grid
can't produce a larger gap, because A\* also has to look inside the cup.

**Weighted (10×10).** From `(0,9)` to `(9,0)`. Every shortest route, at 18 moves, has to cross mud
(cost 4). A 22-move plain road dips round a mud ridge. A slippery band crosses both routes, and
there is one water tile and a patch of sand. BFS picks a mud route (cost 27.5). UCS and A\*
(admissible) take the road (cost 22.5). A\* (inadmissible) rushes through the mud: cost 27.5, but
only 19 expansions against 102.

**KeyDoor (12×12).** The start is `(0,0)`. The goal `(11,0)` sits inside a 3×3 restricted room. The
keycard is at `(0,11)`, on the other side of a two-tile-wide river whose only bridge is at the far
east edge. The cheapest plan (cost 49) switches to swim mode, swims straight down to the key, picks
it up, walks back over the bridge and enters the room. A BFS over raw `(x, y)` that drops inventory
and mode has no solution; this control is tested in `tests/test_search.py`.

## Demo script

1. **Open Field + all 5 algorithms.** Identical path cost (14) for everything except DFS. Point
   out how differently many nodes each one expanded.
2. **U-Trap + Greedy vs A\*.** Press Play. Greedy floods the cup and expands 118 nodes, about 1.4×
   A\*'s 85.
3. **Weighted + BFS vs UCS vs A\* (admissible).** BFS takes the fewest moves (18, cost 27.5). UCS
   and A\* take the cheapest route (22 moves, cost 22.5).
4. **Switch the heuristic to Inadmissible** and press Run, or open the Heuristic Comparison tab.
   On the same grid, the path cost rises from 22.5 to 27.5 and expansions drop from 102 to 19.
5. **KeyDoor + BFS.** In the rule log (Arena tab), filter to `RESTRICTED_ZONE`: `blocked: RestrictedZone requires KeyCard`
   only for states without the key. Once the key is held, no restricted-zone blocks appear.
6. **Explainer tab:** summarizes state, rules and admissibility.

## Limitations and possible extensions

- The maps are tiny and hand-made. A procedural generator with a fixed seed would allow
  benchmarks.
- `speed` mode has no benefit yet; it only adds a constraint. A real speed bonus (cheaper plain
  moves) would make mode choice a genuine trade-off.
- Hazards are walls. "Damage" tiles with a health component in the state are a natural extension.
- The heuristics are Manhattan-based. A pattern-database or relaxed-problem heuristic could
  demonstrate dominance.
- The animation re-renders matplotlib figures (~75 ms each). An image cache or a canvas renderer
  would make playback smoother.
- Further strategies (IDA\*, weighted A\*, bidirectional search) would fit the shared interface.

## Git workflow used

The history follows the milestone plan: one Conventional Commit per milestone (`chore:`, `feat:`,
`test:`, `docs:`), in the imperative mood. Before each commit, `make check` (ruff, mypy, pytest)
was green and the Streamlit app launched. Nothing was amended or force-pushed. `.venv/`, caches
and OS files are ignored. See `git log --oneline`.
