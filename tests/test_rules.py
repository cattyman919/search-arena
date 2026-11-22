"""Unit tests for the five constraint rules and their evaluation order."""

from __future__ import annotations

from domain.models import Action, Grid, Mode, Problem, State
from domain.scenarios import TERRAIN_COST
from reasoning.rules import RuleLog, allowed, eval_rules

#   x: 0      1         2
# y0:  start  slippery  water
# y1:  plain  hazard    restricted
GRID = Grid(
    width=3,
    height=2,
    terrain={(1, 0): "slippery", (2, 0): "water"},
    hazards=frozenset({(1, 1)}),
    restricted=frozenset({(2, 1)}),
    items={},
    start=(0, 0),
    goal=(0, 1),
)
PROBLEM = Problem(GRID, dict(TERRAIN_COST), State((0, 0)), (0, 1))

RIGHT = Action("move", 1, 0)
LEFT = Action("move", -1, 0)
UP = Action("move", 0, -1)
DOWN = Action("move", 0, 1)


def _state(pos: tuple[int, int], mode: Mode = "normal", keycard: bool = False) -> State:
    return State(pos, frozenset({"keycard"}) if keycard else frozenset(), mode)


def test_wall_bounds_blocks_move_off_corner() -> None:
    ok, why = allowed(PROBLEM, _state((0, 0)), LEFT)
    assert not ok and why is not None
    assert why.rule == "WALL_BOUNDS"
    assert why.detail == "blocked: out of bounds"
    ok, why = allowed(PROBLEM, _state((0, 0)), UP)
    assert not ok and why is not None and why.rule == "WALL_BOUNDS"


def test_hazard_blocks() -> None:
    ok, why = allowed(PROBLEM, _state((0, 1)), RIGHT)
    assert not ok and why is not None
    assert why.rule == "HAZARD"


def test_restricted_zone_needs_keycard() -> None:
    ok, why = allowed(PROBLEM, _state((2, 0), mode="swim"), DOWN)
    assert not ok and why is not None
    assert why.rule == "RESTRICTED_ZONE"
    assert why.detail == "blocked: RestrictedZone requires KeyCard"
    ok, why = allowed(PROBLEM, _state((2, 0), mode="swim", keycard=True), DOWN)
    assert ok and why is None


def test_slippery_blocked_in_speed_allowed_in_normal() -> None:
    ok, why = allowed(PROBLEM, _state((0, 0), mode="speed"), RIGHT)
    assert not ok and why is not None
    assert why.rule == "SLIPPERY_MODE"
    assert why.detail == "blocked: SlipperyTile unsafe in SpeedMode"
    ok, why = allowed(PROBLEM, _state((0, 0), mode="swim"), RIGHT)
    assert not ok and why is not None and why.detail.endswith("SwimMode")
    assert allowed(PROBLEM, _state((0, 0)), RIGHT) == (True, None)


def test_water_needs_swim() -> None:
    ok, why = allowed(PROBLEM, _state((1, 0)), RIGHT)
    assert not ok and why is not None
    assert why.rule == "WATER_SWIM"
    assert allowed(PROBLEM, _state((1, 0), mode="swim"), RIGHT) == (True, None)


def test_rule_order_first_block_wins() -> None:
    # Restricted + water + slippery + hazard all on one cell: HAZARD comes first.
    stacked = Grid(
        width=2,
        height=1,
        terrain={(1, 0): "water"},
        hazards=frozenset({(1, 0)}),
        restricted=frozenset({(1, 0)}),
        items={},
        start=(0, 0),
        goal=(0, 0),
    )
    problem = Problem(stacked, dict(TERRAIN_COST), State((0, 0)), (0, 0))
    _, why = allowed(problem, State((0, 0)), RIGHT)
    assert why is not None and why.rule == "HAZARD"

    no_hazard = Grid(2, 1, {(1, 0): "water"}, frozenset(), frozenset({(1, 0)}), {}, (0, 0), (0, 0))
    problem = Problem(no_hazard, dict(TERRAIN_COST), State((0, 0)), (0, 0))
    _, why = allowed(problem, State((0, 0)), RIGHT)
    assert why is not None and why.rule == "WATER_SWIM"

    slippery_restricted = Grid(
        2, 1, {(1, 0): "slippery"}, frozenset(), frozenset({(1, 0)}), {}, (0, 0), (0, 0)
    )
    problem = Problem(slippery_restricted, dict(TERRAIN_COST), State((0, 0)), (0, 0))
    _, why = allowed(problem, State((0, 0), mode="speed"), RIGHT)
    assert why is not None and why.rule == "SLIPPERY_MODE"


def test_eval_rules_lists_applicable_verdicts_in_order() -> None:
    results = eval_rules(PROBLEM, _state((2, 0), mode="swim"), DOWN)
    assert [r.rule for r in results] == ["WALL_BOUNDS", "HAZARD", "RESTRICTED_ZONE"]
    assert [r.ok for r in results] == [True, True, False]
    assert eval_rules(PROBLEM, _state((0, 0)), Action("toggle_mode")) == []


def test_rule_log_counts_and_caps() -> None:
    log = RuleLog()
    for _ in range(300):
        allowed(PROBLEM, _state((1, 0)), RIGHT, log)
    assert log.blocked_counts["WATER_SWIM"] == 300
    assert log.counts["WATER_SWIM"] == 300
    assert log.counts["WALL_BOUNDS"] == 300
    assert len(log.entries) <= 500
    assert len(log.blocked_entries()) < 300  # capped, counters are not
