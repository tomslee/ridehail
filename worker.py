import sys
import numpy as np


def do_something(x, y):
    z = x + y
    return (z)


def return_sin(x):
    return ([x, np.sin(x)])


def return_sin_array(offset):
    x = np.linspace(0, 2 * np.pi, 100)
    y = np.sin(x + offset)
    # result = [{"x": x, "y": y} for x, y in zip(x, y)]
    return ([offset, x, y])


def main():
    return_sin(0)


if __name__ == '__main__':
    main()
