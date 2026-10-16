# ruff: noqa: T201  (this is a runnable demonstration script)

"""Side-by-side comparison: horizontal vs vertical histogram bins.

Run with:  python examples/compare_orientations.py
"""

from __future__ import annotations

import io
import shutil
from itertools import zip_longest

import numpy as np

from histoprint import print_hist


def capture(hist, **kwargs) -> list[str]:
    buf = io.StringIO()
    print_hist(hist, file=buf, **kwargs)
    return buf.getvalue().rstrip("\n").split("\n")


def side_by_side(left: list[str], right: list[str]) -> str:
    width = max((len(ln) for ln in left), default=0)
    rows = []
    for l, r in zip_longest(left, right, fillvalue=""):
        rows.append(f"{l:<{width}}   {r}")
    return "\n".join(rows)


def main() -> None:
    rng = np.random.default_rng(7)
    data = np.concatenate([rng.normal(-2, 1, 800), rng.normal(2.5, 1, 400)])
    hist = np.histogram(data, bins=24, range=(-6, 6))

    columns = min(60, (shutil.get_terminal_size().columns - 3) // 2)
    lines = 22

    common = {"columns": columns, "lines": lines, "use_color": False}

    left = capture(hist, title="HORIZONTAL", **common)
    right = capture(hist, title="VERTICAL", orientation="vertical", **common)

    print(side_by_side(left, right))
    print()
    print("=" * (2 * columns + 3))
    print("Notes on the comparison")
    print("=" * (2 * columns + 3))
    print(
        "HORIZONTAL: one row per bin, bar grows right.\n"
        "  * Many bins / long labels stay readable (each bin owns a row).\n"
        "  * Classic ROOT 'text histogram' look.\n\n"
        "VERTICAL: one column per bin, bar grows up.\n"
        "  * Matches the mental model of a printed bar chart.\n"
        "  * Count axis on the left with numeric tick marks (0 at the\n"
        "    baseline, max on top); bin-edge labels with ticks below.\n"
        "  * Better when the variable range is short but you want the\n"
        "    shape to read left-to-right like a normal plot.\n"
        "  * Wide ranges / many bins can crowd the x-axis labels."
    )

    print()
    print("-" * (2 * columns + 3))
    print("Overlaid distributions, both orientations (colour)")
    print("-" * (2 * columns + 3))
    a = np.histogram(rng.normal(0, 1, 1000), bins=15, range=(-4, 4))
    b = np.histogram(rng.normal(1.5, 1, 1000), bins=15, range=(-4, 4))
    multi = ([a[0], b[0]], a[1])
    print_hist(multi, title="HORIZONTAL overlay", labels="AB", columns=80, lines=18)
    print_hist(
        multi,
        title="VERTICAL overlay",
        labels="AB",
        orientation="vertical",
        columns=80,
        lines=18,
    )


if __name__ == "__main__":
    main()
