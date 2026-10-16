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
    The first frame is written plainly. Every subsequent frame is preceded by
    escape sequences that move the cursor back to the beginning of the
    previous frame and erase everything below it::

        ESC[<n>F    Move the cursor to the beginning of the n-th previous line
        ESC[J       Erase from the cursor to the end of the screen

    The output of :func:`print_hist` always ends with a newline, so the
    cursor sits one line below the frame after writing, and ``n`` is simply
    the number of lines of the previous frame. This also handles frames that
    shrink from one update to the next. The last frame stays visible and the
    cursor ends on a fresh line.

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

        control = ""
        if self._started and self._is_terminal():
            # Move to the first line of the previous frame and clear below it.
            control = f"\x1b[{self._prev_height}F\x1b[J"
        # Control codes and frame go out in a single write.
        self.file.write(control + frame)
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
