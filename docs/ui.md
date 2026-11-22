# Streamlit UI

Defined in [`app.py`](../app.py); rendering in [`viz/grid_render.py`](../viz/grid_render.py).
Launch with `make run` (or `uv run streamlit run app.py`).

## Sidebar

- **Scenario** — Open Field, U-Trap, Weighted, KeyDoor.
- **Heuristic** — Admissible / Inadmissible (affects A\* only).
- **Algorithms** — any of BFS, DFS, UCS, Greedy, A\* (default UCS, Greedy, A\*).
- **Run** — clears previous traces, resets the animation, runs every selected algorithm.

Sidebar changes take effect when **Run** is pressed. On first load the default selection runs
automatically so the page is never empty.

## Tabs

**Arena.** One grid per algorithm, side by side, with a shared *Animation step* slider and
Play / Stop buttons. Under each grid: path cost, length, expansions, runtime and max frontier
(red `ABORTED` if a cap tripped, an error if no solution). Below, the *Rule log* expander shows
evaluation/block counts per rule for a chosen trace and the first 10 blocked actions, filterable
by rule.

The *Why?* expander is a rule inspector. Pick any abstract state (cell `x`, `y`, mode, and
whether the keycard is held) and it lists every action (four moves, pickup, toggle_mode) with
every rule that applies to it in evaluation order (✓ / ✗), the final verdict, and the reason.
Blocked rows are highlighted. For example, KeyDoor at `(8, 0)`: *move Right* shows
`✓ WALL_BOUNDS ✓ HAZARD ✗ RESTRICTED_ZONE` without the key and all ✓ with it.

**Metrics Table.** One row per algorithm: Expanded, Generated, Path cost, Path length,
Max frontier, Runtime (ms), Optimal. Rows with `Optimal == False` are highlighted in pink.

**Heuristic Comparison.** Runs A\* with both heuristics on the current scenario, shows both
grids, a two-row metrics table and a summary of the cost and expansion difference. Disabled
unless A\* was selected.

**Explainer.** Static text: what a state is, why the abstract state is needed, the five rules,
and what admissibility means for each heuristic.

## Animation

Pressing Play records the start time; each rerun sets the step from elapsed time
(`PLAY_SECONDS = 2.2`) and calls `st.rerun()` after a 50 ms pause. Because the step is driven by
time rather than a fixed increment, a full playback takes about 3 s regardless of trace length
or render speed (measured 2.9–3.0 s with five grids). Stop clears the `playing` flag.

## Session state

| Key | Meaning |
|---|---|
| `traces` | label → `SearchTrace` from the last Run |
| `scenario`, `heuristic` | values used by the last Run |
| `selected` | algorithm multiselect |
| `anim_step` | slider value |
| `playing`, `play_started`, `play_from`, `max_step` | animation bookkeeping |

## Caching

`_run(scenario, algorithm, heuristic)` is wrapped in `@st.cache_data`. Searches are
deterministic, so caching is safe; animation state and figures are never cached.

## Grid rendering

`render_grid(problem, trace, step=None, title="", figsize=(5, 5)) -> Figure` draws, bottom to top:

1. terrain colours (plain `#e8f0d8`, sand `#f2e2b0`, mud `#b09070`, water `#8ec4e8`,
   slippery `#c8e6f0`);
2. restricted cells with a red hatched border;
3. hazards as dark grey cells with a black dot;
4. items as a yellow circle labelled `K`;
5. expanded cells tinted blue (darker when several modes of a cell were expanded);
6. the path as a thick orange line with dots (faded until the animation reaches the end);
7. `S` and `G` in white circles;
8. a black triangle on the most recently expanded state while animating.

It builds a `matplotlib.figure.Figure` directly (no pyplot global state) and never shows it; the
app calls `st.pyplot(fig)` then `plt.close(fig)`.

## Offline

`.streamlit/config.toml` sets `gatherUsageStats = false`, so the app makes no network calls.
