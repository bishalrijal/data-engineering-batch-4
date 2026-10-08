"""
benchmark_transform.py
----------------------
Week 5 Assignment — provided harness for Part 1. You don't need to edit this file.

It times the class row-by-row transform (../transform.py) against your vectorized
one (pipeline/transform.py), on the real 10,000 trips and on copies of them
scaled up, and checks that your output is correct:

  1. every input trip comes out exactly once, as a fact row or as a reject
  2. the columns the class transform also produces have the same values
  3. fare_amount matches the source view v_trips to the cent, for every trip
  4. time_key matches the 15-minute rule (14:37 -> 1430)

Your module must define:

    transform_trips_df(trips: pd.DataFrame, lookups: dict) -> tuple[pd.DataFrame, pd.DataFrame]

  trips    the DataFrame from TRIPS_SQL below, as pd.read_sql returns it
  lookups  the same dict class extract_lookup_dim() returns:
           {"driver": {driver_id: driver_key, ...}, ..., "date": {date_key: True, ...}}
  returns  (facts, rejects). facts has one row per loaded trip, with the columns in
           FACT_COLUMNS. rejects has the dropped input rows plus a reject_reason column.

Run from Week5/assignment/:
    python benchmark_transform.py                     # 10k, 100k, 1M rows
    python benchmark_transform.py --scales 1 10       # 10k and 100k only
"""

import argparse
import importlib.util
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

HERE = Path(__file__).resolve().parent

FACT_COLUMNS = [
    "source_trip_id", "date_key", "time_key",
    "driver_key", "passenger_key", "pickup_location_key", "dropoff_location_key",
    "payment_method_key", "promo_code_key",
    "trip_status", "cancelled_by",
    "base_fare", "tip_amount", "discount_amount", "fare_amount",
    "distance_km", "duration_minutes",
    "driver_rating", "passenger_rating", "surge_multiplier",
    "requested_at",
]

TRIPS_SQL = """
    SELECT
        t.trip_id, t.driver_id, t.passenger_id,
        t.pickup_location_id, t.dropoff_location_id,
        t.payment_method_id, t.promo_code_id,
        t.base_fare, t.tip_amount, t.discount_amount, t.surge_multiplier,
        t.distance_km, t.status, t.requested_at, t.completed_at,
        t.driver_rating, t.passenger_rating,
        tc.cancelled_by
    FROM trips t
    LEFT JOIN trip_cancellations tc ON t.trip_id = tc.trip_id
    ORDER BY t.trip_id
"""

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger("benchmark")


def db_config(prefix):
    return dict(
        host=os.getenv(f"{prefix}_DB_HOST"),
        port=os.getenv(f"{prefix}_DB_PORT"),
        dbname=os.getenv(f"{prefix}_DB_NAME"),
        user=os.getenv(f"{prefix}_DB_USER"),
        password=os.getenv(f"{prefix}_DB_PASSWORD"),
    )


def load_module(name, path):
    """Import a .py file by path, so ../transform.py and pipeline/transform.py don't collide."""
    sys.path.insert(0, str(path.parent))   # lets the module's own flat imports resolve
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


def extract_lookups(conn):
    lookups = {}
    with conn.cursor() as cur:
        for name, id_col in [("driver", "driver_id"), ("passenger", "passenger_id"),
                             ("location", "location_id"), ("payment_method", "payment_method_id"),
                             ("promo_code", "promo_code_id")]:
            cur.execute(f"SELECT {id_col}, {name}_key FROM dim_{name}")
            lookups[name] = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT date_key FROM dim_date")
        lookups["date"] = {r[0]: True for r in cur.fetchall()}
    return lookups


def scale_rows(rows, k):
    """k copies of the row-by-row input, with trip_ids made unique."""
    if k == 1:
        return rows
    step = max(r["trip_id"] for r in rows)
    return [{**r, "trip_id": r["trip_id"] + i * step} for i in range(k) for r in rows]


def scale_df(df, k):
    if k == 1:
        return df
    step = df["trip_id"].max()
    return pd.concat(
        [df.assign(trip_id=df["trip_id"] + i * step) for i in range(k)],
        ignore_index=True,
    )


def timed(fn, *args):
    t0 = time.perf_counter()
    result = fn(*args)
    return result, time.perf_counter() - t0


def check(name, passed, detail):
    logger.info(f"{'PASS' if passed else 'FAIL'}  {name:<32} {detail}")
    return passed


def verify(trips_df, facts, rejects, rowwise_rows, v_fares):
    """Correctness checks on the unscaled 10k run. Returns True if all pass."""
    results = []

    missing_cols = [c for c in FACT_COLUMNS if c not in facts.columns]
    results.append(check("fact columns present", not missing_cols, f"missing: {missing_cols}" if missing_cols else "all present"))
    if missing_cols:
        return False
    results.append(check("rejects has reject_reason", "reject_reason" in rejects.columns, ""))

    out_ids = pd.concat([facts["source_trip_id"], rejects["trip_id"]])
    results.append(check(
        "every trip accounted for once",
        len(out_ids) == len(trips_df) and out_ids.is_unique and set(out_ids) == set(trips_df["trip_id"]),
        f"{len(trips_df)} in, {len(facts)} facts + {len(rejects)} rejects",
    ))

    # Same values as the class transform on the columns it also produces.
    # fare_amount is excluded on purpose: the class transform rounds it wrongly.
    ref = pd.DataFrame(rowwise_rows).set_index("source_trip_id")
    got = facts.set_index("source_trip_id")
    common = ref.index.intersection(got.index)
    for col in ["date_key", "driver_key", "passenger_key", "pickup_location_key", "dropoff_location_key",
                "payment_method_key", "promo_code_key", "base_fare", "tip_amount", "discount_amount",
                "surge_multiplier", "distance_km", "duration_minutes", "driver_rating", "passenger_rating"]:
        a = pd.to_numeric(ref.loc[common, col], errors="coerce").astype(float)
        b = pd.to_numeric(got.loc[common, col], errors="coerce").astype(float)
        bad = ~((a - b).abs().le(1e-9) | (a.isna() & b.isna()))
        results.append(check(f"{col} matches class", bad.sum() == 0, f"{bad.sum()} rows differ"))
    status_bad = (ref.loc[common, "status"] != got.loc[common, "trip_status"]).sum()
    results.append(check("trip_status matches source", status_bad == 0, f"{status_bad} rows differ"))

    fare = pd.to_numeric(got["fare_amount"]).astype(float)
    expected = got.index.map(v_fares).astype(float)
    fare_bad = (fare - expected).abs().gt(0.001)
    results.append(check(
        "fare_amount matches v_trips",
        fare_bad.sum() == 0,
        f"{fare_bad.sum()} of {len(got)} trips off; total off by {(fare - expected).sum():+.2f}",
    ))

    req = trips_df.set_index("trip_id").loc[got.index, "requested_at"]
    tk_expected = req.dt.hour * 100 + (req.dt.minute // 15) * 15
    tk_bad = (pd.to_numeric(got["time_key"]).astype("int64") != tk_expected).sum()
    results.append(check("time_key 15-minute rule", tk_bad == 0, f"{tk_bad} rows differ"))

    return all(results)


def main():
    parser = argparse.ArgumentParser(description="Benchmark row-by-row vs vectorized transform")
    parser.add_argument("--scales", type=int, nargs="+", default=[1, 10, 100],
                        help="multiples of the 10k source trips to time (default: 1 10 100)")
    parser.add_argument("--module", default=str(HERE / "pipeline" / "transform.py"),
                        help="path to your vectorized transform module")
    args = parser.parse_args()

    rowwise = load_module("class_transform", HERE.parent / "transform.py")
    vectorized = load_module("student_transform", Path(args.module).resolve())

    src = psycopg2.connect(**db_config("SRC"))
    dst = psycopg2.connect(**db_config("DEST"))
    cfg = db_config("SRC")
    engine = create_engine(URL.create(
        "postgresql+psycopg2", username=cfg["user"], password=cfg["password"],
        host=cfg["host"], port=cfg["port"], database=cfg["dbname"],
    ))

    with src.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(TRIPS_SQL)
        rows = cur.fetchall()
        cur.execute("SELECT trip_id, fare_amount FROM v_trips")
        v_fares = {r["trip_id"]: r["fare_amount"] for r in cur.fetchall()}
    trips_df = pd.read_sql(TRIPS_SQL, engine)
    lookups = extract_lookups(dst)
    logger.info(f"Loaded {len(rows)} trips and dimension lookups")

    # Correctness first, on the real data, with per-row warnings silenced.
    logging.getLogger().setLevel(logging.ERROR)
    rowwise_out = rowwise.transform_trip(rows, lookups)
    facts, rejects = vectorized.transform_trips_df(trips_df, lookups)
    logging.getLogger().setLevel(logging.INFO)
    ok = verify(trips_df, facts, rejects, rowwise_out, v_fares)

    # Then timing.
    logger.info(f"{'rows':>10}  {'row-by-row':>12}  {'vectorized':>12}  {'speed-up':>9}")
    for k in args.scales:
        scaled_rows, scaled_df = scale_rows(rows, k), scale_df(trips_df, k)
        logging.getLogger().setLevel(logging.ERROR)
        _, t_row = timed(rowwise.transform_trip, scaled_rows, lookups)
        _, t_vec = timed(vectorized.transform_trips_df, scaled_df, lookups)
        logging.getLogger().setLevel(logging.INFO)
        logger.info(f"{len(scaled_df):>10,}  {t_row:>11.3f}s  {t_vec:>11.3f}s  {t_row / t_vec:>8.1f}x")
        del scaled_rows, scaled_df

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
