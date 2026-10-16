"""Tests for the hist2d command-line interface."""

import io
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from hist2d import cli

NUMERIC = (
    "1.0 4.0\n2.0 5.0\n2.0 5.0\n3.0 6.0\n3.0 6.0\n3.0 6.0\n4.0 7.0\n4.0 7.0\n5.0 8.0\n"
)


def test_txt_happy_path(tmp_path, capsys):
    """A plain whitespace-separated two-column file renders a heatmap."""
    data = tmp_path / "data.txt"
    data.write_text(NUMERIC)
    rc = cli.main([str(data), "--no-color", "-c", "40", "-r", "10"])
    out = capsys.readouterr().out
    assert rc == 0
    assert any(s in out for s in "░▒▓█")
    assert "\x1b[" not in out


def test_txt_fields_bins_ranges(tmp_path, capsys):
    """Explicit fields, bin count and ranges are honoured."""
    data = tmp_path / "data.txt"
    data.write_text(NUMERIC)
    rc = cli.main(
        [
            str(data),
            "-f",
            "0",
            "-f",
            "1",
            "-b",
            "8",
            "--range-x",
            "0",
            "6",
            "--range-y",
            "3",
            "9",
            "--no-color",
            "-c",
            "40",
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out


def test_txt_cut(tmp_path, capsys):
    """A TXT cut filters the rows before binning."""
    data = tmp_path / "data.txt"
    data.write_text(NUMERIC)
    rc = cli.main([str(data), "-C", "data[0] > 2.", "--no-color", "-c", "40"])
    assert rc == 0
    assert capsys.readouterr().out


def test_txt_too_few_columns(tmp_path, capsys):
    """A single-column file gives a friendly error."""
    data = tmp_path / "one.txt"
    data.write_text("1.0\n2.0\n3.0\n")
    rc = cli.main([str(data), "-c", "40"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "at least two columns" in err
    assert "Traceback" not in err


def test_txt_field_out_of_bounds(tmp_path, capsys):
    """An out-of-range --field gives a friendly message."""
    data = tmp_path / "data.txt"
    data.write_text(NUMERIC)
    rc = cli.main([str(data), "-f", "99", "-c", "40"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Field out of bounds." in err
    assert "Traceback" not in err


def test_garbage_input(tmp_path, capsys):
    """Non-numeric input is rejected with the file-format error."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"a": [1, 2, 3]}\n')
    rc = cli.main([str(bad), "-c", "40"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Could not interpret the file format" in err
    assert "Traceback" not in err


def test_csv_happy_path(tmp_path, capsys):
    """A CSV file with named fields renders successfully."""
    pytest.importorskip("pandas")
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("x,y\n1.0,4.0\n2.0,5.0\n3.0,6.0\n")
    rc = cli.main(
        [str(csv_file), "-f", "x", "-f", "y", "--no-color", "-c", "40", "-r", "10"]
    )
    assert rc == 0
    assert capsys.readouterr().out


def test_stdin(monkeypatch, capsys):
    """INFILE '-' reads two columns from stdin."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(NUMERIC))
    rc = cli.main(["-", "--no-color", "-c", "40", "-r", "10"])
    assert rc == 0
    assert capsys.readouterr().out


def test_root_th2(tmp_path, capsys):
    """A ROOT file with a single 2D histogram is plotted directly."""
    up = pytest.importorskip("uproot")
    x = [1.0, 2.0, 2.5, 3.0, 3.5, 4.0]
    y = [4.0, 5.0, 5.5, 6.0, 6.5, 7.0]
    h2d, xe, ye = np.histogram2d(x, y, bins=3)
    root_file = tmp_path / "h2.root"
    with up.recreate(root_file) as f:
        f["h2"] = (h2d, xe, ye)
    rc = cli.main([str(root_file), "-f", "h2", "--no-color", "-c", "40", "-r", "10"])
    assert rc == 0
    assert capsys.readouterr().out


def test_root_no_field(tmp_path, capsys):
    """ROOT files without a field give a friendly error."""
    up = pytest.importorskip("uproot")
    root_file = tmp_path / "empty.root"
    with up.recreate(root_file):
        pass
    rc = cli.main([str(root_file), "-c", "40"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "at least one field" in err
    assert "Traceback" not in err


def test_python_dash_m(tmp_path):
    """``python -m hist2d`` runs the CLI end to end."""
    data = tmp_path / "data.txt"
    data.write_text(NUMERIC)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hist2d",
            str(data),
            "--no-color",
            "-c",
            "40",
            "-r",
            "10",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0
    assert any(s in result.stdout for s in "░▒▓█")
