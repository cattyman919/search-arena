# Search strategies

Defined in [`reasoning/search.py`](../reasoning/search.py); entrypoint in
[`reasoning/trace.py`](../reasoning/trace.py).

## Shared building blocks

```python
successors(problem, state, log) -> list[tuple[Action, State, float]]
is_goal(state, problem) -> bool                  # state.pos == goal_pos
reconstruct(parent, goal_state) -> list[State]   # follow parent pointers, reverse
```

`successors` checks every move with `rules.allowed()` (recording verdicts in the log), then
adds `pickup` (if an unheld item is here) and `toggle_mode`. Order is fixed:
moves sorted by `(dx, dy)` → pickup → toggle_mode.

## Strategies

| Strategy | Frontier | Priority | Duplicate handling | Optimal? |
|---|---|---|---|---|
| BFS | FIFO deque | — | `visited` marked on push | fewest **actions**, not cost |
| DFS | LIFO stack | — | `visited` marked on pop, depth cap 500 | no |
| UCS | binary heap | `(g, counter)` | `best_g`, skip stale pops | yes |
| Greedy | binary heap | `(h, counter)` | `visited`, each state once | no |
| A\* | binary heap | `(g + h, h, counter)` | `best_g`, skip stale pops, reopen | yes if `h` admissible |

All strategies **stop when a goal state is popped**, never when it is enqueued; this is what
makes UCS and A\* optimal.

UCS, Greedy and A\* share one implementation, `_best_first(name, problem, log, priority,
reopen)`. `reopen=True` (UCS, A\*) re-queues a state whenever a cheaper `g` is found and skips
pops with `g > best_g[state]`; `reopen=False` (Greedy) expands each state at most once.

DFS pushes successors in reverse so that the first successor in canonical order is explored
first (moves before toggles); otherwise it would spend its first steps cycling modes.

A\* breaks `f` ties by lower `h` (prefer states closer to the goal), then insertion order. This
is standard and reduces expansions on plateaus of equal `f`.

## Determinism

- Fixed successor order (`KIND_RANK = {"move": 0, "pickup": 1, "toggle_mode": 2}`).
- Every heap entry ends with a monotonically increasing `counter`, so equal priorities pop in
  insertion order and states are never compared.
- No iteration over sets influences the returned path.

Tested: running every `(scenario, algorithm, heuristic)` twice yields identical `path` and
`expanded`.

## Safety caps

| Cap | Value |
|---|---|
| Expanded nodes | 200 000 |
| Frontier size | 100 000 |
| Wall clock | 5 s, checked every 2 000 expansions |

If a cap trips, the strategy returns a trace with `path = []`,
`stats["aborted"] = "cap_exceeded"` and the partial `expanded` list. In practice no scenario
comes close; the slowest run (BFS on KeyDoor) takes under 10 ms.

## SearchTrace

```python
@dataclass
class SearchTrace:
    algorithm: str          # "BFS", "DFS", "UCS", "Greedy", "A* (admissible)", "A* (inadmissible)"
    scenario: str
    path: list[State]       # empty if no solution
    expanded: list[State]   # expansion order; drives the animation
    frontier_sizes: list[int]
    rule_log: RuleLog
    stats: dict
```

| `stats` key | Meaning |
|---|---|
| `expanded` | nodes popped and expanded (`== len(expanded)`) |
| `generated` | successors produced |
| `path_cost` | sum of edge costs (0 if unsolved) |
| `path_len` | number of actions in the path (0 if unsolved) |
| `max_frontier` | peak frontier size |
| `runtime_ms` | wall clock |
| `optimal` | set by `annotate_optimality` |
| `aborted` | `None` or `"cap_exceeded"` |

## run() and annotate_optimality()

```python
run(scenario_name, algorithm, heuristic="admissible") -> SearchTrace
```

`algorithm` ∈ `bfs, dfs, ucs, greedy, astar`; `heuristic` ∈ `admissible, inadmissible`
(A\* only). It builds a fresh `Problem` and `RuleLog` each call.

```python
annotate_optimality(traces: dict[str, SearchTrace]) -> None
```

Sets `stats["optimal"] = solved and path_cost == UCS path_cost` (using `math.isclose`). If no
UCS trace is in the dict, it runs UCS on the same scenario. Unsolved traces are never optimal.
