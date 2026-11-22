"""Render a scenario grid, optionally overlaid with a search trace, as a matplotlib Figure."""

from __future__ import annotations

from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle

from domain.models import Problem
from reasoning.trace import SearchTrace

TERRAIN_ORDER: tuple[str, ...] = ("plain", "sand", "mud", "water", "slippery")
TERRAIN_COLORS: tuple[str, ...] = ("#e8f0d8", "#f2e2b0", "#b09070", "#8ec4e8", "#c8e6f0")
EXPANDED_COLOR = "#3b6fd8"
PATH_COLOR = "#f07b16"


def render_grid(
    problem: Problem,
    trace: SearchTrace | None,
    step: int | None = None,
    title: str = "",
    figsize: tuple[int, int] = (5, 5),
) -> Figure:
    """Draw terrain, zones, items, expansion progress, path, start/goal, and agent.

    `step` = number of expanded states to show (None = all). The caller displays the
    figure (e.g. ``st.pyplot(fig)``) and then closes it; nothing is shown here.
    """
    grid = problem.grid
    fig = Figure(figsize=figsize, dpi=100)
    ax = fig.add_subplot()

    # 1. terrain
    index = {name: i for i, name in enumerate(TERRAIN_ORDER)}
    cells = [
        [index.get(grid.terrain_at((x, y)), 0) for x in range(grid.width)]
        for y in range(grid.height)
    ]
    ax.imshow(
        cells,
        cmap=ListedColormap(list(TERRAIN_COLORS)),
        vmin=0,
        vmax=len(TERRAIN_ORDER) - 1,
        origin="upper",
        interpolation="nearest",
    )

    # 2. restricted zone
    for x, y in sorted(grid.restricted):
        ax.add_patch(
            Rectangle(
                (x - 0.5, y - 0.5), 1, 1, fill=False, edgecolor="#d62728", hatch="///", lw=1.5
            )
        )

    # 3. hazards
    for x, y in sorted(grid.hazards):
        ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, color="#4a4a4a"))
        ax.plot(x, y, "o", color="black", ms=4)

    # 4. items
    for (x, y), _item in sorted(grid.items.items()):
        ax.add_patch(Circle((x, y), 0.32, facecolor="#ffd400", edgecolor="#8a6d00", lw=1.2))
        ax.text(x, y, "K", ha="center", va="center", fontsize=9, fontweight="bold")

    shown = 0
    if trace is not None:
        total = len(trace.expanded)
        shown = total if step is None else max(0, min(step, total))
        # 5. expanded nodes (one tint per cell, darker when several modes were expanded)
        visits: dict[tuple[int, int], int] = {}
        for state in trace.expanded[:shown]:
            visits[state.pos] = visits.get(state.pos, 0) + 1
        for (x, y), n in sorted(visits.items()):
            ax.add_patch(
                Rectangle(
                    (x - 0.5, y - 0.5), 1, 1, color=EXPANDED_COLOR, alpha=min(0.14 * n, 0.42), lw=0
                )
            )
        # 6. final path (faded until the animation reaches the end)
        if trace.path:
            done = shown >= total
            xs = [s.pos[0] for s in trace.path]
            ys = [s.pos[1] for s in trace.path]
            alpha = 1.0 if done else 0.25
            ax.plot(xs, ys, "-", color=PATH_COLOR, lw=3.5, alpha=alpha, solid_capstyle="round")
            ax.plot(xs, ys, "o", color=PATH_COLOR, ms=3.5, alpha=alpha)

    # 7. start / goal
    for (x, y), label, color in ((grid.start, "S", "#1a9a3a"), (grid.goal, "G", "#d62728")):
        ax.add_patch(Circle((x, y), 0.38, facecolor="white", edgecolor=color, lw=1.8))
        ax.text(x, y, label, ha="center", va="center", color=color, fontsize=11, weight="bold")

    # 8. agent on the most recently expanded state
    if trace is not None and step is not None and 0 < shown < len(trace.expanded):
        ax_, ay = trace.expanded[shown - 1].pos
        ax.plot(ax_, ay, "^", color="black", ms=11)

    ax.set_xlim(-0.5, grid.width - 0.5)
    ax.set_ylim(grid.height - 0.5, -0.5)
    ax.set_xticks([x - 0.5 for x in range(grid.width + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(grid.height + 1)], minor=True)
    ax.grid(which="minor", color="white", lw=0.6)
    ax.tick_params(which="both", length=0, labelsize=7)
    ax.set_xticks(range(grid.width))
    ax.set_yticks(range(grid.height))
    total_expanded = len(trace.expanded) if trace else 0
    ax.set_title(f"{title} — expanded {shown}/{total_expanded}", fontsize=10)
    fig.tight_layout()
    return fig
