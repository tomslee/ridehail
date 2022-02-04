# Ridehail simulation

This is a personal project. You're welcome to use it but no guarantees.

# Installing

## Prerequisites

This README assumes that you are familiar with the Windows or Linux command line, have git installed, and have python installed. I have used the [anaconda distribution](https://www.anaconda.com/products/individual).

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

You will need to install some packages used by the project. I can't lead
you through all the variations here, but you can try one of the
following and Google if you get stuck:

- If you are using Anaconda python on Linux:

```bash
    > conda create --name ridehail --file conda-spec-file-linux.txt
```

- If youa re using Anaconda python on Windows:

```bash
    > conda create --name ridehail --file conda-spec-file-windows.txt
```

- Another thing to try

```bash
    > pip install -r requirements.txt
```

# Running a simulation

- Read example.config
- Make a copy of example.config, eg \<username\>.config
- Run "python ridehail.py \<username\>.config" (or whatever you called it)
- Try making other changes to your config files

There is also a set of example files in the config directory and the walthrough directory. You can run these with, for example:

```bash
    > python ridehail.py walkthrough/step1_map.config
```

Arguments supplied on the command line (not available for all configuration options, but for some) override those in the configuration file. You can, for example, suppress graphical display by using "-dr None" no matter what is in the configuration file. For information command line options, run

```bash
    python ridehail.py --help
```

# Creating your own simulations

Each simulation is managed by a configuration file. You can either copy an
existing configuration file or generate a new one with the following
commands:

```bash
python ridehail.py -wc my_simulation.config
```

You can call it anything you want, but the extension .config is standard.

If you edit your configuration file in a text editor you should see each
parameter has a description.

# Documentation

There are notes on some of the background to this project in the _doc_ folder:

- [Background](doc/background.md)
- [Cities](doc/cities.md)
- [Benchmark](doc/benchmark.md)
- [Notes](doc/notes.md)

```

```
