"""Tests for the histoprint command line interface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from histoprint.cli import histoprint

DATA = Path(__file__).parent / "data"


def test_txt_happy_path():
    """A plain whitespace-separated text file renders successfully."""
    runner = CliRunner()
    result = runner.invoke(histoprint, [str(DATA / "3D.txt"), "-c", "60"])
    assert result.exit_code == 0
    assert "nan" not in result.output


def test_txt_field_out_of_bounds():
    """An out-of-range --field gives a friendly message, not a traceback."""
    runner = CliRunner()
    result = runner.invoke(histoprint, [str(DATA / "3D.txt"), "-f", "99", "-c", "60"])
    assert result.exit_code == 1
    assert "Field out of bounds." in result.output
    # No traceback should leak through.
    assert "Traceback" not in result.output


def test_garbage_json_input(tmp_path):
    """Non-numeric JSON-ish input is rejected, not rendered as nan."""
    pytest.importorskip("pandas")
    bad = tmp_path / "bad.json"
    bad.write_text('{"a": [1,2,3], "b": "text"}\n')
    runner = CliRunner()
    result = runner.invoke(histoprint, [str(bad), "-c", "60"])
    assert result.exit_code != 0
    assert "nan" not in result.output
    assert "Could not interpret the file format" in result.output


def test_csv_happy_path():
    """A genuine CSV with explicit fields and a cut still works."""
    pytest.importorskip("pandas")
    runner = CliRunner()
    result = runner.invoke(
        histoprint,
        [str(DATA / "3D.csv"), "-s", "-f", "x", "-f", "z", "-C", "y > 2.", "-c", "60"],
    )
    assert result.exit_code == 0
    assert "nan" not in result.output


def test_root_label_field_mismatch():
    """Fewer explicit labels than fields errors instead of dropping fields."""
    pytest.importorskip("uproot")
    runner = CliRunner()
    result = runner.invoke(
        histoprint,
        [str(DATA / "histograms.root"), "-f", "one", "-f", "two", "-l", "OnlyOne"],
    )
    assert result.exit_code == 1
    assert "label" in result.output.lower()
