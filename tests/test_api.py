"""
Tests for ExactCup ingestion and cache behaviour.

Uses temporary cache files and mocked HTTP responses so tests
run without network access or changes to the real cache.
"""

import json
import os
import time
from unittest.mock import Mock

import pytest
import requests

import api


# ---------------------------------------------------------
# FIXTURES AND HELPERS
# ---------------------------------------------------------

@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    """Redirect cache operations to an isolated temporary path."""
    path = tmp_path / "ingredients.json"
    monkeypatch.setattr(api, "CACHE_FILE", path)
    return path


@pytest.fixture(autouse=True)
def api_get(monkeypatch):
    """Prevent real HTTP requests and fail on unexpected API calls."""
    mocked_get = Mock(
        side_effect=AssertionError("Unexpected API request")
    )
    monkeypatch.setattr(api.requests, "get", mocked_get)
    return mocked_get


def write_cache(path, days_old):
    """Create a valid test cache with a simulated download age."""
    data = {"ingredients": [{"slug": "cached-flour"}]}
    path.write_text(json.dumps(data), encoding="utf-8")

    # Cache age is determined from the file's modification time.
    modified_at = time.time() - days_old * 24 * 60 * 60
    os.utime(path, (modified_at, modified_at))

    return data


# ---------------------------------------------------------
# CACHE STATUS AND REFRESH POLICY
# ---------------------------------------------------------

def test_missing_cache_status(cache_file):
    """Report a missing cache without attempting a download."""
    assert api.get_cache_status() == {
        "exists": False,
        "cached_at": None,
        "age_days": None,
        "stale": True,
    }


@pytest.mark.parametrize("days_old, force_refresh", [
    (1, False),   # Reuse a fresh cache.
    (31, False),  # Do not automatically refresh an old cache.
    (1, True),    # Block manual refresh before the age threshold.
])
def test_existing_cache_does_not_trigger_request(
    cache_file, api_get, days_old, force_refresh
):
    """Use cached data unless an eligible refresh is requested."""
    expected = write_cache(cache_file, days_old)

    result = api.load_ingredient_data(
        force_refresh=force_refresh
    )

    assert result == expected
    api_get.assert_not_called()


# ---------------------------------------------------------
# SUCCESSFUL DOWNLOADS
# ---------------------------------------------------------

@pytest.mark.parametrize("existing_cache", [False, True])
def test_download_saves_valid_data(
    cache_file, api_get, existing_cache
):
    """Save valid data on first download or eligible manual refresh."""
    if existing_cache:
        write_cache(cache_file, days_old=31)

    downloaded = {"ingredients": [{"slug": "new-flour"}]}
    response = Mock()
    response.json.return_value = downloaded

    # Allow the expected request and supply a successful response.
    api_get.side_effect = None
    api_get.return_value = response

    result = api.load_ingredient_data(
        force_refresh=existing_cache
    )

    assert result == downloaded
    assert json.loads(
        cache_file.read_text(encoding="utf-8")
    ) == downloaded

    api_get.assert_called_once_with(api.API_URL, timeout=15)
    response.raise_for_status.assert_called_once()


# ---------------------------------------------------------
# FAILED REFRESHES
# ---------------------------------------------------------

def test_network_failure_preserves_old_cache(
    cache_file, api_get
):
    """Report a timeout without changing the existing cache."""
    write_cache(cache_file, days_old=31)
    original_bytes = cache_file.read_bytes()

    api_get.side_effect = requests.Timeout("Simulated timeout")

    with pytest.raises(
        RuntimeError,
        match="Could not refresh ExactCup data",
    ):
        api.load_ingredient_data(force_refresh=True)

    assert cache_file.read_bytes() == original_bytes


@pytest.mark.parametrize("invalid_data", [
    {},                    # Missing ingredients list.
    {"ingredients": []},   # Empty ingredients list.
])
def test_invalid_response_preserves_old_cache(
    cache_file, api_get, invalid_data
):
    """Reject invalid downloaded data without replacing the cache."""
    write_cache(cache_file, days_old=31)
    original_bytes = cache_file.read_bytes()

    response = Mock()
    response.json.return_value = invalid_data
    api_get.side_effect = None
    api_get.return_value = response

    with pytest.raises(
        RuntimeError,
        match="Could not refresh ExactCup data",
    ):
        api.load_ingredient_data(force_refresh=True)

    assert cache_file.read_bytes() == original_bytes