"""
The web lab's light/dark theme (claude/dark-mode-spec.md) keeps every colour
in two places: the token block at the top of docs/lab/style.css, and the
per-theme THEME_COLORS tables in docs/lab/js/constants.js (for canvas code,
which can't use CSS tokens). These tests keep colour values from creeping
back in anywhere else, and keep the two places, and the terminal palette,
in step. They read the source files, so they need neither a browser nor
Pyodide.

A line that deliberately keeps a fixed colour in both themes (an icon detail,
say) is marked with a "theme-exempt" comment.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "docs" / "lab"

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNCTION = re.compile(r"\b(?:rgba?|hsla?)\((?!\$)")
# All 148 CSS named colours (longest first, so "lightgrey" isn't read as
# "grey"). "transparent" and "currentColor" are not colours of their own.
CSS_COLOUR_NAMES = """
    lightgoldenrodyellow mediumspringgreen mediumaquamarine
    mediumslateblue mediumturquoise mediumvioletred blanchedalmond
    cornflowerblue darkolivegreen lightslategray lightslategrey
    lightsteelblue mediumseagreen darkgoldenrod darkslateblue
    darkslategray darkslategrey darkturquoise lavenderblush
    lightseagreen palegoldenrod paleturquoise palevioletred
    rebeccapurple antiquewhite darkseagreen lemonchiffon lightskyblue
    mediumorchid mediumpurple midnightblue darkmagenta deepskyblue
    floralwhite forestgreen greenyellow lightsalmon lightyellow
    navajowhite saddlebrown springgreen yellowgreen aquamarine
    blueviolet chartreuse darkorange darkorchid darksalmon darkviolet
    dodgerblue ghostwhite lightcoral lightgreen mediumblue papayawhip
    powderblue sandybrown whitesmoke aliceblue burlywood cadetblue
    chocolate darkgreen darkkhaki firebrick gainsboro goldenrod
    indianred lawngreen lightblue lightcyan lightgray lightgrey
    lightpink limegreen mintcream mistyrose olivedrab orangered
    palegreen peachpuff rosybrown royalblue slateblue slategray
    slategrey steelblue turquoise cornsilk darkblue darkcyan darkgray
    darkgrey deeppink honeydew lavender moccasin seagreen seashell
    crimson darkred dimgray dimgrey fuchsia hotpink magenta oldlace
    skyblue thistle bisque indigo maroon orange orchid purple salmon
    sienna silver tomato violet yellow azure beige black brown coral
    green ivory khaki linen olive wheat white aqua blue cyan gold gray
    grey lime navy peru pink plum snow teal red tan
""".split()
NAMED = re.compile(r"(?<![\w-])(?:" + "|".join(CSS_COLOUR_NAMES) + r")(?![\w-])", re.I)


def _strip_css_comments(text):
    # Keep the newlines so line numbers survive
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)


def _css_outside_token_block():
    text = (LAB / "style.css").read_text()
    begin = text.index("/* @theme-tokens-begin */")
    end = text.index("/* @theme-tokens-end */")
    blanked = "\n" * text[begin:end].count("\n")
    return _strip_css_comments(text[:begin] + blanked + text[end:])


# A declaration: a property name straight after "{" or ";", then its value.
# Selectors ("#id", "a:hover") never follow "{" or ";" as a bare name and colon.
DECLARATION = re.compile(r"[{;]\s*([-a-zA-Z]+)\s*:\s*([^;{}]+)")


def test_css_colours_only_in_token_block():
    """style.css writes colours only as tokens; values live in the token block."""
    text = _css_outside_token_block()
    lines = (LAB / "style.css").read_text().split("\n")
    offenders = []
    for match in DECLARATION.finditer(text):
        value = match[2]
        if HEX.search(value) or FUNCTION.search(value) or NAMED.search(value):
            number = text.count("\n", 0, match.start(2)) + 1
            if "theme-exempt" not in lines[number - 1]:
                offenders.append(f"style.css:{number}: {lines[number - 1].strip()}")
    assert not offenders, "Colour literals outside the token block:\n" + "\n".join(
        offenders
    )


def _js_files():
    for path in sorted(LAB.glob("*.js")) + sorted((LAB / "js").glob("*.js")):
        yield path
    yield from sorted((LAB / "modules").glob("*.js"))


def test_js_colours_only_in_theme_tables():
    """Canvas and chart code reads colours from THEME_COLORS (via themeColor)."""
    offenders = []
    for path in _js_files():
        if path.name == "constants.js":
            continue
        for number, line in enumerate(path.read_text().split("\n"), 1):
            if "theme-exempt" in line:
                continue
            code = line.split("//")[0]
            if code.lstrip().startswith("*"):
                continue  # inside a /** ... */ comment
            strings = re.findall(r"([\"'`])(.*?)\1", code)
            if any(HEX.search(s) for _, s in strings) or FUNCTION.search(code):
                offenders.append(f"{path.relative_to(LAB)}:{number}: {line.strip()}")
    assert not offenders, "Colour literals outside THEME_COLORS:\n" + "\n".join(
        offenders
    )


def _theme_colors():
    """THEME_COLORS from js/constants.js, as {theme: {name: value}}."""
    text = (LAB / "js" / "constants.js").read_text()
    body = text[text.index("export const THEME_COLORS") :]
    tables = {}
    for theme in ("light", "dark"):
        block = re.search(rf"^  {theme}: \{{(.*?)^  \}}", body, re.S | re.M)[1]
        tables[theme] = dict(
            re.findall(r"^\s+([A-Z0-9_]+): (\"[^\"]*\"|\[[^\]]*\])", block, re.M)
        )
        tables[theme] = {k: v.strip('"') for k, v in tables[theme].items()}
    return tables


def _rgb(value):
    """(r, g, b) from "#rrggbb", "rgb(r, g, b)" or "rgb(r g b)"."""
    if value.startswith("#"):
        return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
    return tuple(int(n) for n in re.findall(r"\d+", value)[:3])


def _css_token(name):
    """The (light, dark) values of a light-dark() token in style.css."""
    text = (LAB / "style.css").read_text()
    match = re.search(rf"^\s*{name}: light-dark\((.*)\);$", text, re.M)
    assert match, f"{name} not found as a light-dark() token"
    # Split on the top-level comma
    args, depth = match[1], 0
    for i, ch in enumerate(args):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            return args[:i].strip(), args[i + 1 :].strip()
    raise AssertionError(f"{name}: can't split {args}")


def test_themes_define_the_same_colours():
    """A colour missing from one theme would draw as undefined."""
    tables = _theme_colors()
    assert set(tables["light"]) == set(tables["dark"])


def test_css_domain_tokens_match_theme_colors():
    """CSS legends and labels agree with the canvas colours, in both themes."""
    tables = _theme_colors()
    pairs = {
        "--lab-p1": "P1_SOLID",
        "--lab-p2": "P2_SOLID",
        "--lab-p3": "P3_SOLID",
        "--lab-wait": "WAIT_SOLID",
        "--lab-wait-metric": "WAIT_METRIC",
        "--lab-map-core": "CORE",
        "--lab-you": "YOU",
    }
    for token, name in pairs.items():
        light, dark = _css_token(token)
        assert _rgb(light) == _rgb(tables["light"][name]), token
        assert _rgb(dark) == _rgb(tables["dark"][name]), token


def test_light_phase_colours_match_terminal_palette():
    """The light theme is the unified palette in ridehail/animation/palette.py."""
    palette = (ROOT / "ridehail" / "animation" / "palette.py").read_text()
    light = _theme_colors()["light"]
    for py_name, js_name in (
        ("P1_RGB", "P1_SOLID"),
        ("P2_RGB", "P2_SOLID"),
        ("P3_RGB", "P3_SOLID"),
        ("WAITING_RIDER_RGB", "WAIT_SOLID"),
    ):
        rgb = re.search(rf"^{py_name} = \((\d+), (\d+), (\d+)\)$", palette, re.M)
        assert tuple(int(n) for n in rgb.groups()) == _rgb(light[js_name]), js_name


def test_theme_storage_key_agrees():
    """The pre-paint script in index.html reads the key js/theme.js writes."""
    js = re.search(
        r'^const THEME_STORAGE_KEY = "([^"]+)";',
        (LAB / "js" / "theme.js").read_text(),
        re.M,
    )[1]
    html = (LAB / "index.html").read_text()
    assert f'localStorage.getItem("{js}")' in html
