"""
Values the web lab (docs/lab) keeps in both JavaScript and Python, because
neither side can import the other's modules. These tests read the source
files, so they need neither a browser nor Pyodide.
"""

import re
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent / "docs" / "lab"


def _value(path, pattern):
    match = re.search(pattern, (LAB / path).read_text(), re.M)
    assert match, f"{pattern} not found in {path}"
    return int(match[1])


def test_interpolation_threshold_agrees():
    """worker.py and the JS decide alike which cities get mid-block frames."""
    js = _value("js/constants.js", r"^export const INTERPOLATE_MAX_CITY_SIZE = (\d+);")
    py = _value("worker.py", r"^INTERPOLATE_MAX_CITY_SIZE = (\d+)$")
    assert js == py
