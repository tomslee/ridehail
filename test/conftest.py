"""
Pytest configuration for ridehail simulation regression tests.
"""


def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--update-expected",
        action="store_true",
        default=False,
        help="Update expected results in config files instead of comparing",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "regression: mark test as a regression test that compares simulation results",
    )
