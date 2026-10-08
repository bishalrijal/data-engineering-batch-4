"""
Shared pytest fixtures for the Week 5 assignment.

Every test builds its own small DataFrame from `good_facts` and breaks exactly one
thing in it. No test needs a database. If a test needs Postgres to run, it is an
integration test, not a unit test, and it doesn't belong in this folder.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Make `import quality` / `import transform` resolve to Week5/assignment/pipeline/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))


@pytest.fixture
def good_facts() -> pd.DataFrame:
    """Four valid fact rows: two completed, one cancelled, one no_show.

    Columns and dtypes match what transform_trips_df() returns. Every check in
    quality.py must pass on this frame. Tests copy it and break one thing.
    """
    return pd.DataFrame({
        "source_trip_id":       [101, 102, 103, 104],
        "date_key":             [20250314, 20250314, 20250315, 20250316],
        "time_key":             [830, 1745, 0, 2345],
        "driver_key":           pd.array([1, 2, 1, 3], dtype="Int64"),
        "passenger_key":        pd.array([10, 11, 12, 10], dtype="Int64"),
        "pickup_location_key":  pd.array([5, 6, 7, 5], dtype="Int64"),
        "dropoff_location_key": pd.array([6, 7, 5, 8], dtype="Int64"),
        "payment_method_key":   pd.array([2, 3, 2, None], dtype="Int64"),   # no_show: no payment
        "promo_code_key":       pd.array([None, 4, None, None], dtype="Int64"),
        "trip_status":          ["completed", "completed", "cancelled", "no_show"],
        "cancelled_by":         [None, None, "passenger", None],
        "base_fare":            [18.40, 42.10, 9.75, 12.00],
        "tip_amount":           [2.50, 0.00, 0.00, 0.00],
        "discount_amount":      [0.00, 5.00, 0.00, 0.00],
        "fare_amount":          [20.90, 47.63, 9.75, 12.00],   # 42.10 * 1.25 + 0 - 5 = 47.625 -> 47.63 (half-up)
        "distance_km":          [7.20, 21.85, 3.10, 4.40],
        "duration_minutes":     [18.5, 52.0, None, None],
        "driver_rating":        [4.5, None, None, None],
        "passenger_rating":     [5.0, 4.0, None, None],
        "surge_multiplier":     [1.00, 1.25, 1.00, 1.00],
        "requested_at":         pd.to_datetime([
            "2025-03-14 08:37:00", "2025-03-14 17:52:10",
            "2025-03-15 00:00:00", "2025-03-16 23:59:59",
        ]),
    })


@pytest.fixture
def empty_facts(good_facts) -> pd.DataFrame:
    """Same columns and dtypes as good_facts, zero rows: a quiet night's incremental run."""
    return good_facts.iloc[0:0]
