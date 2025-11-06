# Installation

Ridehail can be installed via pip or uv, with optional dependencies for different feature sets.

## Prerequisites

- **Python**: 3.12 or later
- **Operating System**: Linux, macOS, or Windows

## Quick Install

### Using pip (Recommended for Users)

```bash
# Install with terminal animation support (most popular)
pip install ridehail[terminal]

# Or install with all features
pip install ridehail[full]
```

### Using uv (Recommended for Developers)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install uv if you don't have it
pip install uv

# Install ridehail with terminal support
uv pip install ridehail[terminal]

# Or install with all features
uv pip install ridehail[full]
```

## Installation Options

The package provides several optional dependency groups for different use cases:

### Terminal Animations (Recommended)

```bash
pip install ridehail[terminal]
```

**Includes:**

- `textual` - Modern terminal UI framework
- `textual-plotext` - Terminal plotting integration
- `plotext` - Terminal-based plotting library
- `rich` - Rich text and formatting in the terminal

**Provides access to:**

- `terminal_map` - Real-time vehicle map in terminal
- `terminal_stats` - Real-time statistical charts
- `console` - Text-based console animation
- `terminal_sequence` - Parameter sweep visualization

### Desktop Visualizations

```bash
pip install ridehail[desktop]
```

**Includes:**

- `matplotlib` - Desktop plotting library
- `seaborn` - Statistical visualization
- `scipy` - Scientific computing
- `pandas` - Data analysis

**Provides access to:**

- `map` - Matplotlib vehicle map
- `stats` - Matplotlib statistical charts

### Full Installation (All Features)

```bash
pip install ridehail[full]
```

Includes all terminal, desktop, and development dependencies.

### Minimal Installation (Core Only)

```bash
pip install ridehail
```

Installs only the core simulation engine with no visualization dependencies. Useful for:

- Running simulations programmatically
- Headless servers
- Minimal Docker images
- CI/CD environments

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

# Run a quick simulation
python -m ridehail test.config -a terminal_map
```

## Troubleshooting

### Missing Dependencies Warning

If you see a message like:

```
Warning: Textual dependencies not found. Falling back to matplotlib animation.
```

This means you tried to use terminal animations without installing the `terminal` extra. Install it:

```bash
pip install ridehail[terminal]
```

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
pip install --upgrade ridehail[terminal]

# With uv
uv pip install --upgrade ridehail[terminal]
```

## Browser Version (No Installation)

You can also use Ridehail without any installation via the browser-based lab:

**[https://tomslee.github.io/ridehail/lab/](lab/index.html)**

The browser version runs the full Python simulation engine client-side using Pyodide WebAssembly.

## Next Steps

- [Quick Start Guide](quickstart.md) - Run your first simulation
- [Configuration Overview](configuration/overview.md) - Learn about parameters
- [Animations Guide](animations/overview.md) - Explore visualization modes
