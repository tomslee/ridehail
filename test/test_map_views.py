"""
Tests for the web lab's map views (docs/lab/maps/<name>.json).

A view is generated outside this repository (ridehail-toronto), so these
check the files we serve: each loads, its lookup table has the size its
header claims, its roll puts the city core where the generator pinned it, and
no lattice cell is folded (a fold would draw roads crossing each other). And
the names agree: every view the map's toggle offers, and every city preset's
map view, has a file.
"""

import json
import re
from pathlib import Path

import numpy as np
import pytest

from ridehail.atom import City
from ridehail.presets import CITY_PRESETS

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "docs" / "lab"
MAPS = LAB / "maps"
VIEW_FORMAT = 1  # VIEW_FORMAT in docs/lab/modules/map-view.js


def view_names():
    return sorted(path.stem for path in MAPS.glob("*.json"))


@pytest.fixture(params=view_names())
def view(request):
    return json.loads((MAPS / f"{request.param}.json").read_text())


def lattice(view):
    n = view["city_size"] * view["resolution"] + 1
    return np.array(view["lattice"]).reshape(n, n, 2)


def test_there_are_views():
    assert view_names()


def test_format(view):
    assert view["format"] == VIEW_FORMAT


def test_lattice_size(view):
    n = view["city_size"] * view["resolution"] + 1
    assert len(view["lattice"]) == n * n * 2


def test_no_folded_cells(view):
    """Every cell is a convex quadrilateral: each of its 4 corners turns the
    same way (checking one corner per cell misses a cell flattened at
    another, which the file's rounded coordinates can flip)."""
    p = lattice(view)
    corners = [p[:-1, :-1], p[:-1, 1:], p[1:, 1:], p[1:, :-1]]
    for k in range(4):
        prev, cur, nxt = corners[k - 1], corners[k], corners[(k + 1) % 4]
        e1, e2 = nxt - cur, prev - cur
        cross = e1[..., 0] * e2[..., 1] - e1[..., 1] * e2[..., 0]
        assert (cross > 0).all(), f"corner {k}: {(cross <= 0).sum()} cells"


def test_inside_declared_size(view):
    p = lattice(view)
    assert p.min() >= -0.01
    assert (p.max(axis=(0, 1)) <= np.array(view["size"]) + 0.01).all()


def test_roll_matches_core(view):
    """The roll moves the core's lower bound to the bottom edge of the display."""
    city = City(view["city_size"])
    low, _ = city.core_bounds()
    assert view["roll"] == [0, low]


def test_toggle_views_have_files():
    """The map's Grid | ... toggle names the views the page loads."""
    html = (LAB / "components" / "experiment-tab.html").read_text()
    offered = set(re.findall(r'data-map-view="([^"]+)"', html))
    assert offered, "the map view toggle offers no view"
    assert offered <= set(view_names())


def test_city_preset_views_have_files():
    for name, preset in CITY_PRESETS.items():
        if preset.get("map_view"):
            assert preset["map_view"] in view_names(), name


def test_views_are_not_package_data():
    """Map views are web assets: they stay out of the Python package."""
    assert not (ROOT / "ridehail" / "maps").exists()
    build = (ROOT / "build.sh").read_text()
    assert "--exclude='maps/'" in build


# The web lab's side (docs/lab/worker.py): the real-city presets it sends the
# browser with the "Pyodide loaded" message
def _worker():
    from test_presets import _load_worker_module

    return _load_worker_module()


def test_worker_city_presets():
    from ridehail.presets import CITY_PRESET_NAMES, get_preset

    presets = _worker().get_city_presets()
    assert set(presets) == set(CITY_PRESET_NAMES)
    toronto = presets["toronto-2026"]
    assert toronto["mapView"] == "toronto"
    assert toronto["scale"] == "city"
    assert toronto["title"] == "Toronto 2026"
    python = get_preset("toronto-2026")
    assert toronto["settings"]["citySize"] == python["city_size"]
    assert toronto["settings"]["vehicleCount"] == python["vehicle_count"]
    assert toronto["settings"]["requestRate"] == python["base_demand"]
    # Carried although no control shows it: the calibration depends on it
    assert toronto["settings"]["minTripDistance"] == python["min_trip_distance"]
