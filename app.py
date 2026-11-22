"""Search Arena — Streamlit UI comparing search strategies on symbolic grid worlds."""

from __future__ import annotations

import time

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from domain.models import Action
from domain.scenarios import SCENARIOS
from reasoning.rules import RULE_ORDER
from reasoning.trace import SearchTrace, annotate_optimality, label_for, run
from viz.grid_render import render_grid

SCENARIO_LABELS: dict[str, str] = {
    "Open Field": "open_field",
    "U-Trap": "u_trap",
    "Weighted": "weighted",
    "KeyDoor": "key_door",
}
HEURISTIC_LABELS: dict[str, str] = {"Admissible": "admissible", "Inadmissible": "inadmissible"}
ALGORITHM_KEYS: dict[str, str] = {
    "BFS": "bfs",
    "DFS": "dfs",
    "UCS": "ucs",
    "Greedy": "greedy",
    "A*": "astar",
}
DEFAULT_SELECTED = ["UCS", "Greedy", "A*"]
PLAY_SECONDS = 3.0
FRAME_SLEEP = 0.05


@st.cache_data(show_spinner=False)
def _run(scenario: str, algorithm: str, heuristic: str) -> SearchTrace:
    """Cached wrapper around `reasoning.trace.run` (searches are deterministic)."""
    return run(scenario, algorithm, heuristic)


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("traces", {})
    ss.setdefault("scenario", "open_field")
    ss.setdefault("heuristic", "admissible")
    ss.setdefault("selected", list(DEFAULT_SELECTED))
    ss.setdefault("anim_step", 0)
    ss.setdefault("playing", False)
    ss.setdefault("play_started", 0.0)
    ss.setdefault("play_from", 0)


def _run_selected() -> None:
    """Run button callback: clear traces, reset animation, run every selected algorithm."""
    ss = st.session_state
    ss.scenario = SCENARIO_LABELS[ss.sb_scenario]
    ss.heuristic = HEURISTIC_LABELS[ss.sb_heuristic]
    ss.traces = {}
    ss.anim_step = 0
    ss.playing = False
    for name in ss.selected:
        algorithm = ALGORITHM_KEYS[name]
        ss.traces[label_for(algorithm, ss.heuristic)] = _run(ss.scenario, algorithm, ss.heuristic)
    annotate_optimality(ss.traces)


def _start_play() -> None:
    ss = st.session_state
    ss.playing = True
    ss.play_started = time.perf_counter()
    ss.play_from = 0 if ss.anim_step >= ss.max_step else ss.anim_step


def _stop_play() -> None:
    st.session_state.playing = False


def _advance_animation(max_step: int) -> None:
    """While playing, set the step from elapsed time so a full run never exceeds 3 s."""
    ss = st.session_state
    ss.max_step = max_step
    if ss.anim_step > max_step:
        ss.anim_step = max_step
    if not ss.playing:
        return
    frac = min(1.0, (time.perf_counter() - ss.play_started) / PLAY_SECONDS)
    ss.anim_step = int(ss.play_from + frac * (max_step - ss.play_from))
    if frac >= 1.0 or ss.anim_step >= max_step:
        ss.anim_step = max_step
        ss.playing = False


def _fmt_action(action: Action) -> str:
    if action.kind == "move":
        return f"move({action.dx:+d},{action.dy:+d})"
    if action.kind == "toggle_mode":
        return f"toggle_mode->{action.new_mode}"
    return action.kind


def _show_grid(trace: SearchTrace, step: int | None, title: str) -> None:
    problem = SCENARIOS[trace.scenario]()
    fig = render_grid(problem, trace, step=step, title=title)
    st.pyplot(fig)
    plt.close(fig)


def _metric_captions(trace: SearchTrace) -> None:
    s = trace.stats
    st.caption(
        f"Path cost: {s['path_cost']:g} | Path length: {s['path_len']} | Expanded: {s['expanded']}"
    )
    st.caption(f"Runtime: {s['runtime_ms']:.1f} ms | Max frontier: {s['max_frontier']}")
    if s["aborted"]:
        st.caption(":red[**ABORTED**] (safety cap exceeded)")
    elif not trace.solved:
        st.error("No solution found within caps.")


def _rule_log_panel(traces: dict[str, SearchTrace]) -> None:
    with st.expander("Rule log — why were actions blocked?"):
        label = st.selectbox("Trace", list(traces), key="rule_log_trace")
        log = traces[label].rule_log
        rows = [
            {
                "Rule": r,
                "Evaluations": log.counts.get(r, 0),
                "Blocked": log.blocked_counts.get(r, 0),
            }
            for r in RULE_ORDER
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        blocked = log.blocked_entries()[:10]
        if not blocked:
            st.caption("No blocked actions logged.")
        for state, action, result in blocked:
            key = "+key" if "keycard" in state.inventory else "no key"
            st.text(f"{state.pos} [{state.mode}, {key}], {_fmt_action(action)}: {result.detail}")


def tab_arena(traces: dict[str, SearchTrace]) -> None:
    """Side-by-side animated grids, one per selected algorithm."""
    max_step = max(len(t.expanded) for t in traces.values())
    _advance_animation(max_step)
    c_slider, c_play, c_stop = st.columns([6, 1, 1], vertical_alignment="bottom")
    with c_slider:
        st.slider("Animation step", 0, max_step, key="anim_step", disabled=st.session_state.playing)
    c_play.button("▶ Play", on_click=_start_play, width="stretch")
    c_stop.button("■ Stop", on_click=_stop_play, width="stretch")

    step = st.session_state.anim_step
    for col, (label, trace) in zip(st.columns(len(traces)), traces.items(), strict=True):
        with col:
            _show_grid(trace, step, label)
            _metric_captions(trace)
    _rule_log_panel(traces)


def main() -> None:
    """Page entrypoint."""
    st.set_page_config(page_title="Search Arena", layout="wide")
    _init_state()
    ss = st.session_state

    with st.sidebar:
        st.header("Search Arena")
        scenario_names = list(SCENARIO_LABELS)
        current = next(k for k, v in SCENARIO_LABELS.items() if v == ss.scenario)
        st.radio("Scenario", scenario_names, index=scenario_names.index(current), key="sb_scenario")
        st.radio("Heuristic", list(HEURISTIC_LABELS), key="sb_heuristic")
        st.multiselect("Algorithms", list(ALGORITHM_KEYS), key="selected")
        st.button("Run", type="primary", on_click=_run_selected, width="stretch")
        st.caption("Heuristic applies to A* only.")

    if not ss.traces and ss.selected:
        _run_selected()  # first load: show the default comparison right away

    st.title("Search Arena")
    if not ss.traces:
        st.info("Select at least one algorithm and press Run.")
        return
    scenario_label = next(k for k, v in SCENARIO_LABELS.items() if v == ss.scenario)
    st.caption(f"Scenario: **{scenario_label}** · Heuristic for A*: **{ss.heuristic}**")

    (arena,) = st.tabs(["Arena"])
    with arena:
        tab_arena(ss.traces)

    if ss.playing:
        time.sleep(FRAME_SLEEP)
        st.rerun()


main()
