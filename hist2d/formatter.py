"""Self-contained formatter for 2D histograms (terminal heatmaps).

This module has no dependency on the 1D histoprint machinery. It accepts
``numpy.histogram2d``/``histogramdd`` tuples as well as any object following
the ``PlottableHistogram`` protocol (e.g. ``boost_histogram.Histogram``) with
exactly two axes.
"""

from __future__ import annotations

import math
import shutil
import sys
from collections.abc import Sequence

import numpy as np
from uhi.numpy_plottable import ensure_plottable_histogram

# Ramp of shading characters used to encode 2D bin content (lowest -> highest)
DEFAULT_2D_SYMBOLS = " \u2591\u2592\u2593\u2588"
# Heat-map colour ramp (lowest -> highest)
DEFAULT_2D_FG_COLORS = "kKrRyYw"
TICK_FORMAT = "{: #7.3f}"

_ANSI_CODES = {
    "k": 30,
    "r": 31,
    "g": 32,
    "y": 33,
    "b": 34,
    "m": 35,
    "c": 36,
    "w": 37,
    "0": 39,  # Reset to default
    "K": 90,
    "R": 91,
    "G": 92,
    "Y": 93,
    "B": 94,
    "M": 95,
    "C": 96,
    "W": 97,
}

__all__ = [
    "Hist2DFormatter",
    "get_2d_count_edges",
    "print_2d_hist",
    "text_hist2d",
]


def _ansi(fg, bg, use_color):
    """Return the ANSI escape sequence for a foreground/background colour."""

    if not use_color:
        return ""
    return f"\x1b[{_ANSI_CODES[fg]};{_ANSI_CODES[bg]}m"


def _get_plottable_protocol_bin_edges(axis):
    """Get histogram bin edges from a PlottableAxis.

    Borrowed from ``mplhep.utils``.

    """

    out = np.empty(len(axis) + 1)
    if not isinstance(axis[0], tuple):
        msg = f"Currently only support non-discrete axes {axis}"
        raise TypeError(msg)
    out[0] = axis[0][0]
    out[1:] = [axis[i][1] for i in range(len(axis))]
    return out


class Hist2DFormatter:
    """Class that handles the formatting of 2D histograms.

    Every bin of the 2D histogram is rendered as a single terminal character.
    The bin content is encoded with a ramp of shading characters (and,
    optionally, terminal colors), so the resulting plot looks like a heatmap.

    Parameters
    ----------
    edges_x, edges_y : array-like
        The bin edges along the two axes.
    lines, columns : int, optional
        The number of lines and maximum number of columns of the output.
    title : str, optional
        Title string to print over the histogram.
    symbols : str, optional
        Ramp of characters used to encode the bin content, from lowest to
        highest. Defaults to ``" ░▒▓█"``.
    fg_colors : str, optional
        Ramp of terminal colors used to encode the bin content, from lowest to
        highest. Defaults to ``"kKrRyYw"`` (heat-map-style ramp).
    max_count : float / int, optional
        Set the maximum bin content for plotting. Otherwise the largest bin
        will fill the available "heat" range.
    use_color : bool, optional
        Whether to use terminal colors. Defaults to being enabled whenever
        color codes are set in ``fg_colors``.

    Notes
    -----
    Colors are specified as one character out of "0rgbcmykwRGBCMYKW". If the
    histogram has more bins than the available plot area, groups of adjacent
    bins are averaged, so a heatmap can still be shown.

    """

    def __init__(
        self,
        edges_x,
        edges_y,
        lines=None,
        columns=None,
        title="",
        symbols=DEFAULT_2D_SYMBOLS,
        fg_colors=DEFAULT_2D_FG_COLORS,
        max_count=None,
        use_color=None,
    ):
        self.title = title
        self.edges_x = np.asarray(edges_x, dtype=float)
        self.edges_y = np.asarray(edges_y, dtype=float)

        # Fit histograms into the terminal, unless otherwise specified
        term_size = shutil.get_terminal_size()
        if columns is None:
            columns = term_size.columns - 1
        if lines is None:
            # Try to keep a constant aspect ratio
            lines = min(int(columns / 3.5) + 1, term_size.lines - 1)
        self.lines = lines
        self.columns = columns
        self.max_count = max_count

        self.symbols = symbols or " "
        self.fg_colors = fg_colors or "0"
        if use_color is None:
            self.use_color = any(c != "0" for c in self.fg_colors)
        else:
            self.use_color = use_color
        self.tick_format = TICK_FORMAT
        self.tick_width = len(self.tick_format.format(0.0))

    def format_histogram(self, counts):
        """Format 2D histogram counts as a terminal heatmap.

        Parameters
        ----------
        counts : ndarray
            The 2D histogram entries to be plotted.

        """

        counts = np.nan_to_num(np.array(counts, dtype=float))
        if counts.ndim != 2:
            msg = "Hist2DFormatter requires 2-dimensional counts"
            raise ValueError(msg)
        if counts.size == 0:
            msg = "Cannot plot an empty 2D histogram"
            raise ValueError(msg)

        max_c = (
            float(np.max(counts)) if self.max_count is None else float(self.max_count)
        )
        if max_c == 0.0:
            max_c = 1.0

        # Reserved lines for the x-axis, its tick labels and the legend
        extra_lines = 3
        title_lines = 1 if self.title else 0
        plot_height = max(self.lines - extra_lines - title_lines, 1)
        plot_width = max(self.columns - self.tick_width - 1, 1)

        # Fit the histogram into the plot area
        grid = self._fit(counts, plot_width, axis=1)
        grid = self._fit(grid, plot_height, axis=0)
        ny_grid, nx_grid = grid.shape
        nx = counts.shape[0]
        ny = counts.shape[1]

        # Normalized bin content, in [0, 1]
        norm = np.clip(grid / max_c, 0.0, 1.0)
        n_symbols = len(self.symbols)
        n_colors = len(self.fg_colors)
        symbol_idx = np.round(norm * (n_symbols - 1)).astype(int)
        color_idx = np.minimum((norm * n_colors).astype(int), n_colors - 1)

        out = []
        if self.title:
            out.append(f"{self.title: ^{self.columns:d}s}\n")

        # Rows are printed top (highest y) to bottom (lowest y)
        for r in range(ny_grid - 1, -1, -1):
            y_value = self._axis_label_value(self.edges_y, r, ny_grid, ny)
            label = self._format_edge(y_value)
            cells = "".join(
                self._cell(int(symbol_idx[r, c]), int(color_idx[r, c]))
                for c in range(nx_grid)
            )
            out.append(f"{label:>{self.tick_width}} {cells}\n")

        # X-axis line with tick marks at bin boundaries when they fit
        out.append(" " * self.tick_width + " " + self._axis_line(nx, plot_width) + "\n")

        # X tick labels
        out.append(
            " " * self.tick_width + " " + self._x_tick_labels(nx, plot_width) + "\n"
        )

        # Legend: low value, color/shade ramp, high value
        legend = f"{0:g} {self.symbols} {max_c:g}"
        out.append(" " * self.tick_width + " " + f"{legend:<{plot_width:d}}\n")

        return "".join(out)

    @staticmethod
    def _fit(values, n_cells, axis):
        """Fit ``values`` to ``n_cells`` along ``axis``.

        Bins are stretched if there are fewer bins than cells. If there are
        more bins than cells, groups of adjacent bins are averaged.

        """

        n = values.shape[axis]
        if n == n_cells:
            return values
        if n < n_cells:
            idx = np.minimum((np.arange(n_cells) * n) // n_cells, n - 1)
            return np.take(values, idx, axis=axis)
        bounds = np.linspace(0, n, n_cells + 1)
        starts = np.floor(bounds[:-1]).astype(int)
        ends = np.maximum(np.ceil(bounds[1:]).astype(int), starts + 1)
        parts = [
            np.take(values, np.arange(start, end), axis=axis).mean(axis=axis)
            for start, end in zip(starts, ends, strict=True)
        ]
        return np.stack(parts, axis=axis)

    def _cell(self, symbol_idx, color_idx):
        """Render a single heatmap cell as a string."""

        symbol = self.symbols[symbol_idx]
        # Blank cells (and color-free output) need no ANSI sequences
        if not self.use_color or symbol == " ":
            return symbol
        fg = self.fg_colors[color_idx]
        return _ansi(fg, "0", True) + symbol + _ansi("0", "0", True)

    def _format_edge(self, value):
        """Format an axis value, guarding against overly long numbers."""

        formatted = self.tick_format.format(float(value))
        if len(formatted) > self.tick_width:
            formatted = f"{float(value):7.3g}"
        return formatted

    @staticmethod
    def _axis_label_value(edges, index, n_grid, n):
        """Value to label grid row/column ``index`` (0 = lowest)."""

        if index == n_grid - 1:
            return edges[-1]
        return edges[min(int(np.floor(index * n / n_grid)), n - 1)]

    def _axis_line(self, n_bins, plot_width):
        """Draw the horizontal axis with bin boundary tick marks."""

        if plot_width == 1:
            return "\u2518"
        line = ["\u2514"] + ["\u2500"] * (plot_width - 2) + ["\u2518"]
        if n_bins <= plot_width:
            # Each boundary between two output columns is a real bin edge
            axis_map = np.minimum(
                (np.arange(plot_width) * n_bins) // plot_width, n_bins - 1
            )
            for c in range(1, plot_width):
                if axis_map[c] != axis_map[c - 1]:
                    line[c] = "\u252c"
        return "".join(line)

    def _x_tick_labels(self, n_bins, plot_width):
        """Create the line with (sparse) x tick labels."""

        max_labels = max(1, plot_width // max(self.tick_width, 1))
        step = max(self.tick_width, math.ceil(plot_width / max_labels))

        line = [" "] * plot_width

        def place(c, value):
            text = self._format_edge(value)
            # Left-align on the column, keeping the label inside the plot
            pos = max(0, min(c, plot_width - len(text)))
            for i, char in enumerate(text):
                p = pos + i
                if 0 <= p < plot_width:
                    line[p] = char

        # Always show the right-most (maximum) value, right-aligned in the plot
        end_text = self._format_edge(
            self._axis_label_value(self.edges_x, plot_width - 1, plot_width, n_bins)
        )
        end_start = plot_width - len(end_text)
        place(plot_width - 1, self.edges_x[-1])

        for c in range(0, plot_width, step):
            # Stop before the end label would be overwritten
            if c + self.tick_width > end_start:
                break
            value = self._axis_label_value(self.edges_x, c, plot_width, n_bins)
            place(c, value)
        return "".join(line)


def get_2d_count_edges(hist):
    """Get bin contents and edges from a compatible 2D histogram.

    Supports the ``(H, xedges, yedges)`` and ``(H, [xedges, yedges])`` tuples
    (e.g. from ``numpy.histogram2d``/``numpy.histogramdd``) as well as any
    object following the ``PlottableHistogram`` protocol (e.g.
    ``boost_histogram.Histogram``) with exactly two axes.

    """

    if isinstance(hist, Sequence) and len(hist) == 0:
        msg = "Cannot plot an empty histogram"
        raise ValueError(msg)

    hist = ensure_plottable_histogram(hist)

    axes = hist.axes
    if len(axes) != 2:
        msg = f"Expected a 2D histogram with 2 axes, got {len(axes)}"
        raise ValueError(msg)

    counts = np.asarray(hist.values())
    if counts.ndim != 2:
        msg = f"Expected 2D counts, got {counts.ndim} dimension(s)"
        raise ValueError(msg)
    if counts.size == 0:
        msg = "Cannot plot an empty 2D histogram"
        raise ValueError(msg)

    edges_x = _get_plottable_protocol_bin_edges(axes[0])
    edges_y = _get_plottable_protocol_bin_edges(axes[1])
    return counts, edges_x, edges_y


def print_2d_hist(hist, file=None, **kwargs):
    """Plot the output of ``numpy.histogram2d`` to the console.

    The 2D histogram is rendered as a terminal heatmap, where every bin is
    encoded by a shading character (and color, if enabled).

    Parameters
    ----------
    file : optional
        File like object to print to.
    **kwargs :
        Additional keyword arguments are passed to the `Hist2DFormatter`.

    """

    if file is None:
        file = sys.stdout
    counts, edges_x, edges_y = get_2d_count_edges(hist)
    hist_formatter = Hist2DFormatter(edges_x, edges_y, **kwargs)
    file.write(hist_formatter.format_histogram(counts))
    file.flush()


def text_hist2d(*args, density=None, **kwargs):
    """Thin wrapper around ``numpy.histogram2d``."""

    print_kwargs = {
        "file": kwargs.pop("file", sys.stdout),
        "title": kwargs.pop("title", ""),
        "symbols": kwargs.pop("symbols", DEFAULT_2D_SYMBOLS),
        "fg_colors": kwargs.pop("fg_colors", DEFAULT_2D_FG_COLORS),
        "use_color": kwargs.pop("use_color", None),
        "max_count": kwargs.pop("max_count", None),
        "lines": kwargs.pop("lines", None),
        "columns": kwargs.pop("columns", None),
    }
    kwargs["density"] = density
    hist = np.histogram2d(*args, **kwargs)
    print_2d_hist(hist, **print_kwargs)
    return hist
