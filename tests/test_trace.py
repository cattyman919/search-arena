"""Tests for optimality annotation and rule-log bookkeeping."""

from __future__ import annotations

from reasoning.trace import annotate_optimality, run


def _traces(scenario: str) -> dict:
    return {
        "UCS": run(scenario, "ucs"),
        "A* (admissible)": run(scenario, "astar", "admissible"),
        "Greedy": run(scenario, "greedy"),
    }


def test_ucs_and_admissible_astar_are_optimal() -> None:
    for scenario in ("open_field", "u_trap", "weighted", "key_door"):
        traces = _traces(scenario)
        annotate_optimality(traces)
        assert traces["UCS"].stats["optimal"] is True
        assert traces["A* (admissible)"].stats["optimal"] is True


def test_greedy_marked_suboptimal_on_weighted() -> None:
    traces = _traces("weighted")
    annotate_optimality(traces)
    assert traces["Greedy"].path_cost > traces["UCS"].path_cost
    assert traces["Greedy"].stats["optimal"] is False


def test_annotate_runs_ucs_when_missing() -> None:
    traces = {"A* (inadmissible)": run("weighted", "astar", "inadmissible")}
    annotate_optimality(traces)
    assert traces["A* (inadmissible)"].stats["optimal"] is False


def test_rule_log_counts_consistent() -> None:
    for scenario in ("open_field", "u_trap", "weighted", "key_door"):
        log = run(scenario, "bfs").rule_log
        assert sum(log.blocked_counts.values()) <= sum(log.counts.values())
        assert len(log.entries) <= 500
        for name, blocked in log.blocked_counts.items():
            assert blocked <= log.counts[name]


def test_key_door_restricted_blocks_only_before_pickup() -> None:
    log = run("key_door", "bfs").rule_log
    restricted = [e for e in log.blocked_entries() if e[2].rule == "RESTRICTED_ZONE"]
    assert restricted, "expected at least one RESTRICTED_ZONE block"
    assert all("keycard" not in state.inventory for state, _, _ in restricted)
