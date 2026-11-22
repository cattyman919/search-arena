"""Admissibility checks: h(s) <= true optimal cost-to-go, computed by UCS from s."""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.models import Problem, State
from domain.scenarios import SCENARIOS
from reasoning.heuristics import h_admissible, h_inadmissible, h_keydoor, manhattan
from reasoning.rules import RuleLog
from reasoning.search import Heuristic, bfs, ucs
from reasoning.trace import run


def _true_cost(problem: Problem, state: State) -> float:
    trace = ucs(replace(problem, initial=state), RuleLog())
    assert trace.solved
    return trace.path_cost


def _sample_states(problem: Problem, n: int = 20) -> list[State]:
    """Deterministic, evenly spaced sample of reachable states (BFS expansion order)."""
    reachable = bfs(problem, RuleLog()).expanded
    step = max(1, len(reachable) // n)
    return reachable[::step][:n]


def test_manhattan() -> None:
    assert manhattan((0, 0), (3, 4)) == 7
    assert manhattan((5, 5), (5, 5)) == 0


@pytest.mark.parametrize(
    ("scenario", "h"),
    [("weighted", h_admissible), ("key_door", h_admissible), ("key_door", h_keydoor)],
)
def test_admissible_on_sampled_states(scenario: str, h: Heuristic) -> None:
    problem = SCENARIOS[scenario]()
    states = _sample_states(problem)
    assert len(states) == 20
    for state in states:
        assert h(state, problem) <= _true_cost(problem, state) + 1e-9


def test_inadmissible_overestimates_on_weighted() -> None:
    problem = SCENARIOS["weighted"]()
    optimal = run("weighted", "ucs").path_cost
    assert h_inadmissible(problem.initial, problem) > optimal


def test_keydoor_admissible_at_initial_and_tighter_than_manhattan() -> None:
    problem = SCENARIOS["key_door"]()
    optimal = run("key_door", "ucs").path_cost
    assert h_keydoor(problem.initial, problem) <= optimal
    assert h_keydoor(problem.initial, problem) > h_admissible(problem.initial, problem)
