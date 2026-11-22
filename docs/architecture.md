# Architecture

## Layers

```text
┌──────────────────────────────────────────────────────────────┐
│ app.py  (Streamlit UI: sidebar + 4 tabs)                     │
└───────────────┬──────────────────────────────┬───────────────┘
                │                              │
                ▼                              ▼
┌───────────────────────────────┐  ┌──────────────────────────┐
│ reasoning/trace.py            │  │ viz/grid_render.py       │
│  run(), annotate_optimality() │  │  render_grid() -> Figure │
│  SearchTrace                  │  └──────────┬───────────────┘
└───────┬───────────────────────┘             │
        ▼                                     │
┌───────────────────────────────┐             │
│ reasoning/search.py           │             │
│  successors, bfs, dfs, ucs,   │             │
│  greedy, astar                │             │
└───────┬───────────────┬───────┘             │
        ▼               ▼                     │
┌────────────────┐ ┌─────────────────────┐    │
│ rules.py       │ │ heuristics.py       │    │
│ RULES, RuleLog │ │ h_admissible, ...   │    │
└───────┬────────┘ └─────────┬───────────┘    │
        ▼                   ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│ domain/models.py (Grid, State, Action, Problem)              │
│ domain/scenarios.py (ASCII maps, SCENARIOS registry)         │
└──────────────────────────────────────────────────────────────┘
```

Dependencies point downward only. `domain` imports nothing from the project; `reasoning`
imports `domain`; `viz` imports `domain` and `reasoning.trace`; `app.py` sits on top.

One intentional exception: `reasoning/search.py` imports `SearchTrace` from
`reasoning/trace.py`, and `trace.run()` needs the search functions. To avoid a circular import,
`run()` imports `reasoning.search`, `reasoning.heuristics` and `domain.scenarios` inside the
function body.

## Modules

| Module | Responsibility |
|---|---|
| `domain/models.py` | Frozen dataclasses for the world and the abstract state; `next_mode()` |
| `domain/scenarios.py` | `parse_map()` turns ASCII maps into `Grid`s; four scenario builders; `TERRAIN_COST` |
| `reasoning/rules.py` | Five rule functions, `eval_rules()`, `allowed()`, `RuleResult`, `RuleLog` |
| `reasoning/heuristics.py` | `manhattan`, `h_admissible`, `h_inadmissible`, `h_keydoor`, `select_heuristic` |
| `reasoning/search.py` | `successors`, `is_goal`, `reconstruct`, five strategies, shared caps |
| `reasoning/trace.py` | `SearchTrace`, `run()` entrypoint, `annotate_optimality()`, labels |
| `viz/grid_render.py` | One function, `render_grid()`, returning a matplotlib `Figure` |
| `app.py` | Session state, sidebar, tabs, animation loop, caching |

## Data flow for one comparison

1. The user picks a scenario, heuristic and algorithms in the sidebar and presses **Run**.
2. `_run_selected()` calls the cached `_run(scenario, algorithm, heuristic)` for each algorithm.
3. `_run` calls `reasoning.trace.run()`, which builds a fresh `Problem` from `SCENARIOS`, a fresh
   `RuleLog`, chooses the heuristic, and calls the strategy.
4. The strategy repeatedly calls `successors()`, which asks `rules.allowed()` about each move;
   every rule verdict is recorded in the `RuleLog`.
5. The strategy returns a `SearchTrace` (path, expansion order, frontier sizes, rule log, stats).
6. `annotate_optimality()` compares every trace's cost with the UCS cost.
7. The tabs render the traces: grids via `render_grid()`, tables via pandas.

## No global mutable state

Scenario builders return a new `Problem` every call. Module-level tables (`TERRAIN_COST`,
`SCENARIOS`) are `MappingProxyType` (read-only). Each `run()` creates its own `RuleLog`. This
makes the app safe to cache and every result reproducible.
