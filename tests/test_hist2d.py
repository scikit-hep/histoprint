"""Tests for the self-contained hist2d package."""

import io

import numpy as np
import pytest

from hist2d import Hist2DFormatter, print_2d_hist, text_hist2d


def test_2d_hist():
    """Test printing of 2D histograms as terminal heatmaps."""

    rng = np.random.default_rng(0)
    x = rng.normal(size=1000)
    y = 0.5 * x + rng.normal(size=1000)

    h2d, xe, ye = np.histogram2d(x, y, bins=10)

    # Basic output: shade characters appear and every line fits the width
    f = io.StringIO()
    print_2d_hist((h2d, xe, ye), file=f, columns=40, lines=14, use_color=False)
    out = f.getvalue()
    assert any(s in out for s in "\u2591\u2592\u2593\u2588")
    assert max(len(line.rstrip()) for line in out.splitlines()) <= 40

    # Title and max_count are supported
    f = io.StringIO()
    print_2d_hist(
        (h2d, xe, ye),
        file=f,
        columns=40,
        lines=14,
        use_color=False,
        title="2D",
        max_count=10,
    )
    assert "2D" in f.getvalue()

    # More bins than plot area are aggregated (downsampling) without crashing
    hbig, xbig, ybig = np.histogram2d(x, y, bins=100)
    print_2d_hist(
        (hbig, xbig, ybig), file=io.StringIO(), columns=30, lines=10, use_color=False
    )

    # histogramdd-style tuple: (H, [xedges, yedges])
    hdd, edges = np.histogramdd(np.column_stack([x, y]), bins=5)
    print_2d_hist(
        (hdd, edges), file=io.StringIO(), columns=30, lines=8, use_color=False
    )

    # text_hist2d thin wrapper around numpy.histogram2d
    f = io.StringIO()
    text_hist2d(x, y, bins=5, file=f, use_color=False, columns=30, lines=8)
    assert f.getvalue()


def test_2d_boost():
    """Test 2D boost-histogram histograms (PlottableHistogram protocol)."""

    bh = pytest.importorskip("boost_histogram")

    hist = bh.Histogram(bh.axis.Regular(10, -3, 3), bh.axis.Regular(10, -3, 3))
    hist.fill(
        np.random.default_rng(1).normal(size=500),
        np.random.default_rng(2).normal(size=500),
    )

    f = io.StringIO()
    print_2d_hist(hist, file=f, columns=30, lines=10, use_color=False)
    assert f.getvalue()


def test_2d_wrong_dimension():
    """Non-2D input must raise a clear error."""

    # 1D numpy histogram tuple
    with pytest.raises(ValueError, match="2D"):
        print_2d_hist(np.histogram(np.arange(10)), file=io.StringIO())

    # 1D counts passed to the formatter directly
    with pytest.raises(ValueError, match="2-dimensional"):
        Hist2DFormatter(np.arange(4), np.arange(4), use_color=False).format_histogram(
            np.arange(3)
        )

    # Empty 2D histogram
    with pytest.raises(ValueError, match="empty"):
        print_2d_hist(
            (np.zeros((0, 5)), np.arange(1), np.arange(6)), file=io.StringIO()
        )


def test_2d_color_output():
    """Default color output contains ANSI escape sequences."""

    rng = np.random.default_rng(0)
    h2d, xe, ye = np.histogram2d(rng.normal(size=500), rng.normal(size=500), bins=5)
    f = io.StringIO()
    print_2d_hist((h2d, xe, ye), file=f, columns=30, lines=8)
    assert "\x1b[" in f.getvalue()

    # No color codes when disabled
    f = io.StringIO()
    print_2d_hist((h2d, xe, ye), file=f, columns=30, lines=8, use_color=False)
    assert "\x1b[" not in f.getvalue()
