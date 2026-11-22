# Constraint rules

Defined in [`reasoning/rules.py`](../reasoning/rules.py).

## Rule contract

Each rule is a pure function `(problem, state, action) -> RuleResult | None`:

- `None` — the rule does not apply to this pair (e.g. a terrain rule for a non-matching tile);
- `RuleResult(rule, ok=True, detail)` — applies and allows;
- `RuleResult(rule, ok=False, detail)` — applies and **blocks**.

```python
@dataclass(frozen=True)
class RuleResult:
    rule: str  # "WALL_BOUNDS" | "HAZARD" | "SLIPPERY_MODE" | "WATER_SWIM" | "RESTRICTED_ZONE"
    ok: bool
    detail: str  # short, slide-friendly reason
```

Rules only constrain `move` actions. `pickup` and `toggle_mode` are always allowed at the rule
layer; whether a pickup is meaningful is decided in `successors()`.

## The five rules (evaluation order)

| # | Rule | Applies to | Allows when | Block message |
|---|---|---|---|---|
| 1 | `WALL_BOUNDS` | every move | target inside grid | `blocked: out of bounds` |
| 2 | `HAZARD` | moves to in-bounds cells | target not a hazard | `blocked: hazard tile` |
| 3 | `SLIPPERY_MODE` | moves into slippery | `mode == "normal"` | `blocked: SlipperyTile unsafe in SpeedMode` / `...SwimMode` |
| 4 | `WATER_SWIM` | moves into water | `mode == "swim"` | `blocked: water requires SwimMode` |
| 5 | `RESTRICTED_ZONE` | moves into restricted | `"keycard" in inventory` | `blocked: RestrictedZone requires KeyCard` |

Rules 2–5 return `None` for out-of-bounds targets so they never reason about cells that don't
exist.

The rules are listed in the tuple `RULES`; adding a rule means writing one function and
appending it there.

## Two entry points

- `eval_rules(problem, state, action) -> list[RuleResult]` — every applicable verdict, in order.
  Used by the *Why?* inspector in the Arena tab; it does not stop at the first block.
- `allowed(problem, state, action, log=None) -> (bool, RuleResult | None)` — stops at the
  **first** block and returns it, or `(True, None)`. Used by the search. Every verdict it
  evaluates is recorded in `log` if given.

A test checks, for every cell × mode × inventory × move of every scenario, that the first ✗
in `eval_rules` is exactly the block `allowed` returns, so the inspector and the search can
never disagree.

## RuleLog

```python
@dataclass
class RuleLog:
    entries: list[tuple[State, Action, RuleResult]]  # bounded sample
    counts: dict[str, int]  # all evaluations, per rule
    blocked_counts: dict[str, int]  # all blocks, per rule
```

- `counts` and `blocked_counts` cover the **whole run**, uncapped.
- `entries` is capped at 500 total: up to **80 blocks** and **20 allowed samples** per rule
  (5 × 100 = 500). The per-rule cap keeps a noisy rule (usually `WALL_BOUNDS` or `WATER_SWIM`)
  from crowding out rarer, more interesting blocks like `RESTRICTED_ZONE`.
- `blocked_entries()` returns only the logged blocks, in log order.

Invariant (tested): `blocked_counts[r] <= counts[r]` for every rule.

## Example: KeyDoor

Running BFS on KeyDoor, every `RESTRICTED_ZONE` block comes from a state **without** the
keycard, e.g.

```text
(8, 0) [normal, no key], move(+1,+0): blocked: RestrictedZone requires KeyCard
```

Once a state holds the key, the rule allows the move, so no blocks are logged after pickup.
