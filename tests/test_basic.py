import contextlib
import io

import numpy as np
import pytest
from uhi.numpy_plottable import ensure_plottable_histogram

import histoprint as hp


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

    from histoprint.rich import RichHistogram

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

    from rich.table import Table

    tab = Table(title="Test table")
    tab.add_column("left justify", justify="left", width=29)
    tab.add_column("center justify", justify="center", width=35)
    tab.add_column("right justify", justify="right", width=35)

    from rich.align import Align

    tab.add_row(hist, Align.center(hist), Align.right(hist))

    rich.print(tab)
