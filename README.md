
# Table of Contents

1.  [Ridehail simulation](#org09342bd)
2.  [Running a simulation](#orgc571fba)
3.  [Documentation](#orgad7fb1a)


<a id="org09342bd"></a>

# Ridehail simulation

This is a personal project. You&rsquo;re welcome to use it but don&rsquo;t expect anything.


<a id="orgc571fba"></a>

# Running a simulation

-   Read example.config
-   Make a copy of example.config, eg <username>.config
-   Run &ldquo;python ridehail.py -@ <username>.config&rdquo; (or whatever you called it)
-   Try making other changes to your config files

There is also a set of example files in the config directory. You can run these with, for example:

    python ridehail.py -@ config/lesson_1.config

Arguments supplied on the command line (not available for all configuration options, but for some) override those in the configuration file. You can, for example, suppress graphical display by using &ldquo;-dr None&rdquo; no matter what is in the configuration file. For information command line options, run 

    python ridehail.py --help


<a id="orgad7fb1a"></a>

# Documentation

There are notes on some of the background to this project in the *doc* folder:

-   [Background](doc/background.md)
-   [Benchmark](doc/benchmark.md)
-   [Notes](doc/notes.md)

