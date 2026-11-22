"""Declarative constraint rules over (state, action) pairs.

Each rule inspects one ``(state, action)`` pair and returns ``None`` (does not apply)
or a ``RuleResult`` saying whether it allows or blocks the action. Rules are evaluated
in a fixed order; the first block wins.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from domain.models import Action, Mode, Pos, Problem, State

RULE_ORDER: tuple[str, ...] = (
    "WALL_BOUNDS",
    "HAZARD",
    "SLIPPERY_MODE",
    "WATER_SWIM",
    "RESTRICTED_ZONE",
)

LOG_CAP = 500
BLOCKED_PER_RULE = 80  # 5 rules x (80 blocked + 20 allowed) = 500 entries max
ALLOWED_SAMPLE_PER_RULE = 20

_MODE_NAME: dict[Mode, str] = {"normal": "NormalMode", "speed": "SpeedMode", "swim": "SwimMode"}


@dataclass(frozen=True)
class RuleResult:
    """Verdict of a single rule on a single (state, action) pair."""

    rule: str
    ok: bool
    detail: str


@dataclass
class RuleLog:
    """Bounded log of rule evaluations plus full-run counters."""

    entries: list[tuple[State, Action, RuleResult]] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(RULE_ORDER, 0))
    blocked_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(RULE_ORDER, 0))
    _logged_blocked: dict[str, int] = field(default_factory=dict, repr=False)
    _logged_allowed: dict[str, int] = field(default_factory=dict, repr=False)

    def record(self, state: State, action: Action, result: RuleResult) -> None:
        """Count an evaluation; keep blocks and a small sample of passes in `entries`.

        Entries are capped per rule so that one noisy rule cannot crowd out the others,
        and the total never exceeds ``LOG_CAP``.
        """
        name = result.rule
        self.counts[name] = self.counts.get(name, 0) + 1
        if not result.ok:
            self.blocked_counts[name] = self.blocked_counts.get(name, 0) + 1
        bucket, limit = (
            (self._logged_allowed, ALLOWED_SAMPLE_PER_RULE)
            if result.ok
            else (self._logged_blocked, BLOCKED_PER_RULE)
        )
        if bucket.get(name, 0) < limit and len(self.entries) < LOG_CAP:
            bucket[name] = bucket.get(name, 0) + 1
            self.entries.append((state, action, result))

    def blocked_entries(self) -> list[tuple[State, Action, RuleResult]]:
        """Logged entries whose verdict was a block, in log order."""
        return [e for e in self.entries if not e[2].ok]


def _target(state: State, action: Action) -> Pos:
    return (state.pos[0] + action.dx, state.pos[1] + action.dy)


def _target_on_grid(problem: Problem, state: State, action: Action) -> Pos | None:
    """Target cell of a move if it is on the grid, else None (other rules then skip)."""
    if action.kind != "move":
        return None
    target = _target(state, action)
    return target if problem.grid.in_bounds(target) else None


def rule_wall_bounds(problem: Problem, state: State, action: Action) -> RuleResult | None:
    """Moves must stay inside the grid."""
    if action.kind != "move":
        return None
    if problem.grid.in_bounds(_target(state, action)):
        return RuleResult("WALL_BOUNDS", True, "allowed: target inside grid")
    return RuleResult("WALL_BOUNDS", False, "blocked: out of bounds")


def rule_hazard(problem: Problem, state: State, action: Action) -> RuleResult | None:
    """Moves may not enter hazard tiles."""
    target = _target_on_grid(problem, state, action)
    if target is None:
        return None
    if target in problem.grid.hazards:
        return RuleResult("HAZARD", False, "blocked: hazard tile")
    return RuleResult("HAZARD", True, "allowed: no hazard")


def rule_slippery_mode(problem: Problem, state: State, action: Action) -> RuleResult | None:
    """Slippery tiles may only be entered in normal mode."""
    target = _target_on_grid(problem, state, action)
    if target is None or problem.grid.terrain_at(target) != "slippery":
        return None
    if state.mode == "normal":
        return RuleResult("SLIPPERY_MODE", True, "allowed: SlipperyTile safe in NormalMode")
    return RuleResult(
        "SLIPPERY_MODE", False, f"blocked: SlipperyTile unsafe in {_MODE_NAME[state.mode]}"
    )


def rule_water_swim(problem: Problem, state: State, action: Action) -> RuleResult | None:
    """Water tiles may only be entered in swim mode."""
    target = _target_on_grid(problem, state, action)
    if target is None or problem.grid.terrain_at(target) != "water":
        return None
    if state.mode == "swim":
        return RuleResult("WATER_SWIM", True, "allowed: SwimMode crosses water")
    return RuleResult("WATER_SWIM", False, "blocked: water requires SwimMode")


def rule_restricted_zone(problem: Problem, state: State, action: Action) -> RuleResult | None:
    """Restricted tiles may only be entered while holding the keycard."""
    target = _target_on_grid(problem, state, action)
    if target is None or target not in problem.grid.restricted:
        return None
    if "keycard" in state.inventory:
        return RuleResult("RESTRICTED_ZONE", True, "allowed: KeyCard opens RestrictedZone")
    return RuleResult("RESTRICTED_ZONE", False, "blocked: RestrictedZone requires KeyCard")


Rule = Callable[[Problem, State, Action], RuleResult | None]

RULES: tuple[Rule, ...] = (
    rule_wall_bounds,
    rule_hazard,
    rule_slippery_mode,
    rule_water_swim,
    rule_restricted_zone,
)


def eval_rules(problem: Problem, state: State, action: Action) -> list[RuleResult]:
    """Every applicable rule's verdict, in rule order (for "show me why" displays)."""
    results = (rule(problem, state, action) for rule in RULES)
    return [r for r in results if r is not None]


def allowed(
    problem: Problem, state: State, action: Action, log: RuleLog | None = None
) -> tuple[bool, RuleResult | None]:
    """Return ``(True, None)`` if no rule blocks, else ``(False, first_blocking_rule)``.

    Evaluation stops at the first block; each evaluated verdict is recorded in `log`.
    """
    for rule in RULES:
        result = rule(problem, state, action)
        if result is None:
            continue
        if log is not None:
            log.record(state, action, result)
        if not result.ok:
            return False, result
    return True, None
