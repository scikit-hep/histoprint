"""histoprint - Pretty-print histograms to the terminal"""

from histoprint.formatter import HistFormatter, RichHistogram, print_hist, text_hist

from .version import version as __version__

__all__ = (
    "print_hist",
    "text_hist",
    "formatter",
    "HistFormatter",
    "RichHistogram",
    "__version__",
)
