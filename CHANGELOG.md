# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.7.1]

### Fixed
- Files that are not valid text, CSV, or ROOT input now show the file-format
  error instead of a traceback or a histogram of `nan` edges (issue #159).
- Giving fewer `--label` options than `--field` options for a ROOT file now
  shows a clear error instead of dropping the extra fields (issue #159).
- All-zero or degenerate bin edges no longer print an `x 10^+nan` exponent.
- Composing a symbol onto an existing `X` glyph keeps the glyph.

### Changed
- Discrete axes, mismatched bin edges, and empty input sequences now raise clear
  `TypeError`/`ValueError` messages instead of an assertion or a test helper.

## [2.7.0]

### Fixed
- Out-of-range `--field` on text files now shows "Field out of bounds." instead of a raw traceback (issue #159).
- Overlaying the same composing symbol no longer erases the glyph (issue #159).
- Integer bin edges and plain list edges no longer crash `HistFormatter` (bug 3, issue #159).

### Removed
- Support for Python 3.8, 3.9.

## [2.6.0]

### Removed
- Support for Python <= 3.8

## [2.5.0]

### Added
- Support dor Python up to 3.13.

## [2.4.0]

### Addded
- RichHistogram class for use with the `rich` package.
- Argument to set maximum count in bins for plotting.

### Changed
- Changed tick formatting.

## [2.3.0]

### Changed
- Change name of optional extra requirement from 'root' to 'uproot'.

## [2.2.0]

### Added
- Added support for stacks of PlottableHistograms.

## [2.1.0]

### Added
- Added a `--cut` option to the command line tool to filter the plotted data.

### Fixed
- Now handles empty data gracefully.
