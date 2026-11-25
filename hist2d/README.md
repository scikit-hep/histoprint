# Hist2D

Self-contained implementation of **2D histogram printing** for the terminal:
histograms are rendered as heatmaps where every bin is a single character,
encoded by a ramp of shading characters (` ░▒▓█`) and, when colors are enabled,
by a heat-map color ramp (`kKrRyYw`).

## Requirements

- `numpy` (required)
- `uhi` (required, for `numpy.histogram2d`/`histogramdd` tuples and
  `PlottableHistogram` inputs)
- `pandas` (optional, CSV input only)
- `uproot` + `awkward` (optional, ROOT input only)

Run everything from the repository root, where `hist2d/` is importable.

## Usage

```python
import numpy as np

from hist2d import print_2d_hist, text_hist2d

x = np.random.randn(1000)
y = np.random.randn(1000)

# numpy.histogram2d output
hist = np.histogram2d(x, y, bins=20)
print_2d_hist(hist, title="2D heatmap")

# text_hist2d is a thin wrapper around numpy.histogram2d
text_hist2d(x, y, bins=20, title="Another 2D heatmap")
```

Supported inputs (anything with exactly two axes):

- `(H, xedges, yedges)` tuples from `numpy.histogram2d`
- `(H, [xedges, yedges])` tuples from `numpy.histogramdd`
- `PlottableHistogram` objects such as `boost_histogram.Histogram`

Options (passed to `Hist2DFormatter`): `title`, `columns`, `lines`, `symbols`,
`fg_colors`, `max_count`, `use_color`.

## Behavior

- Bins are stretched if there is more space than bins.
- If there are more bins than plot area, adjacent bins are averaged.
- All-zero histograms are handled (legend range normalized to 1).

## Command line

`hist2d` ships a small CLI (stdlib `argparse` only; `pandas`/`uproot`+`awkward`
are optional and used only for CSV/ROOT input):

```bash
python -m hist2d data.txt --no-color -c 80         # two-column text file
python -m hist2d data.csv -f x -f y -t "2D heatmap" # CSV by column names
python -m hist2d hist.root -f h2 --no-color        # ROOT TH2 histogram
cat data.txt | python -m hist2d --no-color         # stdin
```

The CLI accepts the same inputs as the library and then prints the heatmap:

- TXT files: whitespace-separated columns; `-f 0 -f 1` selects columns (default:
  the first two), `-C "data[0] > 0."` filters rows.
- CSV files: column names via `-f x -f y`, cuts via pandas expressions.
- ROOT files: `-f` is either the path of a single 2D histogram (TH2) or two
  `Tree/Branch` fields that are histogrammed together.

Plotting options: `-b/--bins` (integer count or space-separated edges, e.g.
`-b "0 1 2 3"`), `--bins-x`, `--bins-y`, `--range-x`, `--range-y`, `-t/--title`,
`--symbols`, `--fg-colors`, `--use-color/--no-color`, `--max-count`,
`--density`, `-c/--columns`, `-r/--lines`.

## Running the tests

```bash
python -m pytest tests/test_hist2d.py tests/test_cli2d.py   # from the repository root
```
