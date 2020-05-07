"""Simple function to plot the output of ``numpy.histogram`` to the console"""

from __future__ import division
from six import print_

import sys
import numpy as np


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
        symbols="#XO",
    ):
        self.scale = scale
        self.count_area = count_area
        self.tick_format = tick_format
        self.tick_format_width = tick_format_width
        self.tick_mark = tick_mark
        self.no_tick_mark = no_tick_mark
        self.print_top_edge = print_top_edge
        self.symbols = symbols

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
            for h, s in zip(heights, self.symbols):
                bin_string += s * h

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

    """

    def __init__(
        self, edges, lines=20, columns=79, count_area=True, scale_bin_width=True
    ):
        self.edges = edges
        self.lines = lines
        self.columns = columns
        self.hist_lines = lines
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
        self.bin_formatter = BinFormatter()

    def format_histogram(self, counts):
        """Format (a set of) histogram counts."""

        axis_width = self.bin_formatter.tick_format_width + len(
            self.bin_formatter.tick_mark
        )
        hist_width = self.columns - axis_width

        counts = np.array(counts)
        c = np.sum(counts, axis=0) / self.bin_lines
        symbol_scale = np.max(c) / hist_width
        self.bin_formatter.scale = symbol_scale

        hist_string = ""
        top = self.edges[:-1]
        bottom = self.edges[1:]

        for c, t, b, w in zip(counts.T, top, bottom, self.bin_lines):
            hist_string += self.bin_formatter.format_bin(t, b, c, w)

        return hist_string


def print_hist(hist, file=sys.stdout):
    """plot the output of ``numpy.histogram`` to the console."""

    count, edges = hist
    hist_formatter = HistFormatter(edges)
    print_(hist_formatter.format_histogram([count]), end="", file=file)


def text_hist(*args, **kwargs):
    """Thin wrapper around ``numpy.histogram``."""

    hist = np.histogram(*args, **kwargs)
    print_hist(hist)
    return hist


def test_hist():
    """Poor man's unit tests."""

    A = np.random.randn(1000)
    B = np.random.randn(1000) + 2

    print_("")
    text_hist(A, bins=10)
    print_("")
    text_hist(A, bins=15)
    print_("")
    text_hist(A, bins=20)
    print_("")
    text_hist(A, bins=21)
    print_("")
    text_hist(A, bins=[-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3])
    print_("")
    text_hist(A, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5])


if __name__ == "__main__":
    test_hist()
