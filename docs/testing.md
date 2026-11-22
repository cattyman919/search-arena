# Testing

Run with `make test` (or `uv run pytest -q`). 74 tests, about 0.5 s.

## Layout

| File | Covers |
|---|---|
| `tests/test_rules.py` | each rule blocks/allows correctly, evaluation order, `eval_rules`, `RuleLog` caps |
| `tests/test_heuristic.py` | admissibility on 20 sampled states, inadmissibility, `h_keydoor` dominance |
| `tests/test_search.py` | per-scenario comparisons, KeyDoor abstraction, trace invariants, determinism, unsolvable maps |
| `tests/test_trace.py` | `annotate_optimality`, rule-log consistency, KeyDoor block timing |

## What the key tests prove

- **Rules:** out-of-bounds, hazard, slippery (speed and swim), water and restricted are each
  blocked with the right rule name and message; when several would block, the first in order
  wins.
- **Admissibility:** for 20 evenly spaced reachable states on Weighted and KeyDoor,
  `h(s) <= true cost`, where the true cost is a fresh UCS from `s`.
- **Comparisons:**
  - Open Field: BFS, UCS and A\* have equal cost and length.
  - Weighted: UCS = A\*; BFS costs more but uses fewer moves; inadmissible A\* is costlier and
    expands no more than admissible A\*.
  - U-Trap: Greedy expands more nodes than A\*.
- **Abstraction:** full-state BFS solves KeyDoor; a control BFS over `(x, y)` only does not (and
  the control does solve Open Field, so it is a fair control). The UCS plan ends holding the key
  and passes through swim mode.
- **Trace invariants (every scenario × strategy):** not aborted; starts at the initial state;
  ends on the goal; every consecutive pair is a legal successor; summed edge costs equal
  `path_cost`; `stats["expanded"] == len(expanded)`; runtime < 500 ms.
- **Determinism:** each run repeated gives the identical path and expansion order.
- **Robustness:** with the goal walled off, every strategy returns an empty path with cost 0 and
  no abort.

## App checks

The UI is not unit-tested, but every commit was checked by launching Streamlit and hitting
`/_stcore/health`. During development the app was also driven headlessly with
`streamlit.testing.v1.AppTest` across all scenarios, heuristics and tabs.
