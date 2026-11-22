# Scenarios

All maps are ASCII strings in [`domain/scenarios.py`](../domain/scenarios.py), parsed by
`parse_map()`. Coordinates are `(x, y)`, `y = 0` is the top row.
Legend: `.` plain, `:` sand, `m` mud, `~` water, `s` slippery, `#` hazard, `R` restricted,
`K` keycard, `S` start, `G` goal.

## S1 — Open Field (8×8)

```text
S . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . G
```

Baseline. With uniform cost every shortest route costs 14. It shows that the strategies agree
on cost but differ greatly in effort.

## S2 — U-Trap (10×10)

```text
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
```

The U's mouth faces the start; the only way around is south. Manhattan distance points straight
into the cup. Greedy ignores the cost already paid, so it fills the tall cup before escaping.
A\* charges for the distance walked, so cup cells far from the start look expensive and it
turns south sooner.

## S3 — Weighted (10×10)

```text
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
```

Every shortest (18-move) route must cross mud. A 22-move plain road runs up the west edge,
along the top, and dips south around a mud ridge. The slippery band is crossed by every route
(so `SLIPPERY_MODE` fires for speed/swim states); one water tile and a sand patch add texture.
BFS minimizes moves and pays for mud; UCS and admissible A\* take the road.

## S4 — KeyDoor (12×12)

```text
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
```

The goal `(11,0)` is inside a 3×3 restricted room; the keycard is at `(0,11)` across a
2-wide river whose only bridge is the sand column at the far east. The cheapest plan (cost 49):
toggle to swim, swim straight down to the key, pick it up, walk back east and over the bridge,
then enter the room. A BFS over raw `(x, y)` cannot represent "has key" or "is swimming" and
finds no solution.

## Measured results

Path cost / path length (actions) / expanded nodes. All numbers are deterministic.

| Scenario | BFS | DFS | UCS | Greedy | A\* adm. | A\* inadm. |
|---|---|---|---|---|---|---|
| Open Field | 14 / 14 / 183 | 56 / 56 / 57 | 14 / 14 / 190 | 14 / 14 / 15 | 14 / 14 / 15 | 14 / 14 / 15 |
| U-Trap | 13 / 13 / 213 | 43 / 44 / 45 | 13 / 13 / 218 | 13 / 13 / 118 | 13 / 13 / 85 | 13 / 13 / 118 |
| Weighted | 27.5 / 18 / 291 | 258.5 / 88 / 89 | 22.5 / 22 / 253 | 27.5 / 18 / 19 | 22.5 / 22 / 102 | 27.5 / 18 / 19 |
| KeyDoor | 61 / 36 / 828 | 568 / 414 / 476 | 49 / 36 / 694 | 61 / 36 / 37 | 49 / 36 / 342 | 49 / 36 / 428 |

Highlights:

- **U-Trap:** Greedy expands 118 vs A\*'s 85 (≈1.4×).
- **Weighted:** BFS 27.5 > UCS = A\* 22.5; inadmissible A\* 27.5 with only 19 expansions.
- **KeyDoor:** full-state BFS solves it; `(x, y)` BFS does not.
