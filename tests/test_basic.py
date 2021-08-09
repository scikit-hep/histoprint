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
    )
    hp.print_hist(
        histAll,
        title="Summaries",
        symbols=r"=|\/",
        fg_colors="0",
        bg_colors="0",
        labels=["AAAAAAAAAAAAAAAA", "B", "CCCCCCCCCCCCC", "D"],
        summary=True,
    )
    hp.print_hist(
        (histAll[0][:3], histAll[1]),
        title="No composition",
        labels=["A", "B", "C"],
    )


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

    try:
        # Works with uproot 3
        hist.show()
    except Exception:
        pass
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
