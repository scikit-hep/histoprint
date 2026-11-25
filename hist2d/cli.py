"""Command-line interface for the standalone hist2d package.

Reads two-column data (TXT/CSV) or a ROOT 2D histogram and prints it as a
terminal heatmap::

    python -m hist2d data.txt --no-color -c 80
    python -m hist2d data.csv -f x -f y -t "2D heatmap"
    python -m hist2d hist.root -f h2 --no-color
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np

from hist2d import __version__
from hist2d.formatter import DEFAULT_2D_FG_COLORS, DEFAULT_2D_SYMBOLS, print_2d_hist

__all__ = ["main"]


class CliError(Exception):
    """A user-facing error (printed to stderr, exits with code 1)."""


def _error(msg):
    """Write a message to stderr (``print`` is not allowed by the linter)."""

    sys.stderr.write(msg + "\n")


def _bin_spec(value):
    """Parse a bins specification: an integer count or space-separated edges."""

    vals = [float(v) for v in value.split()]
    if len(vals) == 1:
        return int(vals[0])
    return np.asarray(vals)


def _formatter_kwargs(args):
    """The ``Hist2DFormatter`` keyword arguments for the CLI options."""

    return {
        "title": args.title,
        "symbols": args.symbols,
        "fg_colors": args.fg_colors,
        "use_color": args.use_color,
        "max_count": args.max_count,
        "columns": args.columns,
        "lines": args.lines,
    }


def _print_hist2d(hist, args):
    """Print an already-built 2D histogram."""

    print_2d_hist(hist, **_formatter_kwargs(args))


def _print_2d(x, y, args):
    """Bin ``x`` and ``y`` into a 2D histogram and print it as a heatmap."""

    try:
        bins_x = (
            _bin_spec(args.bins_x) if args.bins_x is not None else _bin_spec(args.bins)
        )
        bins_y = (
            _bin_spec(args.bins_y) if args.bins_y is not None else _bin_spec(args.bins)
        )
        hist_kwargs: dict[str, Any] = {"bins": (bins_x, bins_y)}
        ranges = {}
        if args.range_x is not None:
            ranges[0] = tuple(args.range_x)
        if args.range_y is not None:
            ranges[1] = tuple(args.range_y)
        if ranges:
            if 0 not in ranges:
                ranges[0] = (float(np.nanmin(x)), float(np.nanmax(x)))
            if 1 not in ranges:
                ranges[1] = (float(np.nanmin(y)), float(np.nanmax(y)))
            hist_kwargs["range"] = (ranges[0], ranges[1])
        if args.density:
            hist_kwargs["density"] = True
        hist = np.histogram2d(x, y, **hist_kwargs)
    except (TypeError, ValueError) as e:
        raise CliError(str(e)) from None
    _print_hist2d(hist, args)


def _read_input(infile):
    """Read *infile* into a text handle, supporting '-' for stdin."""

    if infile == "-":
        return StringIO(sys.stdin.read())
    try:
        return StringIO(Path(infile).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def _cut_txt(data, cut):
    """Apply a cut expression to a TXT data array."""

    if not cut:
        return data
    try:
        return data[:, eval(cut)]
    except Exception as e:  # noqa: BLE001
        raise CliError(f"Error interpreting the cut string: {e}") from None  # noqa: EM102


def _parse_txt(infile, args):
    """Interpret *infile* as a whitespace-separated table; return (x, y)."""

    data = np.loadtxt(infile, ndmin=2).T
    data = _cut_txt(data, args.cut)
    if data.ndim != 2 or data.shape[0] < 2:
        msg = "Need at least two columns to build a 2D histogram."
        raise CliError(msg)
    fields = args.fields or [0, 1]
    try:
        fields = [int(f) for f in fields]
    except ValueError:
        msg = "Fields for a TXT file must be integers."
        raise CliError(msg) from None
    try:
        data = data[fields]
    except (KeyError, IndexError):
        msg = "Field out of bounds."
        raise CliError(msg) from None
    if data.ndim != 2 or data.shape[0] < 2:
        msg = "Need at least two columns to build a 2D histogram."
        raise CliError(msg)
    return data[0], data[1]


def _parse_csv(infile, args):
    """Interpret *infile* as a CSV file; return (x, y)."""

    import pandas as pd  # noqa: PLC0415 - Conditional import for optional CSV support

    df = pd.read_csv(infile)
    if args.fields:
        try:
            df = df[args.fields]
        except KeyError:
            msg = "Unknown column name."
            raise CliError(msg) from None
    else:
        df = df.select_dtypes(include="number")
        if df.shape[1] == 0:
            raise ValueError("No numeric columns found in CSV input.")  # noqa: EM101
    if args.cut:
        try:
            df = df[df.eval(args.cut)]
        except Exception as e:  # noqa: BLE001
            raise CliError(f"Error interpreting the cut string: {e}") from None  # noqa: EM102
    if df.shape[1] < 2:
        msg = "Need at least two columns to build a 2D histogram."
        raise CliError(msg)
    data = df.to_numpy().T
    return data[0], data[1]


def _parse_root(infile, args):
    """Interpret *infile* as a ROOT file.

    Returns ``("hist", (values, xedges, yedges))`` for a single 2D histogram
    or ``("data", x, y)`` for two TTree branches.

    """

    try:
        import uproot as up  # noqa: PLC0415 - Conditional import for optional ROOT support
    except ImportError:
        _error("Cannot try ROOT file format. Uproot module not found.")
        raise
    try:
        import awkward as ak  # noqa: PLC0415 - Conditional import for optional ROOT support
    except ImportError:
        _error("Cannot try ROOT file format. Awkward module not found.")
        raise

    F = up.open(infile)
    fields = args.fields or []
    if not fields:
        msg = "Must specify at least one field for ROOT files."
        raise CliError(msg)

    if len(fields) == 1:
        # A single 2D histogram object
        try:
            obj = F[fields[0]]
        except KeyError:
            raise CliError(
                f"Could not find key '{fields[0]}'. Possible values: {F.keys()}"  # noqa: EM102
            ) from None
        try:
            values, *edges = obj.to_numpy()
        except (AttributeError, TypeError, ValueError) as e:
            raise CliError(f"'{fields[0]}' is not a (2D) histogram.") from e  # noqa: EM102
        if len(edges) == 1 and isinstance(edges[0], (tuple, list)):
            edges = edges[0]
        return ("hist", (np.asarray(values), *[np.asarray(ee) for ee in edges]))

    # Two TTree branches
    if len(fields) != 2:
        msg = "Expected either one histogram or two branches for ROOT files."
        raise CliError(msg)
    arrays = []
    tree = None
    for field in fields:
        split = field.split("/")
        if len(split) != 2:
            msg = "ROOT branch fields must have the form 'Tree/Branch'."
            raise CliError(msg)
        name = split[0]
        try:
            t = F[name]
        except KeyError:
            raise CliError(
                f"Could not find tree '{name}'. Possible values: {F.keys()}"  # noqa: EM102
            ) from None
        if tree is None:
            tree = t
        elif tree is not t:
            msg = "Both fields must come from the same TTree."
            raise CliError(msg)
        try:
            arr = t[split[1]].array()
        except KeyError:
            raise CliError(
                f"Could not find branch '{split[1]}' in tree '{name}'."  # noqa: EM102
            ) from None
        with contextlib.suppress(ValueError):
            arr = ak.flatten(arr)
        arrays.append(np.asarray(ak.to_numpy(arr)))
    if args.cut:
        if tree is None:  # pragma: no cover - the loop above always sets it
            msg = "Expected at least one TTree."
            raise CliError(msg)
        try:
            index = tree.arrays("cut", aliases={"cut": args.cut}).cut
        except Exception as e:  # noqa: BLE001
            raise CliError(f"Error interpreting the cut string: {e}") from None  # noqa: EM102
        arrays = [a[index] for a in arrays]
    return ("data", arrays[0], arrays[1])


def _run(args):
    """Dispatch to the appropriate file-format interpreter."""

    handle = _read_input(args.infile)
    if handle is not None:
        try:
            parsed = _parse_txt(handle, args)
        except CliError:
            raise
        except (TypeError, ValueError, IndexError):
            parsed = None
        if parsed is not None:
            _print_2d(parsed[0], parsed[1], args)
            return
        handle.seek(0)
        try:
            parsed = _parse_csv(handle, args)
        except ImportError:
            _error("Cannot try CSV file format. Pandas module not found.")
        except CliError:
            raise
        except (TypeError, ValueError, KeyError, IndexError):
            parsed = None
        if parsed is not None:
            _print_2d(parsed[0], parsed[1], args)
            return
    try:
        parsed = _parse_root(args.infile, args)
    except ImportError:
        pass
    except CliError:
        raise
    except (OSError, ValueError):
        parsed = None
    if parsed is not None:
        if parsed[0] == "hist":
            _print_hist2d(parsed[1], args)
        else:
            _print_2d(parsed[1], parsed[2], args)
        return
    msg = "Could not interpret the file format"
    raise CliError(msg)


def _build_parser():
    """Build the argument parser for the ``hist2d`` CLI."""

    parser = argparse.ArgumentParser(
        prog="hist2d",
        description="Read two-column data (TXT/CSV) or a ROOT 2D histogram and "
        "print it as a terminal heatmap. INFILE can be '-', in which case the "
        "data is read from STDIN.",
    )
    parser.add_argument(
        "infile", nargs="?", default="-", help="input file ('-' for stdin)"
    )
    parser.add_argument("--version", action="version", version=f"hist2d {__version__}")
    parser.add_argument(
        "-b",
        "--bins",
        default="10",
        help="Bins per axis: an integer count or space-separated edges "
        "(e.g. '10' or '0 1 2 3').",
    )
    parser.add_argument(
        "--bins-x", default=None, help="Bins for the x-axis (overrides --bins)."
    )
    parser.add_argument(
        "--bins-y", default=None, help="Bins for the y-axis (overrides --bins)."
    )
    parser.add_argument(
        "--range-x",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=None,
        help="Range of the x-axis. Defaults to the data range.",
    )
    parser.add_argument(
        "--range-y",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=None,
        help="Range of the y-axis. Defaults to the data range.",
    )
    parser.add_argument("-t", "--title", default="", help="Title of the histogram.")
    parser.add_argument(
        "-f",
        "--field",
        dest="fields",
        action="append",
        default=None,
        metavar="FIELD",
        help="Which fields to histogram. For TXT files these are integer column "
        "numbers (default: the first two columns). For CSV files these are the "
        "column names (default: the first two numeric columns). For ROOT files "
        "either the path of a single 2D histogram, or two 'Tree/Branch' fields.",
    )
    parser.add_argument(
        "-C",
        "--cut",
        default=None,
        help="Filter the data by a cut condition. TXT: 'data[0] > 0.'; CSV: a "
        "pandas expression (column names); ROOT: a branch expression.",
    )
    parser.add_argument(
        "--symbols",
        default=DEFAULT_2D_SYMBOLS,
        help=f"Ramp of shading characters (lowest to highest). Default: {DEFAULT_2D_SYMBOLS!r}",
    )
    parser.add_argument(
        "--fg-colors",
        default=DEFAULT_2D_FG_COLORS,
        help=f"Ramp of terminal colors (lowest to highest). Default: {DEFAULT_2D_FG_COLORS!r}",
    )
    parser.add_argument(
        "--use-color",
        dest="use_color",
        action="store_true",
        default=None,
        help="Use terminal colors (default for the terminal).",
    )
    parser.add_argument(
        "--no-color",
        dest="use_color",
        action="store_false",
        default=None,
        help="Do not use terminal colors.",
    )
    parser.add_argument(
        "--max-count", type=float, default=None, help="Set the maximum bin content."
    )
    parser.add_argument(
        "--density", action="store_true", help="Normalize the histogram."
    )
    parser.add_argument(
        "-c",
        "--columns",
        type=int,
        default=None,
        help="Total width of the displayed histogram in characters.",
    )
    parser.add_argument(
        "-r",
        "--lines",
        type=int,
        default=None,
        help="Approximate total height of the displayed histogram in characters.",
    )
    return parser


def main(argv=None):
    """Entry point of the ``hist2d`` CLI. Returns the exit code."""

    args = _build_parser().parse_args(argv)
    try:
        _run(args)
    except CliError as e:
        _error(f"error: {e}")
        return 1
    except (TypeError, ValueError) as e:
        # Formatter/renderer errors (e.g. a 1D ROOT histogram) are user-facing
        _error(f"error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
