"""Module for plotting Numpy-like 1D histograms to the terminal."""

import shutil
import sys
from collections.abc import Sequence
from itertools import cycle
from typing import Optional

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
        self.compose: Optional[str] = compose
        self.fg_color = fg
        self.bg_color = bg
        self.use_color = use_color
        self.add(char, fg, bg)

    def add(self, char=" ", fg="0", bg="0"):
        """Add another element on top."""

        allowed = r" =|\/"
        if char not in allowed:
            msg = f"Symbol not one of the allowed: '{allowed!r}'"
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
            }
            if char in compose_chars:
                if self.compose is not None:
                    self.compose = compose_combinations.get((self.compose, char))
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
        # Unless explicitly asked for no compositio, if no composition is added,
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
        self.symbols = symbols
        if self.symbols == "":
            self.symbols = " "
        self.fg_colors = fg_colors
        if self.fg_colors == "":
            self.fg_colors = "0"
        self.bg_colors = bg_colors
        if self.bg_colors == "":
            self.bg_colors = "0"
        self.stack = stack
        if use_color is None:
            if any(c != "0" for c in fg_colors) or any(c != "0" for c in bg_colors):
                self.use_color = True
            else:
                self.use_color = False
        else:
            self.use_color = use_color
        self.compose: Optional[str] = None

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
        bin_string = ""
        for i_line in range(width):
            # Print axis
            if self.print_top_edge and i_line == 0:
                bin_string += self.tick(top)
            elif not self.print_top_edge and i_line == (width - 1):
                bin_string += self.tick(bottom)
            else:
                bin_string += self.no_tick()

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
                        # Just print them all afer one another
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
                bin_string += hix.render()

            # New line
            bin_string += "\n"

        return bin_string

    def tick(self, edge):
        """Format the tick mark of a bin."""
        return self.tick_format.format(edge) + self.tick_mark

    def no_tick(self):
        """Format the axis without a tick mark."""
        return " " * self.tick_format_width + self.no_tick_mark


class HistFormatter:
    """Class that handles the formating of histograms.

    Parameters
    ----------

    lines, columns : int, optional
        The number of lines and maximum numbre of columns of the output.
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
        **kwargs,
    ):
        self.title = title
        self.edges = edges
        # Fit histograms into the terminal, unless otherwise specified
        term_size = shutil.get_terminal_size()
        if columns is None:
            columns = term_size[0] - 1
        if lines is None:
            # Try to keep a constant aspect ratio
            lines = min(int(columns / 3.5) + 1, term_size[1] - 1)
        self.lines = lines
        self.columns = columns
        self.summary = summary
        self.labels = labels
        self.max_count = max_count

        self.hist_lines = lines - 1  # Less one line for the first tick
        if len(self.title):
            # Make room for the title
            self.hist_lines -= 1

        self.summary = summary
        if self.summary:
            # Make room for a summary at the bottom
            self.hist_lines -= 4
        elif any(len(lab) > 0 for lab in self.labels):
            # Make room for a legend at the bottom
            self.hist_lines -= 1

        if scale_bin_width:
            # Try to scale bins so the number of lines is
            # roughly proportional to the bin width
            line_scale = (
                (edges[-1] - edges[0]) / self.hist_lines
            ) * 0.999  # <- avoid rounding issues
        else:
            # Choose the largest bin as scale,
            # so all bins will scale to <= 1 lines
            # and be rendered with one line
            line_scale = np.max(edges[1:] - edges[:-1])
        if line_scale == 0.0:
            line_scale = 1.0
        self.bin_lines = ((edges[1:] - edges[:-1]) // line_scale).astype(int)
        self.bin_lines = np.where(self.bin_lines, self.bin_lines, 1)
        self.bin_formatter = BinFormatter(**kwargs)

    def format_histogram(self, counts):
        """Format (a set of) histogram counts.

        Paramters
        ---------

        counts : ndarray
            The histogram entries to be plotted.

        """

        axis_width = self.bin_formatter.tick_format_width + len(
            self.bin_formatter.tick_mark
        )
        hist_width = self.columns - axis_width

        counts = np.nan_to_num(np.array(counts))
        while counts.ndim < 2:
            # Make sure counts is a 2D array
            counts = counts[np.newaxis, ...]

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

        hist_string = ""

        # Write the title line
        if len(self.title):
            hist_string += f"{self.title: ^{self.columns:d}s}\n"

        # Get bin edges
        top = np.array(self.edges[:-1])
        bottom = np.array(self.edges[1:])
        # Caclucate common exponent
        common_exponent = np.floor(np.log10(np.max(np.abs(self.edges))))
        top /= 10**common_exponent
        bottom /= 10**common_exponent

        # Write the first tick, common exponent and horizontal axis
        hist_string += self.bin_formatter.tick(top[0])
        ce_string = f" x 10^{common_exponent:+03.0f}" if common_exponent != 0 else ""

        hist_string += ce_string
        if self.bin_formatter.count_area:
            longest_count = f"{max_c:g}/row"
        else:
            longest_count = f"{max_c:g}"
        hist_string += f"{longest_count:>{hist_width - len(ce_string) - 2:d}s} \u2577\n"

        # Write the bins
        for c, t, b, w in zip(counts.T, top, bottom, self.bin_lines):
            hist_string += self.bin_formatter.format_bin(t, b, c, w)

        if self.summary:
            hist_string += self.summarize(counts, top, bottom)
        elif any(len(lab) > 0 for lab in self.labels):
            hist_string += self.summarize(counts, top, bottom, legend_only=True)

        return hist_string

    def summarize(self, counts, top, bottom, legend_only=False):
        """Calculate some summary statistics."""

        summary = ""
        bin_values = (top + bottom) / 2

        label_widths = []

        # First line: symbol, label
        summary += "     "
        for _, lab, s, fg, bg in zip(
            counts,
            cycle(self.labels),
            cycle(self.bin_formatter.symbols),
            cycle(self.bin_formatter.fg_colors),
            cycle(self.bin_formatter.bg_colors),
        ):
            # Pad label to make room for numbers below
            pad_lab = f"{lab:<9}"
            label = " "
            label += Hixel(
                s, fg, bg, self.bin_formatter.use_color, self.bin_formatter.compose
            ).render()
            label += " " + pad_lab
            label_widths.append(3 + len(pad_lab))
            summary += label
        pad = max(self.columns - (5 + np.sum(label_widths)), 0) // 2
        summary = " " * pad + summary
        summary += "\n"

        if legend_only:
            return summary

        # Second line: Total
        summary += " " * pad + "Tot:"
        for c, w in zip(counts, label_widths):
            tot = float(np.sum(c))
            summary += f" {tot: .2e}" + " " * (w - 10)
        summary += "\n"

        # Third line: Average
        summary += " " * pad + "Avg:"
        for c, w in zip(counts, label_widths):
            try:
                average = float(np.average(bin_values, weights=c))
            except ZeroDivisionError:
                average = np.nan
            summary += f" {average: .2e}" + " " * (w - 10)
        summary += "\n"

        # Fourth line: std
        summary += " " * pad + "Std:"
        for c, w in zip(counts, label_widths):
            try:
                average = float(np.average(bin_values, weights=c))
                std = np.sqrt(np.average((bin_values - average) ** 2, weights=c))
            except ZeroDivisionError:
                std = np.nan
            summary += f" {std: .2e}" + " " * (w - 10)
        summary += "\n"

        return summary


def get_plottable_protocol_bin_edges(axis):
    """Get histogram bin edges from PlottableAxis.

    Borrowed from ``mplhep.utils``.

    """

    out = np.empty(len(axis) + 1)
    assert isinstance(
        axis[0], tuple
    ), f"Currently only support non-discrete axes {axis}"
    # TODO: Support discreete axes
    out[0] = axis[0][0]
    out[1:] = [axis[i][1] for i in range(len(axis))]
    return out


def get_count_edges(hist):
    """Get bin contents and edges from a compatible histogram."""

    # Support sequence of histograms
    if isinstance(hist, Sequence) and isinstance(hist[0], PlottableHistogram):
        count = np.stack([h.values() for h in hist])
        edges = get_plottable_protocol_bin_edges(hist[0].axes[0])
        for other_edges in (
            get_plottable_protocol_bin_edges(h.axes[0]) for h in hist[1:]
        ):
            np.testing.assert_allclose(edges, other_edges)

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
    }
    if density:
        print_kwargs["count_area"] = False
    kwargs["density"] = density
    hist = np.histogram(*args, **kwargs)
    print_hist(hist, **print_kwargs)
    return hist
