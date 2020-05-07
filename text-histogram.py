"""Simple function to plot the output of ``numpy.histogram`` to the console"""

from __future__ import division

import sys
import numpy as np

class BinFormater(object):
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

    def __init__(self, scale=1., count_area=True, tick_format='% .2e ', tick_format_width=10, tick_mark='_', no_tick_mark=' ', print_top_edge=False, symbols="#XO"):
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
                bin_string += s*h

            # New line
            bin_string += '\n'

        return bin_string

    def tick(self, edge):
        """Format the tick mark of a bin."""
        return self.tick_format%(edge,) + self.tick_mark

    def no_tick(self):
        """Format the axis without a tick mark."""
        return ' '*self.tick_format_width + self.no_tick_mark

def print_hist(hist, file=sys.stdout):
    """plot the output of ``numpy.histogram`` to the console."""

    counts, edges = hist
    left = np.array(edges[:-1])
    right = np.array(edges[1:])
    width = right-left
    max_count = np.max(counts)
    scale = max_count / 68

    bin_formater = BinFormater(scale=scale)

    for c, l, r in zip(counts, left, right):
        print(bin_formater.format_bin(l,r,[c]), end='', file=file)

def text_hist(*args, **kwargs):
    """Thin wrapper around ``numpy.histogram``."""

    hist = np.histogram(*args, **kwargs)
    print_hist(hist)
    return hist

def test_hist():
    """Poor man's unit tests."""

    A = np.random.randn(1000)
    B = np.random.randn(1000) + 2

    print('')
    text_hist(A)
    print('')
    text_hist(B)

if __name__ == '__main__':
    test_hist()
