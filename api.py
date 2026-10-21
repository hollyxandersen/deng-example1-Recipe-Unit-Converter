"""ExactCup ingredient reference data: local cache + safe refresh."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

CACHE_FILE = Path(__file__).with_name("ingredients.json")
API_URL = "https://exactcup.github.io/api/v1/ingredients.json"
CACHE_MAX_AGE_DAYS = 30


def get_cache_status():
    """Report *local download* age, not the API publisher's update date."""
    if not CACHE_FILE.exists():
        return {"exists": False, "cached_at": None, "age_days": None, "stale": True}

    modified_at = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - modified_at
    return {
        "exists": True,
        "cached_at": modified_at,
        "age_days": max(0, age.days),
        "stale": age >= timedelta(days=CACHE_MAX_AGE_DAYS),
    }


def _read_cached_data():
    with CACHE_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    _validate_data(data)
    return data


def _validate_data(data):
    if not isinstance(data, dict) or not isinstance(data.get("ingredients"), list):
        raise ValueError("ExactCup response does not contain an ingredients list")
    if not data["ingredients"]:
        raise ValueError("ExactCup response contains no ingredients")


def _fetch_and_cache():
    response = requests.get(API_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    _validate_data(data)

    # Write to a temporary file first: failed/interrupted writes cannot
    # overwrite a good cache. os.replace is atomic on the same filesystem.
    fd, temporary_path = tempfile.mkstemp(prefix="ingredients_", suffix=".json", dir=CACHE_FILE.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        os.replace(temporary_path, CACHE_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return data


def load_ingredient_data(force_refresh=False):
    """Load cached reference data without automatic refresh.

    Fetch once when no cache exists. Explicit refresh is permitted only
    when the existing cache is at least 30 days old.
    """
    status = get_cache_status()

    if status["exists"] and not (force_refresh and status["stale"]):
        print("Loading ExactCup ingredient data from cache")
        return _read_cached_data()

    try:
        print("Fetching ExactCup ingredient data")
        return _fetch_and_cache()
    except (requests.RequestException, ValueError, OSError) as exc:
        raise RuntimeError(f"Could not refresh ExactCup data: {exc}") from exc
