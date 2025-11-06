# Installation

Ridehail can be installed via pip or uv, with optional dependencies for different feature sets.

## Prerequisites

- **Python**: 3.12 or later
- **Operating System**: Linux, macOS, or Windows

## Quick Install

### Using pip (Recommended)

```bash
# Install ridehail with terminal and browser animations
pip install ridehail

# Or install with desktop visualizations (matplotlib)
pip install ridehail[desktop]

# Or install everything (desktop + development tools)
pip install ridehail[full]
```

### Using uv (Recommended for Developers)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install uv if you don't have it
pip install uv

# Install ridehail
uv pip install ridehail

# Or with desktop visualizations
uv pip install ridehail[desktop]
```

## What's Included

### Base Installation

```bash
pip install ridehail
```

**Includes everything you need to get started** (~30MB):

- Core simulation engine (`numpy`)
- Terminal animations (`textual`, `plotext`, `rich`)
- Browser-based animations (uses standard library only)

**Available animation modes:**

- `terminal_map` - Real-time vehicle map in terminal
- `terminal_stats` - Real-time statistical charts
- `console` - Text-based console animation
- `terminal_sequence` - Parameter sweep visualization
- `web_map` - Interactive browser map (auto-opens)
- `web_stats` - Interactive browser charts (auto-opens)

### Desktop Visualizations (Optional)

```bash
pip install ridehail[desktop]
```

**Adds matplotlib stack** (~115MB additional):

- `matplotlib` - Desktop plotting library
- `seaborn` - Statistical visualization
- `scipy` - Scientific computing
- `pandas` - Data analysis

**Additional animation modes:**

- `map` - Matplotlib vehicle map
- `stats` - Matplotlib statistical charts

**Use when:**

- Need publication-quality figures
- Want to export high-resolution images
- Prefer traditional matplotlib interface

### Full Installation (All Features)

```bash
pip install ridehail[full]
```

Includes base installation + desktop + development tools.

**Additional tools:**

- `textual-dev` - Textual development tools
- `ruff` - Fast Python linter/formatter
- `pytest` - Testing framework
- `psutil` - System monitoring

## Development Installation

For contributing to the project:

```bash
# Clone the repository
git clone https://github.com/tomslee/ridehail.git
cd ridehail

# Install with development dependencies using uv
uv sync --extra full

# Or with pip
pip install -e ".[full,dev]"
```

**Development extras include:**

- `ruff` - Fast Python linter and formatter
- `pytest` - Testing framework
- `textual-dev` - Textual development tools
- `psutil` - System monitoring

## Verifying Installation

After installation, verify everything works:

```bash
# Check version
python -m ridehail --version

# View available options
python -m ridehail --help

# Create a test configuration
python -m ridehail -wc test.config -cs 8 -vc 30

# Try terminal animation
python -m ridehail test.config -a terminal_map

# Try browser animation (opens automatically)
python -m ridehail test.config -a web_map
```

All animation modes should work immediately after base installation except `map` and `stats` (which require `[desktop]` extra).

## Troubleshooting

### Desktop Animations Not Available

If you try to use `map` or `stats` animations and get an error about missing matplotlib:

```bash
# Install desktop extras
pip install ridehail[desktop]
```

Terminal and browser animations work with base install only.

### Qt Library Conflicts (Linux Desktop Visualizations)

If you encounter Qt library version conflicts with matplotlib:

```
Cannot mix incompatible Qt library (5.15.3) with this library (5.15.17)
```

**Solution:** Use a virtual environment to isolate Qt dependencies:

```bash
# Create fresh virtual environment
python -m venv ridehail_env
source ridehail_env/bin/activate  # On Windows: ridehail_env\Scripts\activate

# Install ridehail
pip install ridehail[desktop]
```

### Python Version

Ridehail requires Python 3.12+. Check your version:

```bash
python --version
```

If you need to install Python 3.12+, visit [python.org](https://www.python.org/downloads/).

## Upgrading

To upgrade to the latest version:

```bash
# With pip
pip install --upgrade ridehail

# With uv
uv pip install --upgrade ridehail

# Or with desktop extras
pip install --upgrade ridehail[desktop]
```

## Browser Version (No Installation)

You can also use Ridehail without any installation via the browser-based lab:

**[https://tomslee.github.io/ridehail/lab/](lab/index.html)**

The browser version runs the full Python simulation engine client-side using Pyodide WebAssembly.

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first simulation
- [Configuration Overview](configuration/overview.md) - Learn about parameters
- [Animations Guide](animations/overview.md) - Explore visualization modes
