# Heuristics

Defined in [`reasoning/heuristics.py`](../reasoning/heuristics.py).

A heuristic `h(state, problem)` estimates the cheapest remaining cost to the goal. It is
**admissible** if `h(s) <= h*(s)` for every state `s`, where `h*` is the true optimal
cost-to-go. A\* with an admissible heuristic and goal test on pop returns an optimal path.

## h_admissible

```python
h_admissible(s) = min(terrain_cost) * manhattan(s.pos, goal)   # = 1.0 * manhattan
```

**Why admissible:** moves are cardinal, so at least `manhattan(pos, goal)` moves remain, and
each move costs at least the cheapest terrain cost (1.0). Zero-cost actions (pickup, toggle)
don't change position, so they can't shorten the distance. Hence `h <= h*`. It is also
consistent: one move changes Manhattan distance by at most 1 and costs at least 1.

## h_inadmissible

```python
h_inadmissible(s) = max(terrain_cost) * manhattan(s.pos, goal)   # = 8.0 * manhattan
```

**Why not admissible:** it prices every remaining step as water. On Weighted, the initial
state has Manhattan distance 18, so `h = 144`, while the true optimal cost is 22.5. Overestimates
make A\* behave greedily: it expands far fewer nodes (19 vs 102 on Weighted) but returns a
costlier path (27.5 vs 22.5).

## h_keydoor

```python
if "keycard" in s.inventory:   h = min_cost * manhattan(pos, goal)
else:                          h = min_cost * (manhattan(pos, key) + manhattan(key, goal))
```

**Why admissible:** while the key is not held, any route to the goal must visit the key cell
first (the goal is inside the restricted room). The cheapest such route is at least the
Manhattan distance to the key plus the Manhattan distance from the key to the goal, each step
costing at least `min_cost`. Once the key is held, it reduces to `h_admissible`. With several
keys it takes the minimum over keys; with none it falls back to `h_admissible`.

It **dominates** `h_admissible` on KeyDoor (33 vs 11 at the start), which is why A\* with it
expands 342 nodes vs UCS's 694.

## Which heuristic is used where

`select_heuristic(scenario, kind)` maps the UI toggle to a function:

| Toggle | KeyDoor | Other scenarios |
|---|---|---|
| Admissible | `h_keydoor` | `h_admissible` |
| Inadmissible | `h_inadmissible` | `h_inadmissible` |

The toggle only affects A\*. Greedy always uses the scenario's admissible heuristic.

## Verified in tests

`tests/test_heuristic.py` checks `h(s) <= true cost` on 20 evenly spaced reachable states of
Weighted and KeyDoor, computing the true cost with a fresh UCS from each state, and checks
`h_inadmissible(initial) > optimal` on Weighted.
