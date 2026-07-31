"""
Shared colour palette for the terminal animations.

This mirrors the web lab's palette (the ``colors`` map and ``WAITING_RIDER_COLOR``
in ``docs/lab/js/constants.js``) so the terminal and browser front-ends read the
same. It covers the *domain* concepts only - the three vehicle phases and the
"waiting rider" signal (trip requests / passengers waiting / wait time). Generic
UI chrome (panel borders, headers, income/price stats) deliberately keeps the
Textual theme's own semantic colours ($primary, $warning, ...) and is not
governed here.

Two forms are provided for the two rendering back-ends used by the terminal
animations:

  - ``*_HEX`` - ``"#rrggbb"`` strings, for Textual CSS (``color: ...;``). Because
    Textual CSS blocks are full of ``{ }`` braces, they can't be built with an
    f-string; use :func:`apply_palette` to substitute the ``RH_*`` tokens
    instead.
  - ``*_RGB`` - ``(r, g, b)`` tuples, for plotext charts (``color=...``).
"""

# Vehicle phase 1 - idle / available (cornflower blue).
P1_HEX = "#6495ed"
P1_RGB = (100, 149, 237)

# Vehicle phase 2 - dispatched / en route to pickup (amber).
P2_HEX = "#d78e00"
P2_RGB = (215, 142, 0)

# Vehicle phase 3 - occupied / carrying a rider (medium sea green).
P3_HEX = "#3cb371"
P3_RGB = (60, 179, 113)

# Waiting rider - trip requests / passengers waiting / wait time (muted pink).
# Matches WAITING_RIDER_COLOR in docs/lab/js/constants.js.
WAITING_RIDER_HEX = "#ed6495"
WAITING_RIDER_RGB = (237, 100, 149)


def apply_palette(css: str) -> str:
    """Substitute the ``RH_*`` colour tokens in a Textual CSS block with the
    shared palette hex values.

    Used instead of an f-string / ``str.format`` because Textual CSS is full of
    ``{ }`` rule braces that would otherwise need escaping. Callers write, e.g.,
    ``color: RH_P1_COLOR;`` in the CSS and wrap the block in ``apply_palette``.
    """
    return (
        css.replace("RH_P1_COLOR", P1_HEX)
        .replace("RH_P2_COLOR", P2_HEX)
        .replace("RH_P3_COLOR", P3_HEX)
        .replace("RH_WAIT_COLOR", WAITING_RIDER_HEX)
    )
