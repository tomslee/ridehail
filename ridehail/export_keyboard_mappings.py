#!/usr/bin/env python3
"""
Export keyboard mappings to JSON for browser consumption.

Run this script to generate keyboard-mappings.json in the browser lab directory.
"""

import json
from pathlib import Path
from ridehail.keyboard_mappings import export_to_json


def main():
    """Export keyboard mappings to JSON file."""
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_file = project_root / "docs" / "lab" / "js" / "keyboard-mappings.json"

    # Export mappings
    mappings_data = export_to_json()

    # Write to file with pretty formatting
    with open(output_file, 'w') as f:
        json.dump(mappings_data, f, indent=2)

    print(f"✓ Keyboard mappings exported to: {output_file}")
    print(f"  Version: {mappings_data['version']}")
    print(f"  Mappings: {len(mappings_data['mappings'])}")
    print(f"  Platforms: {', '.join(mappings_data['platforms'])}")


if __name__ == "__main__":
    main()
