import contextlib
import io
import re
import warnings

import numpy as np
import pytest
from uhi.numpy_plottable import ensure_plottable_histogram

import histoprint as hp
from histoprint.formatter import HistFormatter, Hixel


def test_hist():
    """Poor man's unit tests."""

    A = np.random.randn(1000) - 2
    B = np.random.randn(1000)
    C = np.random.randn(1000) + 2
    D = np.random.randn(500) * 2

    hp.text_hist(B)
    hp.text_hist(
        B, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5], title="Variable bin widths"
    )

    histA = np.histogram(A, bins=15, range=(-5, 5))
    histB = np.histogram(B, bins=15, range=(-5, 5))
    histC = np.histogram(C, bins=15, range=(-5, 5))
    histD = np.histogram(D, bins=15, range=(-5, 5))
    histAll = ([histA[0], histB[0], histC[0], histD[0]], histA[1])

    hp.print_hist(histAll, title="Overlays", labels="ABCDE")
    hp.print_hist(
        histAll,
        title="Stacks",
        stack=True,
        symbols="      ",
        bg_colors="rgbcmy",
        labels="ABCDE",
        max_count=600.0,
    )
    hp.print_hist(
        histAll,
        title="Summaries",
        symbols=r"=|\/",
        use_color=False,
        labels=["AAAAAAAAAAAAAAAA", "B", "CCCCCCCCCCCCC", "D"],
        summary=True,
    )
    hp.print_hist(
        (histAll[0][:3], histAll[1]),
        title="No composition",
        labels=["A", "B", "C"],
    )


def test_width():
    """Test output width."""
    hist = np.histogram(np.random.randn(100) / 1000)
    f = io.StringIO()
    hp.print_hist(hist, file=f, columns=30, use_color=False)
    f.flush()
    f.seek(0)
    n_max = 0
    for line in f:
        print(line, end="")
        n = len(line.rstrip())
        n_max = np.max((n, n_max))
    assert n_max == 30

    hist = (np.array((100.5, 17.5)), np.array((0, 1, 2)))
    f = io.StringIO()
    hp.print_hist(hist, file=f, columns=30, use_color=False)
    f.flush()
    f.seek(0)
    n_max = 0
    for line in f:
        print(line, end="")
        n = len(line.rstrip())
        n_max = np.max((n, n_max))
    assert n_max == 30


def test_nan():
    """Test dealing with nan values."""

    data = np.arange(7, dtype=float)
    data[5] = np.nan
    bins = np.arange(8)
    hp.print_hist((data, bins))


def test_boost():
    """Test boost-histogram if it is available."""

    bh = pytest.importorskip("boost_histogram")

    hist = bh.Histogram(bh.axis.Regular(20, -3, 3))
    hist.fill(np.random.randn(1000))
    hp.print_hist(hist, title="Boost Histogram")


def test_uproot():
    """Test uproot histograms if it is available."""

    pytest.importorskip("awkward")
    uproot = pytest.importorskip("uproot")

    with uproot.open("tests/data/histograms.root") as F:
        hist = F["one"]

    with contextlib.suppress(Exception):
        # Works with uproot 3
        hist.show()
    hp.print_hist(hist, title="uproot TH1")


def test_stack():
    A = np.random.randn(1000) - 2
    B = np.random.randn(1000)
    C = np.random.randn(1000) + 2
    D = np.random.randn(500) * 2

    hp.text_hist(B)
    hp.text_hist(
        B, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5], title="Variable bin widths"
    )

    histA = np.histogram(A, bins=15, range=(-5, 5))
    histB = np.histogram(B, bins=15, range=(-5, 5))
    histC = np.histogram(C, bins=15, range=(-5, 5))
    histD = np.histogram(D, bins=15, range=(-5, 5))
    histAll = ([histA[0], histB[0], histC[0], histD[0]], histA[1])

    hA = ensure_plottable_histogram(histA)
    hB = ensure_plottable_histogram(histB)
    hC = ensure_plottable_histogram(histC)
    hD = ensure_plottable_histogram(histD)

    hist_stack = [hA, hB, hC, hD]

    out1 = io.StringIO()
    out2 = io.StringIO()

    hp.print_hist(histAll, file=out1, title="Overlays", labels="ABCD")
    hp.print_hist(hist_stack, file=out2, title="Overlays", labels="ABCD")

    assert out1.getvalue() == out2.getvalue()


def test_rich_histogram():
    """Test updating the values of a histogram object."""
    rich = pytest.importorskip("rich")

    from histoprint.rich import (  # noqa: PLC0415 - Conditional import for optional rich support
        RichHistogram,
    )

    A = np.random.randn(1000) - 2
    B = np.random.randn(1000) + 2

    hA = np.histogram(A, bins=np.linspace(-5, 5, 11))
    hB = np.histogram(B, bins=hA[1])

    hist = RichHistogram(hA, columns=30)

    rich.print(hist)

    # Update values
    count = hA[0]
    count += hB[0]

    rich.print(hist)

    from rich.table import (  # noqa: PLC0415 - Conditional import for optional rich support
        Table,
    )

    tab = Table(title="Test table")
    tab.add_column("left justify", justify="left", width=29)
    tab.add_column("center justify", justify="center", width=35)
    tab.add_column("right justify", justify="right", width=35)

    from rich.align import (  # noqa: PLC0415 - Conditional import for optional rich support
        Align,
    )

    tab.add_row(hist, Align.center(hist), Align.right(hist))

    rich.print(tab)


def test_hixel_same_symbol_overlay():
    """Re-adding the same composing symbol must keep the glyph (issue #159)."""
    h = Hixel("/", "W", "0", use_color=False, compose=" ")
    h.add("/", "W", "0")
    # The composing character must survive, not be erased to None.
    assert h.compose == "/"
    # And the rendered Hixel must still contain the "/" composing glyph.
    assert "⃫" in h.render()


def test_integer_edges():
    """Integer bin edges must not crash the formatter (issue #159)."""
    # Through HistFormatter directly.
    HistFormatter(np.arange(5), columns=40).format_histogram(np.zeros(4))

    # Through print_hist with an integer-edge tuple.
    f = io.StringIO()
    hist = (np.array([1, 2, 3, 4]), np.arange(5))
    hp.print_hist(hist, file=f, columns=40, use_color=False)
    assert f.getvalue()

    # And with plain Python list edges.
    hist = (np.array([1, 2, 3, 4]), [0.0, 1.0, 2.0, 3.0, 4.0])
    hp.print_hist(hist, file=io.StringIO(), columns=40, use_color=False)


def test_degenerate_edges_no_warning():
    """All-zero / degenerate edges must not emit numpy RuntimeWarnings."""
    f = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        hp.print_hist((np.zeros(4), np.zeros(5)), file=f, columns=40, use_color=False)
    # The bogus "x 10^+nan" exponent label must not appear.
    assert "nan" not in f.getvalue()


def test_empty_list_raises():
    """An empty input sequence must raise a clear ValueError (issue #159)."""
    with pytest.raises(ValueError, match="empty"):
        hp.print_hist([], file=io.StringIO())


def test_vertical_basic():
    """Vertical mode renders a baseline, bars and stays within the width."""
    rng = np.random.default_rng(0)
    hist = np.histogram(rng.normal(size=500), bins=10, range=(-4, 4))
    f = io.StringIO()
    hp.print_hist(hist, file=f, columns=80, use_color=False, orientation="vertical")
    out = f.getvalue()
    assert out
    # Baseline with the corner marker must be present
    assert "\u2514" in out
    assert "\u2500" in out
    # Some block characters were drawn (non-empty bars)
    assert "\u2588" in out
    # No line exceeds the requested width
    assert max(len(line) for line in out.splitlines()) <= 80


def test_vertical_bar_heights():
    """Bars grow upward from the baseline, one column per bin, height ~ count."""
    counts = np.array([10.0, 20.0, 40.0, 80.0])
    edges = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    f = io.StringIO()
    hp.print_hist(
        (counts, edges),
        file=f,
        columns=60,
        lines=12,
        use_color=False,
        max_count=80.0,
        count_area=False,
        orientation="vertical",
    )
    out = f.getvalue().splitlines()
    baseline = out.index(next(ln for ln in out if "\u2514" in ln))
    # The bar area starts at the baseline corner column.
    bar0 = out[baseline].index("\u2514")
    # 4 equal bins over the 51-column plot area are drawn as [13, 13, 13, 12].
    widths = [13, 13, 13, 12]
    starts = [0, *np.cumsum(widths)]
    bar_left = [bar0 + s for s in starts[:-1]]
    # plot_rows = number of bar rows above the baseline (the header is row 0).
    plot_rows = baseline - 1
    assert plot_rows == 9
    # Heights are deterministic for these fixed parameters (standard test, not
    # re-derived from the formatter internals).
    heights = [1, 2, 4, 9]
    # The tallest bar must fill the plot area; the empty/short bars must not.
    for h in range(1, max(heights) + 1):
        row = out[baseline - h]
        cols = [i for i, ch in enumerate(row) if ch == "\u2588"]
        present = [i for i in range(4) if heights[i] >= h]
        expected_cols = set()
        for i in present:
            expected_cols.update(
                range(bar_left[i], bar_left[i] + (starts[i + 1] - starts[i]))
            )
        assert set(cols) == expected_cols, (
            f"h={h}: cols {sorted(cols)} != {sorted(expected_cols)}"
        )


def test_vertical_composing_symbols():
    """The / and \\ symbols must be drawn vertically like horizontally."""
    rng = np.random.default_rng(0)
    edges = np.linspace(-4, 4, 11)
    counts = [np.histogram(rng.normal(i, 1, 200), bins=edges)[0] for i in range(5)]
    f = io.StringIO()
    hp.print_hist(
        (counts, edges),
        file=f,
        orientation="vertical",
        columns=60,
        lines=14,
        use_color=False,
        symbols="|=/\\",
    )
    out = f.getvalue()
    assert "\u20e5" in out or "\u20eb" in out


def test_vertical_matches_horizontal_summary():
    """Totals, averages and stds in the summary are orientation-independent."""
    rng = np.random.default_rng(1)
    a = np.histogram(rng.normal(-2, 1, 1000), bins=12, range=(-5, 5))[0]
    b = np.histogram(rng.normal(2, 1, 1000), bins=12, range=(-5, 5))[0]
    # Large edges exercise the common-exponent scaling of the summary values.
    edges = np.linspace(-50000, 50000, 13)
    hist_all = ([a, b], edges)

    fh = io.StringIO()
    hp.print_hist(
        hist_all,
        file=fh,
        columns=90,
        use_color=False,
        summary=True,
        labels=["A", "B"],
    )
    fv = io.StringIO()
    hp.print_hist(
        hist_all,
        file=fv,
        columns=90,
        use_color=False,
        summary=True,
        labels=["A", "B"],
        orientation="vertical",
    )

    def summary_lines(buf):
        return [
            ln
            for ln in buf.getvalue().splitlines()
            if ln.strip()[:4] in ("Tot:", "Avg:", "Std:")
        ]

    lines_h = summary_lines(fh)
    lines_v = summary_lines(fv)
    assert lines_h
    assert lines_v
    assert [ln.split() for ln in lines_h] == [ln.split() for ln in lines_v]


def test_vertical_stack_and_overlay():
    """Both stacked and overlaid multi-histograms render vertically."""
    rng = np.random.default_rng(2)
    a = np.histogram(rng.normal(size=300), bins=8)[0]
    b = np.histogram(rng.normal(size=300), bins=8)[0]
    hist_all = ([a, b], np.histogram(rng.normal(size=10), bins=8)[1])
    for stack in (True, False):
        f = io.StringIO()
        hp.print_hist(
            hist_all,
            file=f,
            columns=70,
            use_color=False,
            symbols="=|",
            stack=stack,
            orientation="vertical",
        )
        assert f.getvalue()


def test_vertical_invalid_orientation():
    """An unknown orientation is rejected early."""
    with pytest.raises(ValueError, match="orientation"):
        HistFormatter(np.arange(5), orientation="diagonal")


def test_vertical_degenerate_edges():
    """Zero-width / empty data must not crash vertical mode."""
    f = io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        hp.print_hist(
            (np.zeros(4), np.arange(5)),
            file=f,
            columns=50,
            use_color=False,
            orientation="vertical",
        )
    assert "nan" not in f.getvalue()


def test_vertical_many_bins_fits_width():
    """More bins than columns must stay within the requested width."""
    counts = np.arange(40, dtype=float)
    edges = np.arange(41, dtype=float)
    f = io.StringIO()
    hp.print_hist(
        (counts, edges),
        file=f,
        columns=45,
        lines=12,
        use_color=False,
        orientation="vertical",
    )
    out = f.getvalue()
    assert max(len(line) for line in out.splitlines()) <= 45
    # Dense labels must not merge into a single ambiguous token like "1.63.07".
    lines_out = out.splitlines()
    label_row = lines_out[-1]
    assert not re.search(r"\d\.\d+\.\d", label_row)
    # The maximum edge is always labelled (edges are scaled by x 10^+01).
    assert label_row.rstrip().endswith("4")
    # No data is dropped: the tallest (last) bins reach the top of the plot.
    top_row = lines_out[1]
    assert top_row.rstrip().endswith("\u2588")
    # All counts contribute: the surplus bins are merged, not cut.
    assert "/col" in lines_out[0]
    bars = [ln for ln in lines_out if "\u2588" in ln]
    assert len(bars) == 9


def test_vertical_final_label_kept():
    """The maximum edge label wins over a colliding neighbour."""
    counts = np.ones(15)
    edges = np.linspace(-3.9, 3.07, 16)
    f = io.StringIO()
    hp.print_hist(
        (counts, edges),
        file=f,
        columns=40,
        lines=8,
        use_color=False,
        orientation="vertical",
    )
    label_row = f.getvalue().splitlines()[-1]
    assert label_row.rstrip().endswith("3.07")
    assert label_row.lstrip().startswith("-3.9")
    assert "  " in label_row.strip()  # labels never touch


def test_counts_mismatch_raises():
    """A count array with the wrong number of bins raises a clear error."""
    # np.arange(4) defines 3 bins, so a 2-entry count must be rejected.
    # Exercised through HistFormatter directly (print_hist routes 1D input
    # through the uhi PlottableProtocol, which validates edges first).
    formatter = HistFormatter(np.arange(4), columns=40, orientation="vertical")
    with pytest.raises(ValueError, match="but the edges define"):
        formatter.format_histogram(np.array([1.0, 2.0]))
