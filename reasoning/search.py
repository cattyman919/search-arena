"""Uninformed and informed search strategies over the abstract state space.

All strategies share `successors` (rule-checked transitions), stop when a goal state is
*popped*, enforce the same safety caps, and are fully deterministic: successors come in a
fixed order and priority-queue ties are broken by an insertion counter.
"""

from __future__ import annotations

import heapq
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace

from domain.models import Action, Problem, State, next_mode
from reasoning.rules import RuleLog, allowed
from reasoning.trace import SearchTrace

MAX_EXPANDED = 200_000
MAX_FRONTIER = 100_000
MAX_SECONDS = 5.0
TIME_CHECK_EVERY = 2_000

KIND_RANK = {"move": 0, "pickup": 1, "toggle_mode": 2}
MOVES: tuple[Action, ...] = tuple(
    sorted(
        (Action("move", dx, dy) for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))),
        key=lambda a: (KIND_RANK[a.kind], a.dx, a.dy),
    )
)

Heuristic = Callable[[State, Problem], float]
Successor = tuple[Action, State, float]
Parents = dict[State, tuple[State | None, Action | None]]


def successors(problem: Problem, state: State, log: RuleLog | None = None) -> list[Successor]:
    """Enumerate all (action, next_state, edge_cost) triples the rule layer allows.

    Moves cost the terrain cost of the target cell; pickup and toggle_mode cost 0.
    Pickup is only generated when there is an item here that is not yet held.
    Order: moves sorted by (dx, dy), then pickup, then toggle_mode.
    """
    grid = problem.grid
    out: list[Successor] = []
    for action in MOVES:
        ok, _ = allowed(problem, state, action, log)
        if ok:
            target = (state.pos[0] + action.dx, state.pos[1] + action.dy)
            cost = problem.terrain_cost[grid.terrain_at(target)]
            out.append((action, replace(state, pos=target), cost))
    item = grid.items.get(state.pos)
    if item is not None and item not in state.inventory:
        out.append((Action("pickup"), replace(state, inventory=state.inventory | {item}), 0.0))
    mode = next_mode(state.mode)
    out.append((Action("toggle_mode", new_mode=mode), replace(state, mode=mode), 0.0))
    return out


def is_goal(state: State, problem: Problem) -> bool:
    """Goal test: the agent stands on the goal cell (inventory and mode are irrelevant)."""
    return state.pos == problem.goal_pos


def reconstruct(parent: Parents, goal_state: State) -> list[State]:
    """Walk parent pointers back to the start, reverse, and return the state path."""
    path = [goal_state]
    prev, _ = parent[goal_state]
    while prev is not None:
        path.append(prev)
        prev, _ = parent[prev]
    path.reverse()
    return path


class _Run:
    """Shared bookkeeping for one search: counters, caps, and trace assembly."""

    def __init__(self, name: str, problem: Problem, log: RuleLog) -> None:
        self.name = name
        self.problem = problem
        self.log = log
        self.expanded: list[State] = []
        self.frontier_sizes: list[int] = []
        self.generated = 0
        self.max_frontier = 0
        self.t0 = time.perf_counter()

    def pop(self, state: State, frontier_len: int) -> None:
        """Record one expansion and the frontier size at the moment of popping."""
        self.expanded.append(state)
        self.frontier_sizes.append(frontier_len)

    def push_size(self, frontier_len: int) -> None:
        """Track the peak frontier size."""
        self.max_frontier = max(self.max_frontier, frontier_len)

    def capped(self, frontier_len: int) -> bool:
        """True if any safety cap has tripped."""
        n = len(self.expanded)
        if n >= MAX_EXPANDED or frontier_len > MAX_FRONTIER:
            return True
        return n % TIME_CHECK_EVERY == 0 and time.perf_counter() - self.t0 > MAX_SECONDS

    def finish(self, path: list[State], cost: float, aborted: str | None = None) -> SearchTrace:
        """Assemble the trace with the standard stats keys."""
        return SearchTrace(
            algorithm=self.name,
            scenario="",
            path=path,
            expanded=self.expanded,
            frontier_sizes=self.frontier_sizes,
            rule_log=self.log,
            stats={
                "expanded": len(self.expanded),
                "generated": self.generated,
                "path_cost": cost if path else 0.0,
                "path_len": max(len(path) - 1, 0),
                "max_frontier": self.max_frontier,
                "runtime_ms": (time.perf_counter() - self.t0) * 1000.0,
                "optimal": False,
                "aborted": aborted,
            },
        )

    def abort(self) -> SearchTrace:
        """Trace for a run stopped by a safety cap."""
        return self.finish([], 0.0, aborted="cap_exceeded")


def bfs(problem: Problem, log: RuleLog) -> SearchTrace:
    """Breadth-first search: FIFO queue, minimizes the number of actions (not cost)."""
    run = _Run("BFS", problem, log)
    start = problem.initial
    queue: deque[tuple[State, float]] = deque([(start, 0.0)])
    visited: set[State] = {start}
    parent: Parents = {start: (None, None)}
    run.push_size(1)
    while queue:
        if run.capped(len(queue)):
            return run.abort()
        state, g = queue.popleft()
        run.pop(state, len(queue) + 1)
        if is_goal(state, problem):
            return run.finish(reconstruct(parent, state), g)
        for action, nxt, cost in successors(problem, state, log):
            run.generated += 1
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = (state, action)
                queue.append((nxt, g + cost))
        run.push_size(len(queue))
    return run.finish([], 0.0)


def dfs(problem: Problem, log: RuleLog, max_depth: int = 500) -> SearchTrace:
    """Depth-first search: LIFO stack with a depth cap; explores successors in order."""
    run = _Run("DFS", problem, log)
    start = problem.initial
    # (state, parent, action, depth, g)
    stack: list[tuple[State, State | None, Action | None, int, float]] = [
        (start, None, None, 0, 0.0)
    ]
    visited: set[State] = set()
    parent: Parents = {}
    run.push_size(1)
    while stack:
        if run.capped(len(stack)):
            return run.abort()
        state, prev, how, depth, g = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        parent[state] = (prev, how)
        run.pop(state, len(stack) + 1)
        if is_goal(state, problem):
            return run.finish(reconstruct(parent, state), g)
        if depth >= max_depth:
            continue
        succ = successors(problem, state, log)
        run.generated += len(succ)
        # Push in reverse so the first successor in canonical order is explored first.
        for action, nxt, cost in reversed(succ):
            if nxt not in visited:
                stack.append((nxt, state, action, depth + 1, g + cost))
        run.push_size(len(stack))
    return run.finish([], 0.0)


def _best_first(
    name: str,
    problem: Problem,
    log: RuleLog,
    priority: Callable[[float, State], tuple[float, ...]],
    reopen: bool,
) -> SearchTrace:
    """Generic best-first search keyed by `priority(g, state)` plus an insertion counter.

    With ``reopen=True`` (UCS, A*), a state is re-queued whenever a cheaper g is found and
    stale pops (``g > best_g``) are skipped. With ``reopen=False`` (Greedy), each state is
    expanded at most once (``visited`` set).
    """
    run = _Run(name, problem, log)
    start = problem.initial
    counter = 0
    frontier: list[tuple[tuple[float, ...], int, float, State]] = [
        (priority(0.0, start), counter, 0.0, start)
    ]
    best_g: dict[State, float] = {start: 0.0}
    visited: set[State] = set()
    parent: Parents = {start: (None, None)}
    run.push_size(1)
    while frontier:
        if run.capped(len(frontier)):
            return run.abort()
        _, _, g, state = heapq.heappop(frontier)
        if reopen:
            if g > best_g[state]:
                continue
        elif state in visited:
            continue
        visited.add(state)
        run.pop(state, len(frontier) + 1)
        if is_goal(state, problem):
            return run.finish(reconstruct(parent, state), g)
        for action, nxt, cost in successors(problem, state, log):
            run.generated += 1
            ng = g + cost
            if reopen:
                if ng >= best_g.get(nxt, float("inf")):
                    continue
            elif nxt in visited or nxt in parent:
                continue
            best_g[nxt] = ng
            parent[nxt] = (state, action)
            counter += 1
            heapq.heappush(frontier, (priority(ng, nxt), counter, ng, nxt))
        run.push_size(len(frontier))
    return run.finish([], 0.0)


def ucs(problem: Problem, log: RuleLog) -> SearchTrace:
    """Uniform-cost search: priority queue on path cost g; optimal for nonnegative costs."""
    return _best_first("UCS", problem, log, lambda g, s: (g,), reopen=True)


def greedy(problem: Problem, log: RuleLog, h: Heuristic) -> SearchTrace:
    """Greedy best-first: priority on h only; fast but neither optimal nor complete-cost."""
    return _best_first("Greedy", problem, log, lambda g, s: (h(s, problem),), reopen=False)


def astar(problem: Problem, log: RuleLog, h: Heuristic, label: str = "A*") -> SearchTrace:
    """A*: priority on f = g + h, ties broken by lower h, then insertion order.

    Goal test on pop (not on enqueue), so with an admissible h the result is optimal.
    """

    def priority(g: float, s: State) -> tuple[float, ...]:
        hv = h(s, problem)
        return (g + hv, hv)

    return _best_first(label, problem, log, priority, reopen=True)
