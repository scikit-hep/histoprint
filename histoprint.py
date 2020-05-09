"""Simple function to plot the output of ``numpy.histogram`` to the console"""

from __future__ import division
from six import print_

import sys
import numpy as np


class Hixel(object):
    """The smallest unit of a histogram plot."""

    def __init__(self, char=" ", fg="0", bg="0", use_color=True):
        self.character = char
        self.fg_color = fg
        self.bg_color = bg
        self.use_color = use_color

    def add(self, char=" ", fg="0", bg="0"):
        """Add another element on top."""

        if char != " " and fg == self.fg_color:
            # Combine characters if possible
            self.character = self.overlay_characters(self.character, char)
        else:
            self.character = char
            self.fg_color = fg

        if bg != "0":
            self.bg_color = bg

    def render(self, reset=True):
        """Render the Hixel as a string."""
        ret = ""
        if self.character == " " and self.bg_color != "0":
            # Instead of printing a space with BG color,
            # print a full block with same FG color,
            # so the histogram can be copied to text editors.
            ret += self.ansi_color_string(self.bg_color, self.bg_color)
            ret += u"\u2588"
        else:
            ret += self.ansi_color_string(self.fg_color, self.bg_color)
            ret += self.substitute_character(self.character)
        if reset:
            ret += self.ansi_color_string("0", "0")
        return ret

    @staticmethod
    def substitute_character(char):
        r"""Replace some ASCII characters with better looking Unicode.

        Substitutions::

            "-" -> "\u2500"
            "|" -> "\u2502"
            "=" -> "\u2550"
            "+" -> "\u253C"
            "#" -> "\u256A"

        """

        subs = {
            "-": u"\u2500",
            "|": u"\u2502",
            "=": u"\u2550",
            "+": u"\u253C",
            "#": u"\u256A",
        }

        return subs.get(char, char)

    @staticmethod
    def overlay_characters(char1, char2):
        r"""Combine character to give the impression of drawing them both.

        Possible combinations::

            "-" + "|" -> "+"
            "=" + "|" -> "#"
            "/" + "\" -> "X"

        """

        subs = {
            ("-", "|"): "+",
            ("=", "|"): "#",
            ("/", "\\"): "X",
        }
        return subs.get((char1, char2), subs.get((char2, char1), char2))

    def ansi_color_string(self, fg, bg):
        """Set the terminal color."""
        ret = ""
        if self.use_color:
            fg = int(fg, 16) + 30
            bg = int(bg, 16) + 40
            if fg > 37:
                fg += 52
            if bg > 47:
                bg += 52
            if fg == 30:
                ret += "\033[%dm" % (39,)
            else:
                ret += "\033[%dm" % (fg,)
            if bg == 40:
                ret += "\033[%dm" % (49,)
            else:
                ret += "\033[%dm" % (bg,)
        return ret


class BinFormatter(object):
    """Class that turns bin contents into text.

    Arguments
    ---------

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
    colors : iterable
        The foreground colors (single digit hex value) to be used.
        A value of 0 means the default terminal color.
    bg_colors : iterable
        The background colors (single digit hex value) to be used.
        A value of 0 means "transparent".
    stack : bool
        Whether to stack the histograms, or overlay them.
    use_color : bool
        Whether to use color output.

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
        symbols=" |=",
        colors="000",
        bg_colors="300",
        stack=False,
        use_color=True,
    ):
        self.scale = scale
        self.count_area = count_area
        self.tick_format = tick_format
        self.tick_format_width = tick_format_width
        self.tick_mark = tick_mark
        self.no_tick_mark = no_tick_mark
        self.print_top_edge = print_top_edge
        self.symbols = symbols
        self.colors = colors
        self.bg_colors = bg_colors
        self.stack = stack
        self.use_color = use_color

    def format_bin(self, top, bottom, counts, width=1):
        """Return a string that represents the bin.

        Arguments
        ---------

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
            for h, s, c, bg in zip(heights, self.symbols, self.colors, self.bg_colors):
                if h:
                    if self.stack:
                        # Just print them all afer one another
                        line += [Hixel(s, c, bg, self.use_color) for _ in range(h)]
                    else:
                        # Overlay histograms
                        if h > len(line):
                            for hix in line:
                                hix.add(s, c, bg)
                            line += [
                                Hixel(s, c, bg, self.use_color)
                                for _ in range(h - len(line))
                            ]
                        else:
                            for hix in line[:h]:
                                hix.add(s, c, bg)

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

    Arguments
    ---------

    lines, columns : int
        The number of lines and maximum numbre of columns of the output.
    count_area : bool
        Whether the bin content is represented by the area or height of the bin.
    scale_bin_width : bool
        Whether the lines per bin should scale with the bin width.
    title : str
        Title string to print over the histogram.
    stack : bool
        Whether to stack or overlay the histograms.

    """

    def __init__(
        self,
        edges,
        lines=23,
        columns=79,
        count_area=True,
        scale_bin_width=True,
        title="",
        stack=False,
    ):
        self.title = title
        self.edges = edges
        self.lines = lines
        self.columns = columns
        self.hist_lines = lines - 2
        if scale_bin_width:
            # Try to scale bins so the number of lines is
            # roughly proportional to the bin width
            line_scale = ((edges[-1] - edges[0]) / self.hist_lines) * 0.999
        else:
            # Choose the larges bin as scale,
            # so all bins will scale to <= 1 lines
            # and be rendered with one line
            line_scale = np.max(edges[1:] - edges[:-1])
        self.bin_lines = ((edges[1:] - edges[:-1]) // line_scale).astype(int)
        self.bin_lines = np.where(self.bin_lines, self.bin_lines, 1)
        self.bin_formatter = BinFormatter(stack=stack, count_area=count_area)

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

        if self.bin_formatter.stack:
            # Bin content will be sum of all histograms
            c = np.sum(counts, axis=0)
        else:
            # Bin content will be maximum of all histograms
            c = np.max(counts, axis=0)
        if self.bin_formatter.count_area:
            # Bin content will be divided by number of lines
            c = c / self.bin_lines

        # Set a scale so that largest bin wills width of allocated area
        symbol_scale = np.max(c) / hist_width
        self.bin_formatter.scale = symbol_scale

        # Write the title line
        hist_string = ("{:^%ds}\n" % (self.columns,)).format(self.title)

        top = self.edges[:-1]
        bottom = self.edges[1:]

        # Write the first tick
        hist_string += self.bin_formatter.tick(top[0]) + "\n"

        # Write the bins
        for c, t, b, w in zip(counts.T, top, bottom, self.bin_lines):
            hist_string += self.bin_formatter.format_bin(t, b, c, w)

        return hist_string


def print_hist(hist, file=sys.stdout, title="", stack=False, count_area=True):
    """plot the output of ``numpy.histogram`` to the console."""

    count, edges = hist
    hist_formatter = HistFormatter(
        edges, title=title, stack=stack, count_area=count_area
    )
    print_(hist_formatter.format_histogram(count), end="", file=file)


def text_hist(*args, **kwargs):
    """Thin wrapper around ``numpy.histogram``."""

    file = kwargs.pop("file", sys.stdout)
    title = kwargs.pop("title", "")
    stack = kwargs.pop("stack", False)
    count_area = kwargs.pop("count_area", True)
    density = kwargs.pop("density", False)
    if density:
        count_area = False
    hist = np.histogram(*args, density=density, **kwargs)
    print_hist(hist, file=file, title=title, stack=stack, count_area=count_area)
    return hist


def test_hist():
    """Poor man's unit tests."""

    A = np.random.randn(1000) - 2
    B = np.random.randn(1000)
    C = np.random.randn(1000) + 2

    text_hist(A, bins=10, title="10 bins")
    text_hist(A, bins=20, title="20 bins")
    text_hist(A, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5], title="Variable bins")

    histA = np.histogram(A, bins=20, range=(-5, 5))
    histB = np.histogram(B, bins=20, range=(-5, 5))
    histC = np.histogram(C, bins=20, range=(-5, 5))
    histAll = ([histA[0], histB[0], histC[0]], histA[1])

    print_hist(histAll, title="Overlays")
    print_hist(histAll, title="Stack", stack=True)


if __name__ == "__main__":
    test_hist()
