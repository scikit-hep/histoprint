"""Module for rendering histograms as live, in-place updating output.

:class:`LiveHistogram` re-renders a histogram at a fixed terminal position by
writing ANSI cursor-control escape codes, so the histogram can be updated
while data is being collected (e.g. from a stream or a detector).
"""

from __future__ import annotations

import io
import sys
import time
from typing import TextIO

from histoprint.formatter import print_hist

__all__ = ["LiveHistogram"]


class LiveHistogram:
    """Redraw a histogram in place at a fixed terminal position.

    Parameters
    ----------
    file : TextIO, optional
        The stream to draw on. Defaults to ``sys.stdout``.
    force_live : bool, optional
        Emit cursor-control escape codes even if ``file.isatty()`` is False.
        This is mainly useful for testing with streams such as
        ``io.StringIO`` (default: False).
    min_interval : float, optional
        Minimum number of seconds between two repaints. Updates arriving
        sooner than this after a repaint are dropped, so the histogram is
        refreshed at most this often (default: no throttling).
    **kwargs :
        All other keyword arguments are passed to :func:`print_hist`, e.g.
        ``title``, ``labels``, ``stack``, ``use_color`` or ``columns``.

    Notes
    -----
    The first frame is written plainly. Every subsequent frame overwrites the
    previous frame line by line: the cursor is moved back to the beginning of
    the previous frame and each line is rewritten followed by ``ESC[K``
    (erase to end of line), so content that disappears (e.g. a bar that
    shrank) is removed without blanking the whole frame::

        ESC[<n>F    Move the cursor to the beginning of the n-th previous line
        ESC[K       Erase from the cursor to the end of the current line

    The previous frame is never erased as a whole, which avoids the blank
    "flash" between repaints (important when the output is recorded or
    mirrored, where large coloured frames may be delivered in several
    chunks). If the new frame is shorter, the lines left over below it are
    erased with ``ESC[J``; if it is taller, the extra lines are written
    below. The output of :func:`print_hist` always ends with a newline, so
    the cursor sits one line below the frame after writing, and ``n`` is
    simply the number of lines of the previous frame. The last frame stays
    visible and the cursor ends on a fresh line.

    If the stream is not a terminal (e.g. a pipe or a file), no escape codes
    are written and every update prints like :func:`print_hist`.

    The histogram must fit into the terminal, because the cursor cannot move
    back beyond the terminal scroll region.

    """

    def __init__(
        self,
        file: TextIO | None = None,
        force_live: bool = False,
        min_interval: float = 0.0,
        **kwargs,
    ):
        self.file = file if file is not None else sys.stdout
        self.force_live = force_live
        self.min_interval = min_interval
        self.kwargs = kwargs
        self._prev_height = 0
        self._prev_frame: str | None = None
        self._last_render = -float("inf")
        self._started = False

    @staticmethod
    def _frame_lines(frame: str) -> int:
        """Return the number of terminal lines occupied by ``frame``."""
        lines = frame.count("\n")
        if frame and not frame.endswith("\n"):
            lines += 1
        return lines

    def _is_terminal(self) -> bool:
        """Return whether cursor-control codes can be used on the stream."""
        if self.force_live:
            return True
        try:
            return bool(self.file.isatty())
        except (AttributeError, ValueError):
            return False

    def _repaint(self, frame: str) -> str:
        """Build the escape sequence that overwrites the previous frame.

        The previous frame is replaced line by line: the cursor is moved to
        the top of it, then every line of the new frame is written followed
        by ``ESC[K``, which erases the rest of that line. Erasing each line
        *after* painting it keeps the screen content-continuous, so there is
        no blank flash between repaints. If the new frame is shorter, the
        rows left over from the old frame are erased below it.
        """

        lines = frame.split("\n")[:-1]  # print_hist output ends with "\n"
        new_height = len(lines)

        sequence = [f"\x1b[{self._prev_height}F\r"]
        for line in lines:
            sequence.append("\r" + line + "\x1b[K\n")
        if new_height < self._prev_height:
            # The cursor is on the first row left over from the old frame;
            # erase it and everything below it (all empty by design).
            sequence.append("\r\x1b[J")
        return "".join(sequence)

    def update(self, hist) -> None:
        """Redraw ``hist`` in place.

        Parameters
        ----------
        hist :
            A histogram in any format accepted by :func:`print_hist`.

        Notes
        -----
        Updates that arrive sooner than ``min_interval`` after a repaint, or
        that render exactly like the last frame, are skipped without writing.

        """

        now = time.monotonic()
        # Throttle: drop updates that are too fast to be worth a repaint.
        if self._started and now - self._last_render < self.min_interval:
            return

        # Render into memory so the frame size is known before writing.
        buffer = io.StringIO()
        print_hist(hist, file=buffer, **self.kwargs)
        frame = buffer.getvalue()

        # Skip repaints if nothing changed.
        if self._started and frame == self._prev_frame:
            return

        if self._started and self._is_terminal():
            output = self._repaint(frame)
        else:
            output = frame
        self.file.write(output)
        self.file.flush()

        self._prev_height = self._frame_lines(frame)
        self._prev_frame = frame
        self._last_render = now
        self._started = True

    def __enter__(self):
        """Enter the live rendering context."""
        return self

    def __exit__(self, *_exc_info) -> None:
        """Leave the last frame on screen; the cursor is on a fresh line."""
        return
