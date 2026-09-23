"""Pytest configuration and fixtures."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "phase3: tests for Phase 3 (REST API) - skipped until implementation"
    )


# Skip Phase 3 tests if fastapi is not installed (not yet implemented)
pytest_plugins = []

try:
    import fastapi  # noqa: F401
except ImportError:

    def pytest_collection_modifyitems(config, items):
        """Skip Phase 3 tests if fastapi is not available."""
        skip_marker = pytest.mark.skip(reason="Phase 3 (REST API) not yet implemented")
        for item in items:
            if "test_api" in str(item.fspath) or "test_member2" in str(item.fspath):
                item.add_marker(skip_marker)
