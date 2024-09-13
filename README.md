# Ridehail simulation

This is a personal project. You're welcome to use it but no guarantees.

# Installing

## Prerequisites

This README assumes that you are familiar with the Windows or Linux command line, have git installed, and have python installed.

To check you have the prerequisites:

- At the command prompt, confirm you have git installed. Your output may
  be a bit different.
  > git --version
  > git version 2.34.1.windows.1
- At the command prompt, confirm you have python installed
  > python --version
  > Python 3.9.7

Some features of the program require python 3.8 or later.

## Clone the project and install packages

Clone the project into a directory where you will run the application.
I use the src/ directory under my home directory.

src > git clone https://github.com/tomslee/ridehail-animation.git
src > cd ridehal-animation

You will need to install some packages used by the project. The best
practice is to create a python virtual environment for this project 
and then install the packages with the following command. I have called
the virtual environment "rhenv" and any files in there are excluded
from git by adding rhenv/ to the .gitignore file. It would be easiest
if you did the same.

```bash
    > pip install -r requirements.txt
```

# Running a simulation in the browser

The project uses pyodide, which is brilliant, to run the python code in
the browser. The code for this is in the web folder.

Here are instructions for running it in a local browser. You can access
a hosted version at https://tomslee.github.io/ridehail/lab/.

The javascript and HTML files needed for the browser are in the 
docs/lab folder of this project.

First you do have to build the ridehail package, which makes a wheel file
in the dist folder. If you have run the pip install -r requirements.txt
command above then you should have the *build* package installed.

From the root directory of the project:
```
> python -m build
> # The version number below may be different
> pip install dist/ridehail-0.0.1-py3-none-any.whl --force-reinstall
```

Then start a web server from the /web directory:

```
> cd docs/lab
> cp ../../dist/ridehail-0.0.1-py3-non-any.whl dist/
> python -m http.server > /dev/null 2>&1 &
```

At least, that command runs the server silently and in the background in
Linux. Just try python -m http.server in a separate console if you're on
Windows or want to see output.

Then go to http://localhost:8000 to see the output. If there are problems
in the browser the next step is to use the browser developer tools to see
what is going on

# Running a simulation

- Read example.config
- Make a copy of example.config, eg \<username\>.config
- Run "python run.py \<username\>.config" (or whatever you called it)
- Try making other changes to your config files

There is also a set of example files in the config directory and the walthrough directory. You can run these with, for example:

```bash
    > python run.py walkthrough/step1_map.config
```

Arguments supplied on the command line (not available for all configuration options, but for some) override those in the configuration file. You can, for example, suppress graphical display by using "-dr None" no matter what is in the configuration file. For information command line options, run

```bash
    python run.py --help
```

# Creating your own simulations

Each simulation is managed by a configuration file. You can either copy an
existing configuration file or generate a new one with the following
commands:

```bash
python run.py -wc my_simulation.config
```

You can call it anything you want, but the extension .config is standard.

If you edit your configuration file in a text editor you should see each
parameter has a description.

# Documentation

There are notes on some of the background to this project in the _doc_ folder:

- [Background](docs/background.md)
- [Cities](docs/cities.md)
- [Benchmark](docs/benchmark.md)
- [Notes](docs/notes.md)

```

```
