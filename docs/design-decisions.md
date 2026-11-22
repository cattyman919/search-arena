# Design decisions and deviations from the brief

The original assignment brief fixed most of the design. This page records where the
implementation differs and why.

## U-Trap geometry and the size of the Greedy/A\* gap

The brief asked for a symmetric U with "Greedy expands ~5× more than A\*". On a uniform
4-connected grid with the start on the goal's row, every cup cell has `f < C*`, so A\* also
expands the whole cup; the symmetric U measured Greedy 125 vs A\* 135 — the wrong way round.

About 1 000 U-shaped variants on 10×10 were searched automatically. The best is the current
asymmetric U (tall cup to the north, short way round to the south): **Greedy 118 vs A\* 85,
≈1.4×**. No simple U on 10×10 reaches 5×, so the README and tests use the measured gap
(`greedy.expanded > astar.expanded`).

## A\* tie-breaking on h

A\* priority is `(f, h, counter)` rather than `(f, counter)`. The counter is still last, so
ordering stays deterministic. Preferring lower `h` among equal `f` is standard and keeps A\*
from exploring whole plateaus of equal `f`. Without it, A\* still beats Greedy on U-Trap
(109 vs 118), just by less.

## Weighted: no "10-step diagonal"

The brief described a ~10-step diagonal through mud vs an ~18-step detour. With cardinal moves
only, every path from `(0,9)` to `(9,0)` needs at least 18 moves, so a 10-step route cannot exist.
The map instead makes every 18-move route cross mud (cheapest 27.5 for BFS's choice) and offers a
22-move plain road (22.5). This keeps the intended lesson: BFS minimizes moves, UCS/A\* minimize
cost.

## KeyDoor start position

The brief did not specify one; `(0,0)` was chosen so the agent must cross the river to reach the
key and come back, making both the swim mode and the keycard essential.

## Open Field "identical metrics"

Costs are identical (except DFS), but expansion counts differ (15 to 190) because the strategies
explore differently. The demo script says "identical path cost".

## Mode toggles and `speed`

`toggle_mode` is free and always available, which triples the state space. `speed` has no cost
effect in the brief, so it only restricts movement (slippery). This is faithful to the brief and
noted as an extension point.

## DFS successor order

DFS pushes successors in reverse so the first successor in canonical order (a move) is explored
first. Pushing in natural order would make DFS cycle through modes before moving.

## Rule log cap per rule

The brief caps the log at 500 entries. A single shared cap fills up with `WALL_BOUNDS` and
`WATER_SWIM` blocks before any `RESTRICTED_ZONE` block on KeyDoor, which would break the demo.
The cap is therefore split per rule (80 blocks + 20 allowed samples × 5 rules = 500). The UI also
filters blocks by rule.

## Animation timing

The brief described a loop incrementing the step by `max_step // 60`. With five matplotlib grids
per frame (~75 ms each), that would take far longer than 3 s. The step is instead derived from
elapsed time, so playback always ends in about 3 s.

## Extras not in the brief

- `Makefile` for common tasks.
- `ruff` and `mypy` as dev dependencies, with every commit passing both.
- `pandas` declared explicitly (it was only a transitive dependency of Streamlit).
- `.streamlit/config.toml` disabling usage statistics, to honour "no network calls".
- Python pinned to 3.12 via `.python-version` (`requires-python >= 3.11`).
- Two extra commits: a separate dependency commit (per the brief's own start-up steps) and the
  rule-log filter.
