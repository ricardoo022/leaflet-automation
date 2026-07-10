"""Shared pytest configuration.

Gates ``@pytest.mark.e2e`` tests behind an explicit ``--run-e2e`` flag so the
suite stays green by default (live external calls cost real time / rate-limit).
Without ``--run-e2e`` every e2e-marked item is skipped during collection.
"""
from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests that hit the REAL external Lidl API + real SQLite.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests that call the REAL external Lidl API and real SQLite "
        "via a real OS subprocess (gated behind --run-e2e).",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if config.getoption("--run-e2e"):
        return

    skip_marker = pytest.mark.skip(
        reason="e2e test requires --run-e2e (hits the REAL external Lidl API)",
    )
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_marker)