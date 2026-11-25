"""hist2d - render 2D histograms as terminal heatmaps (self-contained)."""

from hist2d.formatter import (
    Hist2DFormatter,
    print_2d_hist,
    text_hist2d,
)

__version__ = "0.1.0"

__all__ = (
    "Hist2DFormatter",
    "__version__",
    "print_2d_hist",
    "text_hist2d",
)
