"""Module for plotting Numpy-like 1D histograms to the terminal."""

from __future__ import division
from itertools import cycle

import sys
import numpy as np
import click

DEFAULT_SYMBOLS = " |=/\\"
COMPOSING_SYMBOLS = "/\\"
DEFAULT_FG_COLORS = "WWWWW"
DEFAULT_BG_COLORS = "K0000"

__all__ = ["print_hist", "text_hist", "HistFormatter"]


class Hixel(object):
    """The smallest unit of a histogram plot."""

    def __init__(self, char=" ", fg="0", bg="0", use_color=True, compose=" "):
        self.character = " "
        self.compose = compose
        self.fg_color = fg
        self.bg_color = bg
        self.use_color = use_color
        self.add(char, fg, bg)

    def add(self, char=" ", fg="0", bg="0"):
        """Add another element on top."""

        allowed = " =|\/"
        if char not in allowed:
            raise ValueError("Symbol not one of the allowed: '%s'" % (allowed,))

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
            ret += u"\u2588"
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
            "|": u"\u2502",
            "=": u"\u2550",
            "#": u"\u256A",
            "\\": u"\u20e5",
            "/": u"\u20eb",
            "X": u"\u20e5\u20eb",
            None: u"",
        }

        ret = subs.get(char, char)
        # Characters can be displayed differently when they have a composing character on top.
        # This looks ugly if some Hixels of a histogram are covered by another and some are not.
        # Unless explicitly asked for no compositio, if no composition is added,
        # use empty composition character to make them all display the same.
        ret += subs.get(compose, u"\u034f")

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

            ret += "\033[%d;%dm" % (fg, bg)
        return ret


class BinFormatter(object):
    """Class that turns bin contents into text.

    Parameters
    ----------

    scale : float
        The scale of the histogram, i.e. one text character corresponds to
        `scale` counts.
    count_area : bool
        Whether the bin content is represented by the area or height of the bin.
    tick_format : st
        The format string for tick values.
    tick_format_width : int
        Width of the evaluated tick format.
    tick_mark : str
        Character of the tick mark.
    no_tick_mark : str
        Character to be printed for axis without tick.
    print_top_edge : bool
        Whether to print the top or bottom edge of the bin.
    symbols : iterable
        The foreground symbols to be used for the histograms.
    fg_colors : iterable
        The foreground colours to be used.
    bg_colors : iterable
        The background colours to be used.
    stack : bool
        Whether to stack the histograms, or overlay them.
    use_color : bool
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
        tick_format="% .2e ",
        tick_format_width=10,
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
        self.tick_format_width = tick_format_width
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
        if self.count_area:
            scale = self.scale * width
        else:
            scale = self.scale

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
                    else:
                        # Overlay histograms
                        if h > len(line):
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
        return self.tick_format % (edge,) + self.tick_mark

    def no_tick(self):
        """Format the axis without a tick mark."""
        return " " * self.tick_format_width + self.no_tick_mark


class HistFormatter(object):
    """Class that handles the formating of histograms.

    Parameters
    ----------

    lines, columns : int
        The number of lines and maximum numbre of columns of the output.
    count_area : bool
        Whether the bin content is represented by the area or height of the bin.
    scale_bin_width : bool
        Whether the lines per bin should scale with the bin width.
    title : str
        Title string to print over the histogram.
    summary : bool
        Whether to print a summary of the histograms.
    labels : iterable
        Labels the histograms.
    **kwargs :
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
        labels=[""],
        summary=False,
        **kwargs
    ):
        self.title = title
        self.edges = edges
        # Fit histograms into the terminal, unless otherwise specified
        term_size = click.get_terminal_size()
        if columns is None:
            columns = term_size[0] - 1
        if lines is None:
            # Try to keep a constant aspect ratio
            lines = min(int(columns / 3.5) + 1, term_size[1] - 1)
        self.lines = lines
        self.columns = columns
        self.summary = summary
        self.labels = labels

        self.hist_lines = lines - 1  # Less one line for the first tick
        if len(self.title):
            # Make room for the title
            self.hist_lines -= 1

        self.summary = summary
        if self.summary:
            # Make room for a summary at the bottom
            self.hist_lines -= 4
        elif any([len(l) > 0 for l in self.labels]):
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
        self.bin_lines = ((edges[1:] - edges[:-1]) // line_scale).astype(int)
        self.bin_lines = np.where(self.bin_lines, self.bin_lines, 1)
        self.bin_formatter = BinFormatter(**kwargs)

    def format_histogram(self, counts):
        """Format (a set of) histogram counts."""

        axis_width = self.bin_formatter.tick_format_width + len(
            self.bin_formatter.tick_mark
        )
        hist_width = self.columns - axis_width

        counts = np.array(counts)
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
        if self.bin_formatter.count_area:
            # Bin content will be divided by number of lines
            c = tot_c / self.bin_lines
        else:
            c = tot_c

        # Set a scale so that largest bin fills width of allocated area
        symbol_scale = np.max(c) / hist_width
        self.bin_formatter.scale = symbol_scale * 0.999  # <- avoid rounding issues

        hist_string = ""

        # Write the title line
        if len(self.title):
            hist_string += ("{: ^%ds}\n" % (self.columns,)).format(self.title)

        top = self.edges[:-1]
        bottom = self.edges[1:]

        # Write the first tick and horizontal axis
        hist_string += self.bin_formatter.tick(top[0])
        longest_count = tot_c[np.argmax(c)]
        if np.issubdtype(longest_count.dtype, np.integer):
            hist_string += (u"{: %dd} \u2577\n" % (hist_width - 2,)).format(
                longest_count
            )
        else:
            # Pad with spaces
            hist_string += " " * (hist_width - axis_width)
            # The tick value
            hist_string += self.bin_formatter.tick_format % (longest_count,)
            # The tick
            hist_string += u"\u2577\n"

        # Write the bins
        for c, t, b, w in zip(counts.T, top, bottom, self.bin_lines):
            hist_string += self.bin_formatter.format_bin(t, b, c, w)

        if self.summary:
            hist_string += self.summarize(counts, top, bottom)
        elif any([len(l) > 0 for l in self.labels]):
            hist_string += self.summarize(counts, top, bottom, legend_only=True)

        return hist_string

    def summarize(self, counts, top, bottom, legend_only=False):
        """Calculate some summary statistics."""

        summary = ""
        bin_values = (top + bottom) / 2

        label_widths = []

        # First line: symbol, label
        summary += "     "
        for c, l, s, fg, bg in zip(
            counts,
            cycle(self.labels),
            cycle(self.bin_formatter.symbols),
            cycle(self.bin_formatter.fg_colors),
            cycle(self.bin_formatter.bg_colors),
        ):
            # Pad label to make room for numbers below
            l = "%-9s" % (l,)
            label = " "
            label += Hixel(
                s, fg, bg, self.bin_formatter.use_color, self.bin_formatter.compose
            ).render()
            label += " " + l
            label_widths.append(3 + len(l))
            summary += label
        pad = max(self.columns - (5 + np.sum(label_widths)), 0) // 2
        summary = " " * pad + summary
        summary += "\n"

        if legend_only:
            return summary

        # Second line: Total
        summary += " " * pad + "Tot:"
        for c, w in zip(counts, label_widths):
            tot = np.sum(c)
            summary += " % .2e" % (tot,) + " " * (w - 10)
        summary += "\n"

        # Third line: Average
        summary += " " * pad + "Avg:"
        for c, w in zip(counts, label_widths):
            average = np.average(bin_values, weights=c)
            summary += " % .2e" % (average,) + " " * (w - 10)
        summary += "\n"

        # Fourth line: std
        summary += " " * pad + "Std:"
        for c, w in zip(counts, label_widths):
            average = np.average(bin_values, weights=c)
            std = np.sqrt(np.average((bin_values - average) ** 2, weights=c))
            summary += " % .2e" % (std,) + " " * (w - 10)
        summary += "\n"

        return summary


def get_count_edges(hist):
    """Get bin contents and edges from a compatible histogram."""

    # Try the boost-histogram interface
    try:
        hist = hist.to_numpy()
    except:
        pass

    # Try the uproot interface
    try:
        hist = hist.numpy()
    except:
        pass

    # Try the Numpy interface
    try:
        count, edges = hist
    except ValueError:
        raise ValueError("Not a compatible histogram!")

    return count, edges


def print_hist(hist, file=click.get_text_stream("stdout"), **kwargs):
    """Plot the output of ``numpy.histogram`` to the console.

    Parameters
    ----------

    file : optional
        File like object to print to.
    **kwargs :
        Additional keyword arguments are passed to the `HistFormatter`.

    """

    count, edges = get_count_edges(hist)
    hist_formatter = HistFormatter(edges, **kwargs)
    click.echo(hist_formatter.format_histogram(count), nl=False, file=file)


def text_hist(*args, **kwargs):
    """Thin wrapper around ``numpy.histogram``."""

    print_kwargs = {
        "file": kwargs.pop("file", click.get_text_stream("stdout")),
        "title": kwargs.pop("title", ""),
        "stack": kwargs.pop("stack", False),
        "symbols": kwargs.pop("symbols", DEFAULT_SYMBOLS),
        "fg_colors": kwargs.pop("fg_colors", DEFAULT_FG_COLORS),
        "bg_colors": kwargs.pop("bg_colors", DEFAULT_BG_COLORS),
        "count_area": kwargs.pop("count_area", True),
    }
    density = kwargs.pop("density", False)
    if density:
        print_kwargs["count_area"] = False
    hist = np.histogram(*args, density=density, **kwargs)
    print_hist(hist, **print_kwargs)
    return hist
