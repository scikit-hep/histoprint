"""Shared configuration for the hist2d test suite."""

import sys
from pathlib import Path

# Make the hist2d package importable when the tests are run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
