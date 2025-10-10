# Ridehail simulation

This is a personal project. You're welcome to use it but no guarantees.

## Installing

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

Some features of the program require python 3.8 or later.

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

**Terminal animations only (console, map, stats using Textual):**
```bash
uv sync --extra terminal
```

**Matplotlib visualizations only:**
```bash
uv sync --extra desktop
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

**Note:** If you try to run terminal animations (e.g., `-as terminal_stats`, `-as terminal_map`, `-as console`) without installing the `terminal` extra, you'll see a fallback warning and matplotlib will be used instead.

## Running a simulation (desktop)

- Read example.config
- Make a copy of example.config, eg \<username\>.config
- Run "python run.py \<username\>.config" (or whatever you called it)
- Try making other changes to your config files

There is also a set of example files in the config directory and the
walkthrough directory. You can run these with, for example:

```bash
> python run.py walkthrough/step1_map.config
```

or

```bash
> uv run run.py walkthrough/step1_map.config
```

Arguments supplied on the command line (not available for all configuration
options, but for some) override those in the configuration file. You can, for
example, suppress graphical display by using "-dr None" no matter what is
in the configuration file. For information command line options, run

```bash
> python run.py --help
```

## Creating your own simulations

Each simulation is managed by a configuration file. You can either copy an
existing configuration file or generate a new one with the following
commands:

```bash
python run.py -wc my_simulation.config
```

You can call it anything you want, but the extension .config is standard.

If you edit your configuration file in a text editor you should see each
parameter has a description.

## Ridehail Lab: running a simulation in the browser

The project uses pyodide, which is brilliant, to run the python code in
the browser. The code for this is in the web folder.

Here are instructions for running it in a local browser. You can access
a hosted version at <https://tomslee.github.io/ridehail/>.

The javascript and HTML files needed for the browser are in the
./docs/lab folder of this project.

First you do have to build the ridehail package, which makes a wheel file
in the dist folder.

### Building the Wheel Package

Build the ridehail package as a wheel file. The build script automatically handles versioning and copies the wheel to the web distribution directory:

```bash
./build_wheel.sh
```

Or manually:
```bash
uv build --wheel --package ridehail
```

**Important:** The wheel only includes core dependencies (numpy) in `Requires-Dist`. Optional dependencies (`terminal`, `desktop`, `dev`) are stored as metadata with `extra ==` markers, so they are NOT installed unless explicitly requested.

This means:
- **Web/Pyodide:** Only numpy is required (Pyodide already includes it)
- **Local development:** Install with `uv sync --extra terminal` or `--extra full` to get animation dependencies

You can verify the wheel's dependencies:
```bash
python3 -c "import zipfile; z = zipfile.ZipFile('dist/ridehail-0.1.0-py3-none-any.whl'); print(z.read('ridehail-0.1.0.dist-info/METADATA').decode())" | grep Requires-Dist
```

### Start a web server from the project directory:

```bash
> cp dist/ridehail-0.0.1-py3-non-any.whl docs/lab/dist/
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
uv run python run.py your_config.config -as terminal_stats
```

**Build wheel for web distribution:**
```bash
./build_wheel.sh
# Creates minimal wheel with only numpy dependency
# Copies to docs/lab/dist/ for browser version
```

**Export keyboard mappings (after modifying shortcuts):**
```bash
python ridehail/export_keyboard_mappings.py
```

### Keyboard mappings export

The project uses a unified keyboard mapping system across desktop (terminal/Textual) and browser platforms. If you modify keyboard shortcuts in `ridehail/keyboard_mappings.py`, you must export them to JSON for the browser:

```bash
python ridehail/export_keyboard_mappings.py
```

This generates `docs/lab/js/keyboard-mappings.json` which the browser interface loads. See `docs/keyboard-unification-summary.md` for details on the keyboard mapping system.

### Material Design Lite warnings

The project uses the Material Design Lite UI framework. Material Design Lite is no longer
supported by Google because of course it isn't. MDL produces a set of errors in the developer tools console of the form "Added non-passive event listener...". Moving from
MDL to Material Design 3 looks like a big job and who needs it? I'd rather ignore
the warnings.

## More documentation

There are notes on some of the background to this project in the _doc_ folder:

- [Background](docs/background.md)
- [Cities](docs/cities.md)
- [Benchmark](docs/benchmark.md)
- [Notes](docs/notes.md)

## Qt library for matplotlib animations.

I've had some problems with incompatible Qt versions. Here is a specific case:

Error message: - "Cannot mix incompatible Qt library (5.15.3) with this library (5.15.17)".
Root Cause: You have: - System Qt5 libraries: 5.15.3 (in /usr/lib/x86_64-linux-gnu/) - PyQt5-Qt5 package: 5.15.17 (in your virtual environment)
