import numpy as np
from histoprint import *


def test_hist():
    """Poor man's unit tests."""

    A = np.random.randn(1000) - 2
    B = np.random.randn(1000)
    C = np.random.randn(1000) + 2
    D = np.random.randn(500) * 2

    text_hist(B)
    text_hist(
        B, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5], title="Variable bin widths"
    )

    histA = np.histogram(A, bins=15, range=(-5, 5))
    histB = np.histogram(B, bins=15, range=(-5, 5))
    histC = np.histogram(C, bins=15, range=(-5, 5))
    histD = np.histogram(D, bins=15, range=(-5, 5))
    histAll = ([histA[0], histB[0], histC[0], histD[0]], histA[1])

    print_hist(histAll, title="Overlays", labels="ABCDE")
    print_hist(
        histAll,
        title="Stacks",
        stack=True,
        symbols="      ",
        bg_colors="rgbcmy",
        labels="ABCDE",
    )
    print_hist(
        histAll,
        title="Summaries",
        symbols=r"=|\/",
        fg_colors="0",
        bg_colors="0",
        labels=["AAAAAAAAAAAAAAAA", "B", "CCCCCCCCCCCCC", "D"],
        summary=True,
    )
    print_hist(
        (histAll[0][:3], histAll[1]),
        title="No composition",
        labels=["A", "B", "C"],
    )


def test_boost():
    """Test boost-histogram if it is available."""

    try:
        import boost_histogram as bh
    except:
        return

    hist = bh.Histogram(bh.axis.Regular(20, -3, 3))
    hist.fill(np.random.randn(1000))
    print_hist(hist, title="Boost Histogram")


def test_uproot():
    """Test uproot hsitograms if it is available."""

    try:
        import uproot
        import awkward
    except:
        return

    with uproot.open("tests/data/histograms.root") as F:
        hist = F["one"]

    try:
        # Works with uproot 3
        hist.show()
    except:
        pass
    print_hist(hist, title="uproot TH1")


if __name__ == "__main__":
    test_hist()
    test_boost()
    test_uproot()
