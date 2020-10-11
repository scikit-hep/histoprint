"""Module containing the CLI programs for histoprint."""

import numpy as np
import click
from histoprint import *
import histoprint.formatter as formatter


@click.command()
@click.argument("infile", type=click.Path(exists=True, dir_okay=False, allow_dash=True))
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
@click.option(
    "-f",
    "--field",
    "fields",
    type=str,
    multiple=True,
    help="Which fields to histogram. Interpretation of the fields depends on "
    "the file format. TXT files only support integers for column numbers "
    "starting at 0. For CSV files, the fields must be the names of the columns "
    "as specified in the first line of the file. When plotting from ROOT files, "
    "at least one field must be specified. This can either be the path to a "
    "single TH1, or one or more paths to TTree branches.",
)
@click.option(
    "-c",
    "--columns",
    type=int,
    default=None,
    help="Total width of the displayed historgram in characters. Defaults to width of the terminal.",
)
@click.option(
    "-r",
    "--lines",
    type=int,
    default=None,
    help="Approximate total height of the displayed historgram in characters. Calculated from number of columns by default.",
)
@click.version_option()
def histoprint(infile, **kwargs):
    """Read INFILE and print a histogram of the contained columns.

    INFILE can be '-', in which case the data is read from STDIN.
    """

    # Read file into buffer for use by implementations
    try:
        with click.open_file(infile, "rt") as f:
            data = f.read(-1)
    except UnicodeDecodeError:
        # Probably some binary file
        data = ""

    if len(data) > 0:
        try:
            # Python 2
            from StringIO import StringIO
        except ImportError:
            # Python 3
            from io import StringIO
        data_handle = StringIO(data)
        del data

        # Try to interpret file as textfile
        try:
            data_handle.seek(0)
            _histoprint_txt(data_handle, **kwargs)
            exit(0)
        except ValueError:
            pass

        # Try to interpret file as CSV file
        try:
            data_handle.seek(0)
            _histoprint_csv(data_handle, **kwargs)
            exit(0)
        except ImportError:
            click.echo("Cannot try CSV file format. Pandas module not found.", err=True)

    # Try to interpret file as ROOT file
    try:
        _histoprint_root(infile, **kwargs)
        exit(0)
    except ImportError:
        click.echo("Cannot try ROOT file format. Uproot module not found.", err=True)

    click.echo("Could not interpret file format.", err=True)
    exit(1)


def _bin_edges(kwargs, data):
    """Get the desired bin edges."""
    bins = kwargs.pop("bins", "10")
    bins = np.fromiter(bins.split(), dtype=float)
    if len(bins) == 1:
        bins = int(bins[0])
    if isinstance(bins, int):
        minval = np.inf
        maxval = -np.inf
        for d in data:
            minval = min(minval, np.nanmin(d))
            maxval = max(maxval, np.nanmax(d))
        bins = np.linspace(minval, maxval, bins + 1)
    return bins


def _histoprint_txt(infile, **kwargs):
    """Interpret file as as simple whitespace separated table."""

    # Read the data
    data = np.loadtxt(infile, ndmin=2)
    data = data.T

    # Interpret field numbers
    fields = kwargs.pop("fields", [])
    if len(fields) > 0:
        try:
            fields = [int(f) for f in fields]
        except ValueError:
            click.echo("Fields for a TXT file must be integers.", err=True)
            exit(1)
        try:
            data = data[fields]
        except KeyError:
            click.echo("Field out of bounds.", err=True)
            exit(1)

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist = [[], bins]
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    print_hist(hist, **kwargs)


def _histoprint_csv(infile, **kwargs):
    """Interpret file as as CSV file."""

    import pandas as pd

    # Read the data
    data = pd.read_csv(infile)

    # Interpret field numbers/names
    fields = list(kwargs.pop("fields", []))
    if len(fields) > 0:
        try:
            data = data[fields]
        except KeyError:
            click.echo("Unknown column name.", err=True)
            exit(1)

    # Get default columns labels
    if kwargs.get("labels", ("",)) == ("",):
        kwargs["labels"] = data.columns

    # Convert to array
    data = data.to_numpy().T

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist = [[], bins]
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    print_hist(hist, **kwargs)


def _histoprint_root(infile, **kwargs):
    """Interpret file as as ROOT file."""

    import uproot as up

    # Open root file
    F = up.open(infile)

    # Interpret field names
    fields = list(kwargs.pop("fields", []))
    if len(fields) == 0:
        click.echo("Must specify at least on field for ROOT files.", err=True)
        click.echo(F.keys())
        exit(1)

    # Get default columns labels
    if kwargs.get("labels", ("",)) == ("",):
        kwargs["labels"] = [field.split("/")[-1] for field in fields]

    # Read the data
    if len(fields) == 1:
        # Possible a single histogram
        try:
            hist = F[fields[0]].numpy()
        except (AttributeError, KeyError):
            pass
        else:
            kwargs.pop("bins", None)  # Get rid of useless parameter
            print_hist(hist, **kwargs)
            return

    data = []
    for field in fields:
        branch = F
        for key in field.split("/"):
            try:
                branch = branch[key]
            except KeyError:
                click.echo(
                    "Could not find key '%s'. Possible values: %s"
                    % (key, branch.keys())
                )
                exit(1)
        try:
            d = np.array(branch.array().flatten())
        except ValueError:
            click.echo(
                "Could not interpret root object '%s'. Possible child branches: %s"
                % (key, branch.keys())
            )
            exit(1)
        data.append(d)

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist = [[], bins]
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    print_hist(hist, **kwargs)
