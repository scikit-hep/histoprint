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


if __name__ == "__main__":
    test_hist()
