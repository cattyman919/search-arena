"""Search trace container, optimality annotation, and the central `run` entrypoint."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from domain.models import State
from reasoning.rules import RuleLog

__all__ = ["ALGORITHMS", "RuleLog", "SearchTrace", "annotate_optimality", "label_for", "run"]

ALGORITHMS: tuple[str, ...] = ("bfs", "dfs", "ucs", "greedy", "astar")
_LABELS = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "greedy": "Greedy"}


@dataclass
class SearchTrace:
    """Everything one search run produced: path, expansion order, rule log, stats."""

    algorithm: str
    scenario: str
    path: list[State]
    expanded: list[State]
    frontier_sizes: list[int]
    rule_log: RuleLog
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def path_cost(self) -> float:
        """Sum of edge costs along the path (0.0 if no solution)."""
        return float(self.stats.get("path_cost", 0.0))

    @property
    def solved(self) -> bool:
        """True if a path to the goal was found."""
        return bool(self.path)


def label_for(algorithm: str, heuristic: str = "admissible") -> str:
    """Human-readable label, e.g. ``"A* (inadmissible)"``."""
    if algorithm == "astar":
        return f"A* ({heuristic})"
    return _LABELS[algorithm]


def run(scenario_name: str, algorithm: str, heuristic: str = "admissible") -> SearchTrace:
    """Run one strategy on one scenario with a fresh `RuleLog`.

    `heuristic` ("admissible" / "inadmissible") only affects A*; Greedy always uses the
    admissible heuristic for the scenario (h_keydoor on key_door).
    """
    # Imported here: search.py depends on SearchTrace defined above.
    from domain.scenarios import SCENARIOS
    from reasoning import search
    from reasoning.heuristics import select_heuristic

    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm!r}")
    problem = SCENARIOS[scenario_name]()
    log = RuleLog()
    if algorithm == "bfs":
        trace = search.bfs(problem, log)
    elif algorithm == "dfs":
        trace = search.dfs(problem, log)
    elif algorithm == "ucs":
        trace = search.ucs(problem, log)
    elif algorithm == "greedy":
        trace = search.greedy(problem, log, select_heuristic(scenario_name, "admissible"))
    else:
        h = select_heuristic(scenario_name, heuristic)
        trace = search.astar(problem, log, h, label=label_for("astar", heuristic))
    trace.scenario = scenario_name
    return trace


def annotate_optimality(traces: dict[str, SearchTrace]) -> None:
    """Set ``stats['optimal'] = (path_cost == UCS path_cost)`` on every trace.

    Uses the UCS trace in `traces` if present, otherwise runs UCS silently on the
    scenario of the first trace. Unsolved traces are never optimal.
    """
    if not traces:
        return
    reference = next((t for t in traces.values() if t.algorithm == "UCS"), None)
    if reference is None:
        reference = run(next(iter(traces.values())).scenario, "ucs")
    for trace in traces.values():
        trace.stats["optimal"] = (
            trace.solved and reference.solved and math.isclose(trace.path_cost, reference.path_cost)
        )
