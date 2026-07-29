"""Module montaining classes that support the `rich` console protocol."""

from rich.text import Text

from histoprint import formatter

__all__ = ["RichHistogram"]


class RichHistogram:
    """Histogram object that supports `Rich`'s `Console Protocol`.

    Ths provided `hist` is kept as a reference, so it is possible to update its
    contents after the creation of the RichHistogram.

    Parameters
    ----------

    hist :
        A compatible histogram type.
    **kwargs : optional
        Additional keyword arguments are passed to the `HistFormatter`.

    """

    def __init__(self, hist, **kwargs):
        self.hist = hist
        self.kwargs = kwargs

    def __rich__(self):
        """Output rich formatted histogram."""

        count, edges = formatter.get_count_edges(self.hist)
        hist_formatter = formatter.HistFormatter(edges, **self.kwargs)

        text = Text.from_ansi(hist_formatter.format_histogram(count))

        # Make sure lines are never wrapped or right-justified
        text.justify = "left"
        text.overflow = "ellipsis"
        text.no_wrap = True

        return text
