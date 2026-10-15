"""Module for plotting Numpy-like 1D histograms to the terminal."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Sequence
from itertools import cycle

import numpy as np
from uhi.numpy_plottable import ensure_plottable_histogram
from uhi.typing.plottable import PlottableHistogram

DEFAULT_SYMBOLS = " |=/\\"
COMPOSING_SYMBOLS = "/\\"
DEFAULT_FG_COLORS = "WWWWW"
DEFAULT_BG_COLORS = "K0000"

__all__ = ["HistFormatter", "print_hist", "text_hist"]


class Hixel:
    """The smallest unit of a histogram plot."""

    def __init__(self, char=" ", fg="0", bg="0", use_color=True, compose=" "):
        self.character = " "
        self.compose: str | None = compose
        self.fg_color = fg
        self.bg_color = bg
        self.use_color = use_color
        self.add(char, fg, bg)

    def add(self, char=" ", fg="0", bg="0"):
        """Add another element on top."""

        allowed = r" =|\/"
        if char not in allowed:
            msg = f"Symbol not one of the allowed: {allowed!r}"
            raise ValueError(msg)

        if fg == self.fg_color:
            # Combine characters if possible
            char_combinations = {
                ("|", "="): "#",
                ("=", "|"): "#",
                ("#", "="): "#",
                ("#", "|"): "#",
            }
            compose_chars = r"\/"
            compose_combinations = {
                ("/", "\\"): "X",
                ("\\", "/"): "X",
                (" ", "\\"): "\\",
                (" ", "/"): "/",
                ("/", "/"): "/",
                ("\\", "\\"): "\\",
                ("X", "/"): "X",
                ("X", "\\"): "X",
                ("X", "X"): "X",
            }
            if char in compose_chars:
                if self.compose is not None:
                    # Fall back to the existing composing character (e.g. when
                    # re-adding the same symbol, or composing onto an "X") so
                    # the glyph is never erased.
                    self.compose = compose_combinations.get(
                        (self.compose, char), self.compose
                    )
            else:
                self.character = char_combinations.get((self.character, char), char)
        elif char != " ":
            # Otherwise overwrite if it is not a " "
            self.character = " "
            self.fg_color = fg
            self.add(char, fg, bg)

        if bg != "0":
            self.bg_color = bg

    def render(self, reset=True):
        """Render the Hixel as a string."""
        ret = ""
        if (
            self.character == " "
            and (self.compose == " " or self.compose is None)
            and self.bg_color != "0"
        ):
            # Instead of printing a space with BG color,
            # print a full block with same FG color,
            # so the histogram can be copied to text editors.
            # Replace BG colour with opposite brightness,
            # so it shows when the text is selected in a terminal.
            ret += self.ansi_color_string(self.bg_color, self.bg_color.swapcase())
            ret += "\u2588"
        else:
            ret += self.ansi_color_string(self.fg_color, self.bg_color)
            ret += self.substitute_character(self.character, self.compose)
        if reset:
            ret += self.ansi_color_string("0", "0")
        return ret

    @staticmethod
    def substitute_character(char, compose):
        r"""Replace some ASCII characters with better looking Unicode.

        Substitutions::

            "|" -> "\u2502"
            "=" -> "\u2550"
            "#" -> "\u256A"
            "\" -> " \u20e5"
            "/" -> " \u20eb"
            "X" -> " \u20e5\u20eb"

        """

        subs = {
            "|": "\u2502",
            "=": "\u2550",
            "#": "\u256a",
            "\\": "\u20e5",
            "/": "\u20eb",
            "X": "\u20e5\u20eb",
            None: "",
        }

        ret = subs.get(char, char)
        # Characters can be displayed differently when they have a composing character on top.
        # This looks ugly if some Hixels of a histogram are covered by another and some are not.
        # Unless explicitly asked for no composition, if no composition is added,
        # use empty composition character to make them all display the same.
        ret += subs.get(compose, "\u034f")

        return ret

    def ansi_color_string(self, fg, bg):
        """Set the terminal color."""
        ret = ""
        if self.use_color:
            # The ANSI color codes
            subs = {
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
            fg = subs[fg]
            bg = subs[bg] + 10

            ret += f"\033[{fg:d};{bg:d}m"
        return ret


class BinFormatter:
    """Class that turns bin contents into text.

    Parameters
    ----------

    scale : float
        The scale of the histogram, i.e. one text character corresponds to
        `scale` counts.
    count_area : bool, optional
        Whether the bin content is represented by the area or height of the bin.
    tick_format : str, optional
        The format string for tick values.
    tick_mark : str, optional
        Character of the tick mark.
    no_tick_mark : str, optional
        Character to be printed for axis without tick.
    print_top_edge : bool, optional
        Whether to print the top or bottom edge of the bin.
    symbols : iterable, optional
        The foreground symbols to be used for the histograms.
    fg_colors : iterable, optional
        The foreground colours to be used.
    bg_colors : iterable, optional
        The background colours to be used.
    stack : bool, optional
        Whether to stack the histograms, or overlay them.
    use_color : bool, optional
        Whether to use color output.

    Notes
    -----

    Colours are specified as one character out of "0rgbcmykwRGBCMYKW". These
    are mapped to the terminal's default colour scheme. A "0" denotes the
    default foreground colour or "transparent" background. The capital letters
    denote the bright versions of the lower case ones.

    """

    def __init__(
        self,
        scale=1.0,
        count_area=True,
        tick_format="{: #7.3f} ",
        tick_mark="_",
        no_tick_mark=" ",
        print_top_edge=False,
        symbols=DEFAULT_SYMBOLS,
        fg_colors=DEFAULT_FG_COLORS,
        bg_colors=DEFAULT_BG_COLORS,
        stack=False,
        use_color=None,
    ):
        self.scale = scale
        self.count_area = count_area
        self.tick_format = tick_format
        self.tick_format_width = len(tick_format.format(0.0))
        self.tick_mark = tick_mark
        self.no_tick_mark = no_tick_mark
        self.print_top_edge = print_top_edge
        self.symbols = symbols or " "
        self.fg_colors = fg_colors or "0"
        self.bg_colors = bg_colors or "0"
        self.stack = stack
        if use_color is None:
            self.use_color = any(c != "0" for c in fg_colors + bg_colors)
        else:
            self.use_color = use_color
        self.compose: str | None = None

    def format_bin(self, top, bottom, counts, width=1):
        """Return a string that represents the bin.

        Parameters
        ----------

        top : float
            The top edge of the bin
        bottom : float
            The bottom edge of the bin
        counts : iterable
            The counts for each histogram in the bin
        width : int
            The width of the bin in lines

        """

        # Adjust scale by width if area represents counts
        scale = self.scale * (width if self.count_area else 1)

        if scale == 0:
            scale = 1.0

        # Calculate bin heights in characters
        heights = [int(c // scale) for c in counts]

        # Decide whether to use composing characters
        for s in self.symbols[: len(counts)]:
            if s in COMPOSING_SYMBOLS:
                self.compose = " "
                break
        else:
            self.compose = None

        # Format bin
        bin_string = []
        for i_line in range(width):
            # Print axis
            if self.print_top_edge and i_line == 0:
                bin_string.append(self.tick(top))
            elif not self.print_top_edge and i_line == (width - 1):
                bin_string.append(self.tick(bottom))
            else:
                bin_string.append(self.no_tick())

            # Print symbols
            line = []
            for h, s, fg, bg in zip(
                heights,
                cycle(self.symbols),
                cycle(self.fg_colors),
                cycle(self.bg_colors),
            ):
                if h:
                    if self.stack:
                        # Just print them all after one another
                        line += [
                            Hixel(s, fg, bg, self.use_color, self.compose)
                            for _ in range(h)
                        ]
                    # Overlay histograms
                    elif h > len(line):
                        for hix in line:
                            hix.add(s, fg, bg)
                        line += [
                            Hixel(s, fg, bg, self.use_color, self.compose)
                            for _ in range(h - len(line))
                        ]
                    else:
                        for hix in line[:h]:
                            hix.add(s, fg, bg)

            for hix in line:
                bin_string.append(hix.render())

            # New line
            bin_string.append("\n")

        return "".join(bin_string)

    def tick(self, edge):
        """Format the tick mark of a bin."""
        return self.tick_format.format(edge) + self.tick_mark

    def no_tick(self):
        """Format the axis without a tick mark."""
        return " " * self.tick_format_width + self.no_tick_mark


class HistFormatter:
    """Class that handles the formatting of histograms.

    Parameters
    ----------

    lines, columns : int, optional
        The number of lines and maximum number of columns of the output.
    count_area : bool, optional
        Whether the bin content is represented by the area or height of the bin.
    scale_bin_width : bool, optional
        Whether the lines per bin should scale with the bin width.
    title : str, optional
        Title string to print over the histogram.
    labels : iterable, optional
        Labels the histograms.
    summary : bool, optional
        Whether to print a summary of the histograms.
    max_count : float / int, optional
        Set the maximum bin content for plotting. Otherwise largest bin will
        fill the available width. Should be a count density of counts per row
        if `count_area` is set.
    orientation : {"horizontal", "vertical"}, optional
        Direction in which the bins are plotted. "horizontal" (default) gives
        one row per bin with bars extending to the right. "vertical" gives one
        column per bin with bars extending upwards.
    **kwargs : optional
        Additional keyword arguments are passed to the `BinFormatter`

    Notes
    -----

    The `HistFormatter` will try to fit everything within the requested number
    of lines, but this is not guaranteed. The final number of lines can be
    bigger or smaller, depending on the number of bins and their widths.

    """

    def __init__(
        self,
        edges,
        lines=None,
        columns=None,
        scale_bin_width=True,
        title="",
        labels=("",),
        summary=False,
        max_count=None,
        orientation="horizontal",
        **kwargs,
    ):
        if orientation not in {"horizontal", "vertical"}:
            msg = f"orientation must be 'horizontal' or 'vertical', got {orientation!r}"
            raise ValueError(msg)
        self.orientation = orientation
        self.title = title
        self.edges = np.asarray(edges, dtype=float)
        # Fit histograms into the terminal, unless otherwise specified
        term_size = shutil.get_terminal_size()
        if columns is None:
            columns = term_size.columns - 1
        if lines is None:
            # Try to keep a constant aspect ratio
            lines = min(int(columns / 3.5) + 1, term_size.lines - 1)
        self.lines = lines
        self.columns = columns
        self.summary = summary
        self.labels = labels
        self.max_count = max_count

        self.hist_lines = lines - 1  # Less one line for the first tick
        if self.title:
            # Make room for the title
            self.hist_lines -= 1
        if orientation == "vertical":
            # Make room for the x-axis line and its bin-edge labels
            self.hist_lines -= 2

        if self.summary:
            # Make room for a summary at the bottom
            self.hist_lines -= 4
        elif any(len(lab) > 0 for lab in self.labels):
            # Make room for a legend at the bottom
            self.hist_lines -= 1
        self.hist_lines = max(self.hist_lines, 1)

        if scale_bin_width:
            # Try to scale bins so the number of lines is
            # roughly proportional to the bin width
            line_scale = (
                (self.edges[-1] - self.edges[0]) / self.hist_lines
            ) * 0.999  # <- avoid rounding issues
        else:
            # Choose the largest bin as scale,
            # so all bins will scale to <= 1 lines
            # and be rendered with one line
            line_scale = np.max(self.edges[1:] - self.edges[:-1])
        if line_scale == 0.0:
            line_scale = 1.0
        self.bin_lines = ((self.edges[1:] - self.edges[:-1]) // line_scale).astype(int)
        self.bin_lines = np.where(self.bin_lines, self.bin_lines, 1)
        self.bin_formatter = BinFormatter(**kwargs)

    def format_histogram(self, counts):
        """Format (a set of) histogram counts.

        Parameters
        ----------

        counts : ndarray
            The histogram entries to be plotted.

        """

        if self.orientation == "vertical":
            return self._format_histogram_vertical(counts)

        axis_width = self.bin_formatter.tick_format_width + len(
            self.bin_formatter.tick_mark
        )
        hist_width = self.columns - axis_width

        counts = self._normalise_counts(counts)

        # Get max or total counts in each bin
        if self.bin_formatter.stack:
            # Bin content will be sum of all histograms
            tot_c = np.sum(counts, axis=0)
        else:
            # Bin content will be maximum of all histograms
            tot_c = np.max(counts, axis=0)

        # Get bin lengths
        # Bin content will be divided by number of lines
        c = tot_c / self.bin_lines if self.bin_formatter.count_area else tot_c

        # Set a scale so that largest bin fills width of allocated area
        max_c = np.max(c) if self.max_count is None else self.max_count

        symbol_scale = max_c / hist_width
        self.bin_formatter.scale = symbol_scale * 0.999  # <- avoid rounding issues

        hist_string = []

        # Write the title line
        if self.title:
            hist_string.append(f"{self.title: ^{self.columns:d}s}\n")

        # Get bin edges, scaled by the common exponent
        common_exponent, ce_string = self._scale_string()
        top = np.array(self.edges[:-1]) / 10**common_exponent
        bottom = np.array(self.edges[1:]) / 10**common_exponent

        # Write the first tick, common exponent and horizontal axis
        hist_string.append(self.bin_formatter.tick(top[0]))
        hist_string.append(ce_string)
        if self.bin_formatter.count_area:
            longest_count = f"{max_c:g}/row"
        else:
            longest_count = f"{max_c:g}"
        hist_string.append(
            f"{longest_count:>{hist_width - len(ce_string) - 2:d}s} \u2577\n"
        )

        # Write the bins
        for c, t, b, w in zip(counts.T, top, bottom, self.bin_lines, strict=True):
            hist_string.append(self.bin_formatter.format_bin(t, b, c, w))

        if self.summary:
            hist_string.append(self.summarize(counts, top, bottom))
        elif any(len(lab) > 0 for lab in self.labels):
            hist_string.append(self.summarize(counts, top, bottom, legend_only=True))

        return "".join(hist_string)

    def _scale_string(self):
        """Return ``(common_exponent, ce_string)`` for the bin edges.

        ``ce_string`` is the ``" x 10^NNN"`` suffix (empty for small edges),
        guarded against all-zero edges. Shared by both orientations.
        """
        max_edge = float(np.max(np.abs(self.edges))) if self.edges.size else 0.0
        common_exponent = 0.0 if max_edge == 0 else np.floor(np.log10(max_edge))
        ce_string = f" x 10^{common_exponent:+03.0f}" if common_exponent != 0 else ""
        return common_exponent, ce_string

    def _normalise_counts(self, counts):
        """Return ``counts`` as a 2D array of shape ``(n_hists, n_bins)``.

        ``nan``/``inf`` are replaced by zero and a 1D input is promoted to a
        single histogram. Raises ``ValueError`` if the number of bins does not
        match the edges, mirroring the project's clear-error style.
        """
        counts = np.nan_to_num(np.array(counts))
        while counts.ndim < 2:
            counts = counts[np.newaxis, ...]
        n_bins = len(self.edges) - 1
        if counts.shape[1] != n_bins:
            msg = (
                f"Bin counts have {counts.shape[1]} entries but the edges define "
                f"{n_bins} bins"
            )
            raise ValueError(msg)
        return counts

    def _scaled_edges(self):
        """Return ``self.edges`` divided by the common exponent."""
        common_exponent, _ = self._scale_string()
        return np.array(self.edges, dtype=float) / 10**common_exponent

    def _x_labels(self, width, centers, labels):
        """Return the bin-edge label row as a list of chars.

        Labels are placed greedily left-to-right, skipping any that would
        run into the previous one. The final (maximum) edge label is
        right-aligned to the bar area's right edge; if that position would
        collide with the previous label it is moved directly after it, and
        dropped altogether when even that does not fit.
        """
        row = [" "] * width
        last_end = 0
        for center, text in zip(centers[:-1], labels[:-1], strict=True):
            start = max(center - len(text) // 2, 0)
            if len(text) <= width:
                start = min(start, width - len(text))
            if start >= last_end + 1:  # leave at least one space between labels
                row[start : start + len(text)] = list(text)
                last_end = start + len(text)
        # Final (maximum) edge label: right-aligned if it fits, otherwise after
        # the previous label, otherwise skipped. Never overlaps another label.
        final = labels[-1]
        start = max(centers[-1] - len(final), 0)
        if start + len(final) > width:
            start = width - len(final)
        if start < last_end + 1:
            start = last_end + 1
            if start + len(final) > width:
                start = width - len(final)
        if (
            start >= last_end + 1
            and start + len(final) <= width
            and len(final) <= width
        ):
            row[start : start + len(final)] = list(final)
        return row

    def _format_histogram_vertical(self, counts):
        """Format (a set of) histogram counts as vertical bars.

        Each bin becomes a column of characters and the bar grows upwards from
        the baseline, i.e. the transpose of :meth:`format_histogram`. It is
        internal (no public ``format_histogram_vertical`` alias).
        """
        bf = self.bin_formatter
        counts = self._normalise_counts(counts)
        n_hists, n_bins = counts.shape

        # Left margin is used for the y-axis value labels
        left_width = bf.tick_format_width + len(bf.tick_mark)
        plot_width = max(self.columns - left_width, 1)
        plot_rows = max(self.hist_lines, 1)

        # Column width per bin, distributed proportionally to each bin's edge
        # width (largest-remainder method) so the bar area fills the available
        # width exactly. This mirrors the horizontal "lines per bin" scaling but
        # starts from the edge widths, which avoids overshooting when there are
        # few bins.
        edge_widths = np.diff(self.edges)
        if np.sum(edge_widths) <= 0:
            edge_widths = np.ones(n_bins)
        exact = edge_widths * (plot_width / np.sum(edge_widths))
        widths = np.maximum(1, np.floor(exact).astype(int))
        # Hand out any leftover columns to the widest-fractional bins so the
        # area fills exactly. If there are more bins than columns, ``widths``
        # is already at least one per bin and nothing is left to distribute.
        for idx in np.argsort(-np.modf(exact)[0])[
            : max(plot_width - int(np.sum(widths)), 0)
        ]:
            widths[idx] += 1
        # Never exceed the available width: with more bins than columns (or
        # many tiny bins) the sum of the widths naturally overshoots, so the
        # surplus columns are cut rather than extending past the plot. Only
        # the bins that are actually drawn set the vertical scale, so the
        # tallest visible bar still fills the plot area.
        total_w = min(int(np.sum(widths)), plot_width)
        starts = np.concatenate(([0], np.cumsum(widths)))
        visible = starts[:-1] < total_w

        # counts-per-character scale over the drawn bins, using density when
        # area represents counts
        max_c = self._counts_per_char(counts[:, visible], exact[visible])
        scale = (max_c / plot_rows) * 0.999  # <- avoid rounding issues

        # Composition is decided once (mirroring the horizontal code) and must
        # be set before the grid is built, because Hixel rendering reads it.
        compose = None
        for s in bf.symbols[:n_hists]:
            if s in COMPOSING_SYMBOLS:
                compose = " "
                break
        bf.compose = compose

        # Build a grid of Hixels, indexed [row][column], row 0 = top
        grid = [
            [
                Hixel(" ", compose=compose, use_color=bf.use_color)
                for _ in range(total_w)
            ]
            for _ in range(plot_rows)
        ]
        for ib in range(n_bins):
            cols = range(int(starts[ib]), min(int(starts[ib + 1]), total_w))
            cell_scale = scale * (exact[ib] if bf.count_area else 1)
            if cell_scale <= 0:
                continue
            heights = [int(c // cell_scale) for c in counts[:, ib]]
            base = 0  # running offset for stacked bins
            for ih in range(n_hists):
                h = heights[ih]
                # Stacked bins occupy a disjoint band [base, base+h); overlaid
                # bins all grow from the baseline, so only the top differs.
                top = min(base + h, plot_rows) if bf.stack else min(h, plot_rows)
                for r in range(base, top):
                    row = plot_rows - 1 - r
                    for col in cols:
                        grid[row][col].add(
                            bf.symbols[ih % len(bf.symbols)],
                            bf.fg_colors[ih % len(bf.fg_colors)],
                            bf.bg_colors[ih % len(bf.bg_colors)],
                        )
                base += h if bf.stack else 0

        # --- Assemble the output ---
        out = []
        if self.title:
            out.append(f"{self.title: ^{self.columns:d}s}\n")

        _, ce_string = self._scale_string()
        # Header: the count-per-column scale, right aligned so the line is
        # exactly self.columns wide (mirrors the horizontal header).
        longest_count = f"{max_c:g}/col" if bf.count_area else f"{max_c:g}"
        pad = self.columns - left_width - len(ce_string) - len(longest_count)
        out.append(
            " " * left_width + ce_string + f"{longest_count:>{max(pad, 0):d}s}\n"
        )

        # Bar rows with a y-axis tick on the left gutter
        gutter = " " * left_width
        for i, row in enumerate(grid):
            if i == 0:
                tick = self._y_tick(max_c, left_width)
            elif i == plot_rows - 1:
                tick = self._y_tick(0.0, left_width)
            else:
                tick = " " * left_width
            out.append(tick + "".join(h.render() for h in row) + "\n")

        # Baseline: corner at the bar-area left edge, dashes filling the rest.
        # Kept to exactly self.columns wide so it matches the bar rows.
        out.append(
            gutter + "\u2514" + "\u2500" * (self.columns - left_width - 1) + "\n"
        )

        # Bin-edge labels underneath the baseline. A compact 3-significant-
        # figure format is used because full ``tick_format`` values (8 chars)
        # are far wider than the per-bin column spacing and would never fit.
        edges = self._scaled_edges()
        labels = [f"{e:.3g}" for e in edges]
        bar0 = left_width  # label row index of bar column 0
        centers = [
            bar0 + (int(starts[ib]) if ib < n_bins else total_w - 1)
            for ib in range(n_bins + 1)
        ]
        label_row = self._x_labels(self.columns, centers, labels)
        out.append("".join(label_row).rstrip() + "\n")

        if self.summary or any(len(lab) > 0 for lab in self.labels):
            # Scale edges by the common exponent (as the horizontal path does)
            # so the summary statistics are orientation-independent.
            scaled = self._scaled_edges()
            out.append(
                self.summarize(
                    counts, scaled[:-1], scaled[1:], legend_only=not self.summary
                )
            )

        return "".join(out)

    def _counts_per_char(self, counts, exact_widths):
        """Return the count reference the vertical axis is scaled against.

        When stacking, this is the per-bin sum; otherwise the per-bin maximum.
        When ``count_area`` is set, the per-bin value is a density (counts per
        column) using the exact (non-rounded) bin widths. ``self.max_count``
        overrides the data-driven maximum.
        """
        bf = self.bin_formatter
        tot_c = np.sum(counts, axis=0) if bf.stack else np.max(counts, axis=0)
        denom = exact_widths if bf.count_area else 1
        max_c = (
            float(np.max(tot_c / denom)) if self.max_count is None else self.max_count
        )
        if max_c == 0:
            max_c = 1.0
        return max_c

    def _y_tick(self, value, width):
        """Right-align a y-axis count value in ``width`` characters.

        Zero is rendered as a plain gutter (spaces) so the baseline row stays
        uncluttered.
        """
        if not value:
            return " " * width
        text = f"{value:.3g}"
        return f"{text:>{width - 1:d}s} "

    def summarize(self, counts, top, bottom, legend_only=False):
        """Calculate some summary statistics."""

        bin_values = (top + bottom) / 2

        label_widths = []

        # First line: symbol, label
        first_line = ["     "]
        for _, lab, s, fg, bg in zip(
            counts,
            cycle(self.labels),
            cycle(self.bin_formatter.symbols),
            cycle(self.bin_formatter.fg_colors),
            cycle(self.bin_formatter.bg_colors),
        ):
            # Pad label to make room for numbers below
            pad_lab = f"{lab:<9}"
            hixel = Hixel(
                s, fg, bg, self.bin_formatter.use_color, self.bin_formatter.compose
            ).render()
            first_line.append(f" {hixel} {pad_lab}")
            label_widths.append(3 + len(pad_lab))
        pad = max(self.columns - (5 + np.sum(label_widths)), 0) // 2

        summary = [" " * pad, *first_line, "\n"]

        if legend_only:
            return "".join(summary)

        # Second line: Total
        summary.append(" " * pad + "Tot:")
        for c, w in zip(counts, label_widths, strict=True):
            tot = float(np.sum(c))
            summary.append(f" {tot: .2e}" + " " * (w - 10))
        summary.append("\n")

        # Third line: Average
        summary.append(" " * pad + "Avg:")
        for c, w in zip(counts, label_widths, strict=True):
            try:
                average = float(np.average(bin_values, weights=c))
            except ZeroDivisionError:
                average = np.nan
            summary.append(f" {average: .2e}" + " " * (w - 10))
        summary.append("\n")

        # Fourth line: std
        summary.append(" " * pad + "Std:")
        for c, w in zip(counts, label_widths, strict=True):
            try:
                average = float(np.average(bin_values, weights=c))
                std = np.sqrt(np.average((bin_values - average) ** 2, weights=c))
            except ZeroDivisionError:
                std = np.nan
            summary.append(f" {std: .2e}" + " " * (w - 10))
        summary.append("\n")

        return "".join(summary)


def get_plottable_protocol_bin_edges(axis):
    """Get histogram bin edges from PlottableAxis.

    Borrowed from ``mplhep.utils``.

    """

    out = np.empty(len(axis) + 1)
    if not isinstance(axis[0], tuple):
        msg = f"Currently only support non-discrete axes {axis}"
        raise TypeError(msg)
    # TODO: Support discreete axes
    out[0] = axis[0][0]
    out[1:] = [axis[i][1] for i in range(len(axis))]
    return out


def get_count_edges(hist):
    """Get bin contents and edges from a compatible histogram."""

    # Support sequence of histograms
    if isinstance(hist, Sequence) and len(hist) == 0:
        msg = "Cannot plot an empty sequence of histograms"
        raise ValueError(msg)

    if isinstance(hist, Sequence) and isinstance(hist[0], PlottableHistogram):
        count = np.stack([h.values() for h in hist])
        edges = get_plottable_protocol_bin_edges(hist[0].axes[0])
        for other_edges in (
            get_plottable_protocol_bin_edges(h.axes[0]) for h in hist[1:]
        ):
            if not np.allclose(edges, other_edges):
                msg = "All histograms must share the same bin edges"
                raise ValueError(msg)

    else:
        # Single histogram or (a,b,c, edges) tuple:
        # Make sure we have a PlottableProtocol histogram
        hist = ensure_plottable_histogram(hist)

        # Use the PlottableProtocol
        count = hist.values()
        edges = get_plottable_protocol_bin_edges(hist.axes[0])

    return count, edges


def print_hist(hist, file=None, **kwargs):
    """Plot the output of ``numpy.histogram`` to the console.

    Parameters
    ----------

    file : optional
        File like object to print to.
    **kwargs :
        Additional keyword arguments are passed to the `HistFormatter`.

    """
    if file is None:
        file = sys.stdout
    count, edges = get_count_edges(hist)
    hist_formatter = HistFormatter(edges, **kwargs)
    file.write(hist_formatter.format_histogram(count))
    file.flush()


def text_hist(*args, density=None, **kwargs):
    """Thin wrapper around ``numpy.histogram``."""

    print_kwargs = {
        "file": kwargs.pop("file", sys.stdout),
        "title": kwargs.pop("title", ""),
        "stack": kwargs.pop("stack", False),
        "symbols": kwargs.pop("symbols", DEFAULT_SYMBOLS),
        "fg_colors": kwargs.pop("fg_colors", DEFAULT_FG_COLORS),
        "bg_colors": kwargs.pop("bg_colors", DEFAULT_BG_COLORS),
        "count_area": kwargs.pop("count_area", True),
        "orientation": kwargs.pop("orientation", "horizontal"),
    }
    if density:
        print_kwargs["count_area"] = False
    kwargs["density"] = density
    hist = np.histogram(*args, **kwargs)
    print_hist(hist, **print_kwargs)
    return hist
