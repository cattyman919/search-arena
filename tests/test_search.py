"""Correctness, comparison, and determinism tests for all search strategies."""

from __future__ import annotations

import itertools
from collections import deque
from dataclasses import replace

import pytest

from domain.models import Problem, State
from domain.scenarios import SCENARIOS
from reasoning.heuristics import h_admissible
from reasoning.rules import RuleLog
from reasoning.search import astar, bfs, dfs, greedy, is_goal, successors, ucs
from reasoning.trace import SearchTrace, run

CASES = [
    *itertools.product(SCENARIOS, ["bfs", "dfs", "ucs", "greedy"], ["admissible"]),
    *itertools.product(SCENARIOS, ["astar"], ["admissible", "inadmissible"]),
]


@pytest.fixture(scope="module")
def traces() -> dict[tuple[str, str, str], SearchTrace]:
    return {case: run(*case) for case in CASES}


def test_open_field_baseline(traces: dict) -> None:
    bfs_t = traces["open_field", "bfs", "admissible"]
    ucs_t = traces["open_field", "ucs", "admissible"]
    ast_t = traces["open_field", "astar", "admissible"]
    assert bfs_t.path_cost == ucs_t.path_cost == ast_t.path_cost == 14.0
    assert bfs_t.stats["path_len"] == ast_t.stats["path_len"]


def test_weighted_cost_vs_moves(traces: dict) -> None:
    bfs_t = traces["weighted", "bfs", "admissible"]
    ucs_t = traces["weighted", "ucs", "admissible"]
    ast_t = traces["weighted", "astar", "admissible"]
    assert ucs_t.path_cost == ast_t.path_cost
    assert bfs_t.path_cost >= ucs_t.path_cost
    assert bfs_t.path_cost > ucs_t.path_cost  # the scenario is built so BFS pays more
    assert bfs_t.stats["path_len"] < ucs_t.stats["path_len"]


def test_u_trap_greedy_expands_more_than_astar(traces: dict) -> None:
    greedy_t = traces["u_trap", "greedy", "admissible"]
    ast_t = traces["u_trap", "astar", "admissible"]
    assert greedy_t.stats["expanded"] > ast_t.stats["expanded"]


def test_weighted_inadmissible_is_suboptimal_but_cheaper_to_find(traces: dict) -> None:
    ucs_t = traces["weighted", "ucs", "admissible"]
    adm = traces["weighted", "astar", "admissible"]
    inadm = traces["weighted", "astar", "inadmissible"]
    assert inadm.path_cost > ucs_t.path_cost
    assert inadm.stats["expanded"] <= adm.stats["expanded"]


def _bfs_xy_only(problem: Problem) -> bool:
    """Control: BFS over raw (x, y), dropping inventory and mode. Returns True if solved."""
    start = problem.initial.pos
    queue: deque[tuple[int, int]] = deque([start])
    seen = {start}
    while queue:
        pos = queue.popleft()
        if pos == problem.goal_pos:
            return True
        for _, nxt, _ in successors(problem, State(pos)):
            if nxt.pos not in seen:
                seen.add(nxt.pos)
                queue.append(nxt.pos)
    return False


def test_key_door_needs_abstract_state(traces: dict) -> None:
    assert traces["key_door", "bfs", "admissible"].solved
    assert not _bfs_xy_only(SCENARIOS["key_door"]())
    assert _bfs_xy_only(SCENARIOS["open_field"]())  # sanity: the control itself works


def test_key_door_plan_uses_key_and_swim(traces: dict) -> None:
    path = traces["key_door", "ucs", "admissible"].path
    assert "keycard" in path[-1].inventory
    assert any(s.mode == "swim" for s in path)


@pytest.mark.parametrize("case", CASES, ids=lambda c: "-".join(c))
def test_trace_invariants(traces: dict, case: tuple[str, str, str]) -> None:
    trace = traces[case]
    problem = SCENARIOS[case[0]]()
    assert trace.stats["aborted"] is None
    assert trace.solved
    assert trace.path[0] == problem.initial
    assert is_goal(trace.path[-1], problem)
    assert trace.path[-1].pos == problem.goal_pos
    assert trace.stats["expanded"] == len(trace.expanded)
    assert trace.stats["path_len"] == len(trace.path) - 1
    total = 0.0
    for s, s_next in itertools.pairwise(trace.path):
        edges = [c for _, nxt, c in successors(problem, s, RuleLog()) if nxt == s_next]
        assert edges, f"no legal action from {s} to {s_next}"
        total += min(edges)
    assert total == pytest.approx(trace.path_cost)
    assert trace.stats["runtime_ms"] < 500


@pytest.mark.parametrize("case", CASES, ids=lambda c: "-".join(c))
def test_determinism(traces: dict, case: tuple[str, str, str]) -> None:
    again = run(*case)
    assert again.path == traces[case].path
    assert again.expanded == traces[case].expanded
    assert again.stats["expanded"] == traces[case].stats["expanded"]


def test_unreachable_goal_returns_empty_path() -> None:
    problem = SCENARIOS["u_trap"]()
    walled = replace(
        problem,
        grid=replace(problem.grid, hazards=problem.grid.hazards | {(9, 4), (9, 6), (8, 5)}),
    )

    for trace in (
        bfs(walled, RuleLog()),
        dfs(walled, RuleLog()),
        ucs(walled, RuleLog()),
        greedy(walled, RuleLog(), h_admissible),
        astar(walled, RuleLog(), h_admissible),
    ):
        assert trace.path == []
        assert trace.stats["path_cost"] == 0.0 and trace.stats["path_len"] == 0
        assert trace.stats["aborted"] is None
