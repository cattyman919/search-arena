"""Search trace container and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models import State
from reasoning.rules import RuleLog


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
