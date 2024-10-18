"""Module containing the CLI programs for histoprint."""

import contextlib
from io import StringIO
from typing import Any, Dict, List, Tuple

import click
import numpy as np

import histoprint as hp
from histoprint import formatter


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
    help=f"Symbol cycle for multiple histograms. Choices & default: '{formatter.DEFAULT_SYMBOLS}'",
)
@click.option(
    "--fg-colors",
    type=str,
    default=formatter.DEFAULT_FG_COLORS,
    help=f"Colour cycle for foreground colours. Default: '{formatter.DEFAULT_FG_COLORS}', Choices: '0rgbcmykwRGBCMYKW'",
)
@click.option(
    "--bg-colors",
    type=str,
    default=formatter.DEFAULT_BG_COLORS,
    help=f"Colour cycle for background colours. Default: '{formatter.DEFAULT_BG_COLORS}', Choices: '0rgbcmykwRGBCMYKW'",
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
    "single TH1, or one or more paths to TTree branches. Also supports slicing "
    "of array-like branches, e.g. use 'tree/branch[:,2]' to histogram the 3rd "
    "elements of a vector-like branch.",
)
@click.option(
    "-C",
    "--cut",
    "cut",
    type=str,
    help="Filter the data to be plotted by a cut condition. For ROOT files, "
    "variables must be referenced by their branch name within the TTree, e.g. "
    "'momentum > 100.' rather than 'tree/object/momentum > 100.'. For text "
    "files, the fields are referred to as 'data[i]', where 'i' is the field "
    "number. The variables used in the cut do not have to be part of the "
    "plotted fields.",
)
@click.option(
    "-c",
    "--columns",
    type=int,
    default=None,
    help="Total width of the displayed histogram in characters. Defaults to "
    "width of the terminal.",
)
@click.option(
    "-r",
    "--lines",
    type=int,
    default=None,
    help="Approximate total height of the displayed histogram in characters. "
    "Calculated from number of columns by default.",
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
        data_handle = StringIO(data)
        del data

        # Try to interpret file as textfile
        try:
            data_handle.seek(0)
            _histoprint_txt(data_handle, **kwargs)
            return
        except ValueError:
            pass

        # Try to interpret file as CSV file
        try:
            data_handle.seek(0)
            _histoprint_csv(data_handle, **kwargs)
            raise SystemExit(0)
        except ImportError:
            click.echo("Cannot try CSV file format. Pandas module not found.", err=True)

    # Try to interpret file as ROOT file
    try:
        _histoprint_root(infile, **kwargs)
        return
    except ImportError:
        pass

    raise click.FileError(infile, "Could not interpret the file format")


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
            try:
                minval = min(minval, np.nanmin(d))
                maxval = max(maxval, np.nanmax(d))
            except ValueError:
                # Empty data?
                pass
        bins = np.linspace(minval, maxval, bins + 1)
    return bins


def _histoprint_txt(infile, **kwargs):
    """Interpret file as as simple whitespace separated table."""

    # Read the data
    data = np.loadtxt(infile, ndmin=2)
    data = data.T
    cut = kwargs.pop("cut", "")
    if cut is not None and len(cut) > 0:
        try:
            data = data[:, eval(cut)]
        except Exception as e:
            click.echo("Error interpreting the cut string:", err=True)
            click.echo(e, err=True)
            raise SystemExit(1) from None

    # Interpret field numbers
    fields = kwargs.pop("fields", [])
    if len(fields) > 0:
        try:
            fields = [int(f) for f in fields]
        except ValueError:
            click.echo("Fields for a TXT file must be integers.", err=True)
            raise SystemExit(1) from None
        try:
            data = data[fields]
        except KeyError:
            click.echo("Field out of bounds.", err=True)
            raise SystemExit(1) from None

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist: Tuple[Any, Any] = ([], bins)
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    hp.print_hist(hist, **kwargs)


def _histoprint_csv(infile, **kwargs):
    """Interpret file as as CSV file."""

    import pandas as pd

    # Read the data
    data = pd.read_csv(infile)
    cut = kwargs.pop("cut", "")
    if cut is not None and len(cut) > 0:
        try:
            data = data[data.eval(cut)]
        except Exception as e:
            click.echo("Error interpreting the cut string:", err=True)
            click.echo(e, err=True)
            raise SystemExit(1) from None

    # Interpret field numbers/names
    fields = list(kwargs.pop("fields", []))
    if len(fields) > 0:
        try:
            data = data[fields]
        except KeyError:
            click.echo("Unknown column name.", err=True)
            raise SystemExit(1) from None

    # Get default columns labels
    if kwargs.get("labels", ("",)) == ("",):
        kwargs["labels"] = data.columns

    # Convert to array
    data = data.to_numpy().T

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist: Tuple[Any, Any] = ([], bins)
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    hp.print_hist(hist, **kwargs)


def _histoprint_root(infile, **kwargs):
    """Interpret file as as ROOT file."""

    # Import uproot
    try:
        import uproot as up
    except ImportError:
        click.echo("Cannot try ROOT file format. Uproot module not found.", err=True)
        raise
    # Import awkward
    try:
        import awkward as ak
    except ImportError:
        click.echo("Cannot try ROOT file format. Awkward module not found.", err=True)
        raise

    # Open root file
    F = up.open(infile)

    # Interpret field names
    fields = list(kwargs.pop("fields", []))
    if len(fields) == 0:
        click.echo("Must specify at least one field for ROOT files.", err=True)
        click.echo(F.keys(), err=True)
        raise SystemExit(1)

    # Get default columns labels
    if kwargs.get("labels", ("",)) == ("",):
        kwargs["labels"] = [field.split("/")[-1] for field in fields]
    labels = kwargs.pop("labels")

    # Get possible cut expression
    cut = kwargs.pop("cut", "")

    # Possibly a single histogram
    if len(fields) == 1:
        try:
            hist = F[fields[0]]
        except KeyError:
            pass  # Deal with key error further down
        else:
            try:
                hist = F[fields[0]].to_numpy()
            except AttributeError:
                pass
            else:
                kwargs.pop("bins", None)  # Get rid of useless parameter
                hp.print_hist(hist, **kwargs)
                return

    data = []
    # Find TTrees
    trees: List[up.models.TTree.Model_TTree_v19] = []
    tree_fields: List[List[Dict[str, Any]]] = []
    for field, label in zip(fields, labels):
        branch = F
        splitfield = field.split("/")
        for i, key in enumerate(splitfield):
            try:
                branch = branch[key]
            except KeyError:
                click.echo(
                    f"Could not find key '{key}'. Possible values: {branch.keys()}",
                    err=True,
                )
                raise SystemExit(1) from None
            # Has `arrays` method?
            if hasattr(branch, "arrays"):
                # Found it
                path = "/".join(splitfield[i + 1 :])
                if branch in trees:
                    tree_fields[trees.index(branch)].append(
                        {"label": label, "path": path}
                    )
                else:
                    trees.append(branch)
                    tree_fields.append([{"label": label, "path": path}])

                break

    # Reassign labels in correct order
    labels = []
    # Get and flatten the data
    for tree, fields in zip(trees, tree_fields):
        aliases = {}
        d = []
        for field in fields:
            labels.append(field["label"])
            split = field["path"].split("[")
            path = split[0]
            slic = "[" + "[".join(split[1:]) if len(split) > 1 else ""
            aliases[field["label"]] = path
            # Get the branches
            try:
                d.append(eval("tree[path].array()" + slic))
            except up.KeyInFileError as e:
                click.echo(e, err=True)
                click.echo(f"Possible keys: {tree.keys()}", err=True)
                raise SystemExit(1) from None

        # Cut on values
        if cut is not None:
            try:
                index = tree.arrays("cut", aliases={"cut": cut}).cut
            except up.KeyInFileError as e:
                click.echo(e, err=True)
                click.echo(f"Possible keys: {tree.keys()}", err=True)
                raise SystemExit(1) from None
            except Exception as e:
                click.echo("Error interpreting the cut string:", err=True)
                click.echo(e, err=True)
                raise SystemExit(1) from None

            for i in range(len(d)):
                d[i] = d[i][index]

        # Flatten if necessary
        for i in range(len(d)):
            with contextlib.suppress(ValueError):
                d[i] = ak.flatten(d[i])

            # Turn into flat numpy array
            d[i] = ak.to_numpy(d[i])

        data.extend(d)

    # Assign new label order
    kwargs["labels"] = labels

    # Interpret bins
    bins = _bin_edges(kwargs, data)

    # Create the histogram(s)
    hist = ([], bins)
    for d in data:
        hist[0].append(np.histogram(d, bins=bins)[0])

    # Print the histogram
    hp.print_hist(hist, **kwargs)
