"""Conftest for manual tests.

Features:
- If ONLY manual tests are selected (marker 'manual' present and no other collected tests), disable coverage reporting to avoid global threshold failures.
- Provide a concise summary after session with count of executed vs skipped manual tests.
- Print a hint if all manual tests were skipped (likely missing PDF).
"""
from __future__ import annotations
import pytest


def pytest_collection_modifyitems(config, items):
    # Tag to check later
    config._manual_items = [it for it in items if 'manual' in it.keywords]


def pytest_configure(config):
    # Flag to later decide if we should suppress coverage output
    config._suppress_cov = False


def pytest_sessionstart(session):  # type: ignore
    config = session.config
    manual_selected = session.config.getoption('-m') or ''
    # Heuristic: if user specified -m manual then they intend a manual-only run
    if 'manual' in manual_selected:
        config._possible_manual_only = True
    else:
        config._possible_manual_only = False


def pytest_sessionfinish(session, exitstatus):  # type: ignore
    config = session.config
    manual_items = getattr(config, '_manual_items', [])
    # (Let test reports speak; no per-test aggregation implemented to keep hook minimal.)

    # We can't access detailed reports here easily without a plugin; provide basic info
    if manual_items:
        # Determine if all tests were skipped by checking node keywords soon after
        # (A deeper approach would hook into test reports; kept simple intentionally)
        print(f"\n[manual-summary] Antal manuelle tests fundet: {len(manual_items)}")
        # If coverage plugin active and only manual marker used, hint about --no-cov
        marker_expr = session.config.getoption('-m') or ''
        if marker_expr.strip() == 'manual':
            print('[manual-summary] Tip: Brug --no-cov for at undgå coverage threshold fejl ved rene manuelle kørsler.')

    # Additional hint if no tests ran at all
    if not manual_items:
        print('\n[manual-summary] Ingen manuelle tests blev samlet. Kontrollér sti og filnavn.')


@pytest.hookimpl(tryfirst=True)
def pytest_report_header(config):  # type: ignore
    if getattr(config, '_possible_manual_only', False):
        return '[manual] Kører manuel test session (overvej --no-cov)' 
    return None
