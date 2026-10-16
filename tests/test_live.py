"""Tests for :mod:`histoprint.live` (the ``LiveHistogram`` context manager)."""

import io
import re

import numpy as np

import histoprint as hp
from histoprint.live import LiveHistogram


class RecordingStream:
    """Record ``write()`` calls and mimic ``isatty()`` like a terminal."""

    def __init__(self, tty: bool = True) -> None:
        self.tty = tty
        self.writes: list[str] = []

    def isatty(self) -> bool:
        return self.tty

    def write(self, s: str) -> None:
        self.writes.append(s)

    def flush(self) -> None:
        pass


class BrokenIsattyStream(RecordingStream):
    """A stream whose ``isatty()`` raises, like a closed/degraded stream."""

    def isatty(self) -> bool:
        msg = "I/O operation on closed file"
        raise ValueError(msg)


def make_hist(bins: int = 11) -> tuple[np.ndarray, np.ndarray]:
    """Return a deterministic (counts, edges) pair that renders 2-D."""
    edges = np.linspace(-3, 3, bins + 1)
    counts = np.histogram(np.linspace(-2.5, 2.5, 500), bins=edges)[0]
    return counts, edges


def expected_frame(hist, **kwargs) -> str:
    """Render ``hist`` exactly the way ``print_hist`` would."""
    buffer = io.StringIO()
    hp.print_hist(hist, file=buffer, use_color=False, columns=80, **kwargs)
    return buffer.getvalue()


def test_repaints_in_place():
    stream = RecordingStream(tty=True)
    hist1 = make_hist()
    hist2 = (hist1[0] * 2, hist1[1])
    with LiveHistogram(file=stream, use_color=False, columns=80) as live:
        live.update(hist1)
        live.update(hist2)

    assert len(stream.writes) == 2
    first, second = stream.writes
    assert "\x1b" not in first
    match = re.match(r"\x1b\[(\d+)F\x1b\[J", second)
    assert match is not None
    # Cursor moves back by the number of lines of the previous frame.
    assert int(match.group(1)) == first.count("\n")
    # The rest of the second write is a plain re-render of the new histogram.
    assert second[match.end() :] == expected_frame(hist2)


def test_shrinking_frame():
    stream = RecordingStream(tty=True)
    with LiveHistogram(
        file=stream, use_color=False, columns=80, scale_bin_width=False
    ) as live:
        live.update(make_hist(bins=11))
        live.update(make_hist(bins=6))

    first, second = stream.writes
    match = re.match(r"\x1b\[(\d+)F\x1b\[J", second)
    assert match is not None
    assert int(match.group(1)) == first.count("\n")
    # A shorter frame is repainted in place rather than appended below.
    assert second[match.end() :].count("\n") < first.count("\n")


def test_growing_frame():
    """A taller frame repaints in place, and the cursor math tracks the
    new, larger frame height for the next update."""
    stream = RecordingStream(tty=True)
    tall = make_hist(bins=11)
    tall2 = (tall[0] * 2, tall[1])  # new content, same height as ``tall``
    with LiveHistogram(
        file=stream, use_color=False, columns=80, scale_bin_width=False
    ) as live:
        live.update(make_hist(bins=6))  # shorter first frame
        live.update(tall)  # taller second frame
        live.update(tall2)  # new content, same height

    first, second, third = stream.writes
    m2 = re.match(r"\x1b\[(\d+)F\x1b\[J", second)
    assert m2 is not None
    # The cursor moves up by the previous (shorter) frame's height.
    assert int(m2.group(1)) == first.count("\n")
    # The new frame is taller and is painted in place, not appended below.
    assert second[m2.end() :].count("\n") > first.count("\n")

    m3 = re.match(r"\x1b\[(\d+)F\x1b\[J", third)
    assert m3 is not None
    # After a growth, the next repaint uses the new, larger height.
    assert int(m3.group(1)) == second[m2.end() :].count("\n")
    assert third[m3.end() :] == expected_frame(tall2, scale_bin_width=False)


def test_non_tty_fallback():
    stream = RecordingStream(tty=False)
    hist1 = make_hist()
    hist2 = make_hist(bins=8)
    with LiveHistogram(file=stream, use_color=False, columns=80) as live:
        live.update(hist1)
        live.update(hist2)

    assert len(stream.writes) == 2
    assert all("\x1b" not in write for write in stream.writes)
    assert stream.writes[0] == expected_frame(hist1)
    assert stream.writes[1] == expected_frame(hist2)


def test_isatty_valueerror_falls_back():
    # Regression test: a stream whose ``isatty()`` raises ValueError (e.g. a
    # closed/degraded stream) must not crash update(); it falls back to plain
    # printing without escape codes. This used to raise on the second update.
    stream = BrokenIsattyStream()
    hist1 = make_hist()
    hist2 = (hist1[0] * 2, hist1[1])
    with LiveHistogram(file=stream, use_color=False, columns=80) as live:
        live.update(hist1)
        live.update(hist2)

    assert len(stream.writes) == 2
    assert all("\x1b" not in write for write in stream.writes)
    assert stream.writes[0] == expected_frame(hist1)
    assert stream.writes[1] == expected_frame(hist2)


def test_skips_unchanged_frames():
    stream = RecordingStream(tty=True)
    hist = make_hist()
    with LiveHistogram(file=stream, use_color=False, columns=80) as live:
        live.update(hist)
        live.update(hist)

    assert len(stream.writes) == 1


def test_min_interval_skips_fast_updates():
    stream = RecordingStream(tty=True)
    hist1 = make_hist()
    hist2 = (hist1[0] * 3, hist1[1])
    with LiveHistogram(
        file=stream, use_color=False, columns=80, min_interval=60.0
    ) as live:
        live.update(hist1)
        live.update(hist2)

    # The second update arrives well within a minute, so it is dropped.
    assert len(stream.writes) == 1


def test_force_live_on_stringio():
    stream = io.StringIO()
    hist = make_hist()
    with LiveHistogram(
        file=stream, force_live=True, use_color=False, columns=80
    ) as live:
        live.update(hist)
        live.update((hist[0] * 2, hist[1]))

    assert "\x1b[" in stream.getvalue()


def test_import_from_package():
    assert hp.LiveHistogram is LiveHistogram
