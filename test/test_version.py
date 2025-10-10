#!/usr/bin/env python3
"""Verify version consistency across project files."""

import re
import sys
from pathlib import Path


def extract_version_pyproject():
    """Extract version from pyproject.toml."""
    try:
        content = Path("pyproject.toml").read_text()
        match = re.search(r'^version = "(.*)"', content, re.MULTILINE)
        return match.group(1) if match else None
    except FileNotFoundError:
        return None


def extract_version_init():
    """Extract version from ridehail/__init__.py."""
    try:
        content = Path("ridehail/__init__.py").read_text()
        match = re.search(r'^__version__ = "(.*)"', content, re.MULTILINE)
        return match.group(1) if match else None
    except FileNotFoundError:
        return None


def extract_version_webworker():
    """Extract version from webworker.js wheel path."""
    try:
        content = Path("docs/lab/webworker.js").read_text()
        match = re.search(r'ridehail-([0-9.]+)-py3-none-any\.whl', content)
        return match.group(1) if match else None
    except FileNotFoundError:
        return None


def main():
    """Check version consistency."""
    versions = {
        "pyproject.toml": extract_version_pyproject(),
        "ridehail/__init__.py": extract_version_init(),
        "docs/lab/webworker.js": extract_version_webworker(),
    }

    print("Version check:")
    for source, version in versions.items():
        status = version or "NOT FOUND"
        print(f"  {source:30} {status}")

    # Check all versions match
    unique_versions = set(v for v in versions.values() if v)

    if len(unique_versions) == 0:
        print("\n❌ ERROR: No versions found")
        return 1
    elif len(unique_versions) > 1:
        print(f"\n❌ ERROR: Version mismatch: {unique_versions}")
        return 1
    else:
        print(f"\n✓ All versions match: {unique_versions.pop()}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
