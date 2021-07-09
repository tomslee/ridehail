# Ridehail simulation

This is a personal project. You're welcome to use it but don't expect anything.

# Running a simulation

- Read example.config
- Make a copy of example.config, eg \<username\>.config
- Run "python ridehail.py \<username\>.config" (or whatever you called it)
- Try making other changes to your config files

There is also a set of example files in the config directory. You can run these with, for example:

```bash
    python ridehail.py config/lesson_1.config
```

Arguments supplied on the command line (not available for all configuration options, but for some) override those in the configuration file. You can, for example, suppress graphical display by using "-dr None" no matter what is in the configuration file. For information command line options, run

```bash
    python ridehail.py --help
```

# Documentation

There are notes on some of the background to this project in the _doc_ folder:

- [Background](doc/background.md)
- [Cities](doc/cities.md)
- [Benchmark](doc/benchmark.md)
- [Notes](doc/notes.md)

```

```
