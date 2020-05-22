"""Module containing the CLI programs for histoprint."""

import numpy as np
import click
from histoprint import *
import histoprint.formatter as formatter


@click.command()
@click.argument("infile", type=click.File("rt"))
@click.option(
    "-b",
    "--bins",
    type=str,
    default="10",
    help="Number of bins or space-separated bin edges.",
)
@click.option("-t", "--title", type=str, default="", help="Title of the histogram.")
@click.option(
    "--stack/--nostack", type=bool, default=False, help="Stack the histograms."
)
@click.option(
    "-s/-S",
    "--summary/--nosummary",
    type=bool,
    default=False,
    help="Print summary statistics.",
)
@click.option(
    "-l",
    "--label",
    "labels",
    type=str,
    multiple=True,
    default=("",),
    help="Labels for the data, one for each column.",
)
@click.option(
    "--symbols",
    type=str,
    default=formatter.DEFAULT_SYMBOLS,
    help="Symbol cycle for multiple histograms. Choices & default: '%s'"
    % (formatter.DEFAULT_SYMBOLS,),
)
@click.option(
    "--fg-colors",
    type=str,
    default=formatter.DEFAULT_FG_COLORS,
    help="Colour cycle for foreground colours. Default: '%s', Choices: '0rgbcmykwRGBCMYKW'"
    % (formatter.DEFAULT_FG_COLORS,),
)
@click.option(
    "--bg-colors",
    type=str,
    default=formatter.DEFAULT_BG_COLORS,
    help="Colour cycle for background colours. Default: '%s', Choices: '0rgbcmykwRGBCMYKW'"
    % (formatter.DEFAULT_BG_COLORS,),
)
def histoprint(infile, **kwargs):
    """Read INFILE and print a histogram of the contained columns.

    INFILE can be '-', in which case the data is read from STDIN.
    """

    # Read the data
    data = np.loadtxt(infile, ndmin=2)

    # Interpret bins
    bins = kwargs.pop("bins", "10")
    bins = np.fromiter(bins.split(), dtype=float)
    if len(bins) == 1:
        bins = int(bins[0])
    if isinstance(bins, int):
        minval = np.nanmin(data)
        maxval = np.nanmax(data)
        bins = np.linspace(minval, maxval, bins + 1)

    # Create the histogram(s)
    hist = [[], bins]
    for d in data.T:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    print_hist(hist, **kwargs)
