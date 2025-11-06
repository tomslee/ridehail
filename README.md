# Ridehail Simulation

Ridehail is a Python package for simulating and analyzing the dynamics of ride-hailing platforms, such as Uber and Lyft. The package lets you model vehicle fleets, trip demand patterns, and pricing dynamics with interactive visualizations.

The best way to get an idea of what it's about is to try it out interactively at [https://tomslee.github.io/ridehail/lab]

Full[ish] documentation is available at [https://tomslee.github.io/ridehail].

## Features

- **Flexible Simulation Engine**: Configure city size, vehicle counts, trip rates, and dispatch strategies among other variables
- **Multiple Visualization Modes**:
  - Terminal-based animations (console, map, stats) using Textual
  - Desktop matplotlib visualizations
  - Interactive browser-based visualizations with Pyodide
- **Dispatch Algorithm Comparison**: Test different vehicle assignment strategies (in progress)
- **Parameter Sweeps**: Run sequences of simulations to explore parameter spaces
- **Real-time Metrics**: Track vehicle utilization, wait times, ride times, and pricing
- **Reproducible Results**: Date-based versioning and reproducible builds

## Quick Start

### Install with uv (recommended)

uv add ridehail

Dont have `uv`? Install it with: `pip install uv` or see [uv installation docs](https://github.com/astral-sh/uv)

### Or install with pip

pip install ridehail

### Install all features (terminal + matplotlib visualizations + dev tools)

uv pip install ridehail[full]

### Run your first simulation, which just produces some text output

python -m ridehail

### Or with uv

uv run python -m ridehail

## Development install

### Prerequisites

This README assumes that you are familiar with the Windows or Linux
command line, have git installed, and have python installed.

To check you have the prerequisites:

- At the command prompt, confirm you have git installed. Your output may
  be a bit different.
  > git --version
  > git version 2.34.1.windows.1
- At the command prompt, confirm you have python installed
  > python --version
  > Python 3.9.7

Some features require python 3.8 or later.

### Clone the project and install packages

Clone the project into a directory where you will run the application.
I use the src/ directory under my home directory.

```bash
src > git clone <https://github.com/tomslee/ridehail-animation.git>
src > cd ridehail-animation
```

### Development Setup

The project uses optional dependency groups for different features. Choose the setup that matches your needs:

**Recommended: Full local development setup (terminal animations + matplotlib visualizations):**

```bash
uv sync --extra full
```

**Minimal setup (core simulation only, no animations):**

```bash
uv sync
```

**What each extra includes:**

- `terminal`: textual, textual-plotext, plotext, rich (for terminal-based animations)
- `desktop`: matplotlib, seaborn, scipy, pandas (for matplotlib visualizations)
- `dev`: ruff, pytest, textual-dev, psutil (development tools)
- `full`: All of the above

````bash
## Creating your own simulations

Each simulation is managed by a configuration file. You can either copy an
existing configuration file or generate a new one with the following
commands:

```bash
# Generate a config file with default parameters
python -m ridehail -wc my_simulation.config

# Generate a config file with custom parameters
python -m ridehail -wc my_simulation.config -cs 46 -vc 24

# Or with multiple overrides
python -m ridehail -wc custom.config -cs 20 -vc 100 -bd 5.0
````

You can call it anything you want, but the extension .config is standard.

If you edit your configuration file in a text editor you should see each
parameter has a description.

## Ridehail Lab: running a simulation in the browser

The project uses pyodide, which is brilliant, to run the python code in
the browser.

Here are instructions for running it in a local browser. You can access
a hosted version at <https://tomslee.github.io/ridehail/lab/>.

### Start a web server from the project directory:

```bash
> ./build.sh
> cd docs/lab
> python -m http.server > /dev/null 2>&1 &
```

At least, that command runs the server silently and in the background in
Linux. Just try python -m http.server in a separate console if you're on
Windows or want to see output.

Then go to <http://localhost:8000> to see the output. If there are problems
in the browser the next step is to use the browser developer tools to see
what is going on

### Set up Apache to serve the lab as default

As an alternative to running the python http server, you can run the application
from an Apache server if you have one on the machine. I'm trying this in case I want
to expose it via ngrok.

Here's three steps I did, taken from [this 'does not meet the guidelines' StackOverflow question](https://stackoverflow.com/questions/5891802/how-do-i-change-the-root-directory-of-an-apache-server):

1. sudo nano /etc/apache2/sites-available/000-default.conf

   - change DocumentRoot /var/www/html to /home/<your-name>/project-directory

2. sudo nano /etc/apache2/apache2.conf

   - change <Directory /var/www> to the same project directory

3. sudo adduser www-data $USER

   - to give permissions

4. sudo service apache2 restart

Then accessing http://\<machine-name\> should show the page.

## Development notes

### Quick Reference for Developers

**Install dependencies:**

```bash
# Full development environment (recommended)
uv sync --extra full

# After installation, run simulations:
uv run python -m ridehail your_config.config -a terminal_stats
```

**Build wheel for web distribution:**

```bash
./build_wheel.sh
# Creates minimal wheel with only numpy dependency
# Copies to docs/lab/dist/ for browser version
```

## Qt library for matplotlib animations.

I've had some problems with incompatible Qt versions that I have been unable to solve. Here is a specific case:

Error message: - "Cannot mix incompatible Qt library (5.15.3) with this library (5.15.17)".
Root Cause: You have: - System Qt5 libraries: 5.15.3 (in /usr/lib/x86_64-linux-gnu/) - PyQt5-Qt5 package: 5.15.17 (in your virtual environment)

With the terminal-based animations and web-based animations, this is not so important.
