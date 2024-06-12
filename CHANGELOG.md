# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- add support for --field-prefix option at cli

## [2.4.0]

### Added
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
