"""
run_elt.py
----------
Week 5 Assignment — Part 3: ELT with a medallion architecture.

In Part 1 the pipeline was Extract -> Transform (in Python) -> Load. This project is
Extract -> Load -> Transform: Python only copies raw source rows into bronze. Every
transformation after that is SQL that runs inside ride_lakehouse.

    ride_prod ──COPY──▶ bronze.*  ──sql/10_silver.sql──▶ silver.*  ──sql/20_gold.sql──▶ gold.*
              (Python)            (Postgres)                       (Postgres)

You complete extract_load_table() (marked TODO), and you write sql/01_schema.sql,
sql/10_silver.sql and sql/20_gold.sql.

Run from Week5/assignment/elt_medallion/:
    python run_elt.py                        # copy the source into bronze, then build silver + gold
    python run_elt.py --skip-extract         # rebuild silver + gold from bronze; source untouched
"""

import argparse
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent

SOURCE_DB_CONFIG = dict(
    host=    os.getenv("SRC_DB_HOST"),
    port=    os.getenv("SRC_DB_PORT"),
    dbname=  os.getenv("SRC_DB_NAME"),
    user=    os.getenv("SRC_DB_USER"),
    password=os.getenv("SRC_DB_PASSWORD")
)

LAKE_DB_CONFIG = dict(
    host=    os.getenv("LAKE_DB_HOST"),
    port=    os.getenv("LAKE_DB_PORT"),
    dbname=  os.getenv("LAKE_DB_NAME"),           # ride_lakehouse
    user=    os.getenv("LAKE_DB_USER"),
    password=os.getenv("LAKE_DB_PASSWORD")
)

# Source table -> the columns bronze stores, in bronze's column order.
# Every run copies every table in full.
SOURCE_TABLES = {
    "drivers":            ["driver_id", "name", "email", "phone_number", "status", "joined_at"],
    "passengers":         ["passenger_id", "name", "email", "phone_number", "status", "created_at"],
    "locations":          ["location_id", "city_name", "state_province", "country", "latitude", "longitude"],
    "payment_methods":    ["payment_method_id", "name", "type", "is_active"],
    "promo_codes":        ["promo_code_id", "code", "discount_type", "discount_value",
                           "valid_from", "valid_until", "max_uses", "is_active"],
    "trips":              ["trip_id", "driver_id", "passenger_id", "vehicle_id",
                           "pickup_location_id", "dropoff_location_id", "payment_method_id",
                           "promo_code_id", "base_fare", "tip_amount", "discount_amount",
                           "surge_multiplier", "distance_km", "status", "requested_at",
                           "completed_at", "driver_rating", "passenger_rating"],
    "trip_cancellations": ["trip_id", "cancelled_at", "cancelled_by", "cancellation_reason"],
}
SOURCE_NAME = "ride_prod"


# ─────────────────────────────────────────────────────────────────────────────
# Run + step logging  (provided)
# ─────────────────────────────────────────────────────────────────────────────

def start_run(lake):
    with lake.cursor() as cur:
        cur.execute("INSERT INTO ops.elt_run_log DEFAULT VALUES RETURNING batch_id")
        batch_id = cur.fetchone()[0]
    lake.commit()
    logger.info(f"Started batch {batch_id}")
    return batch_id


def finish_run(lake, batch_id, status, detail=None):
    lake.rollback()   # discard any half-finished transaction before writing the outcome
    with lake.cursor() as cur:
        cur.execute(
            "UPDATE ops.elt_run_log SET status = %s, finished_at = now(), detail = %s WHERE batch_id = %s",
            (status, detail, batch_id),
        )
    lake.commit()


@contextmanager
def step(lake, batch_id, name):
    """Times a step and records it in ops.elt_step_log. The body sets s['rows']."""
    s = {"rows": None}
    t0 = time.perf_counter()
    try:
        yield s
    except Exception as e:
        lake.rollback()
        with lake.cursor() as cur:
            cur.execute(
                "INSERT INTO ops.elt_step_log (batch_id, step, started_at, finished_at, status, error) "
                "VALUES (%s, %s, now() - make_interval(secs => %s), now(), 'failed', %s)",
                (batch_id, name, time.perf_counter() - t0, str(e)),
            )
        lake.commit()
        logger.error(f"{name:<28} FAILED: {e}")
        raise
    with lake.cursor() as cur:
        cur.execute(
            "INSERT INTO ops.elt_step_log (batch_id, step, started_at, finished_at, rows_affected, status) "
            "VALUES (%s, %s, now() - make_interval(secs => %s), now(), %s, 'success')",
            (batch_id, name, time.perf_counter() - t0, s["rows"]),
        )
    lake.commit()
    logger.info(f"{name:<28} {s['rows'] if s['rows'] is not None else '-':>8} rows  {time.perf_counter() - t0:6.2f}s")


# ─────────────────────────────────────────────────────────────────────────────
# E — Extract + Load into bronze  (you complete extract_load_table)
# ─────────────────────────────────────────────────────────────────────────────

def extract_load_table(src, lake, table, batch_id):
    """
    TODO: copy one source table into bronze.<table> and return the number of rows
    copied. Bronze only ever grows: don't delete or update what's already there.

    Requirements:
      - Stream it with COPY on both sides, not SELECT + executemany:
            src:  cur.copy_expert("COPY (SELECT ...) TO STDOUT ...", buffer)
            lake: cur.copy_expert("COPY bronze.<table> (...) FROM STDIN ...", buffer)
        An io.StringIO buffer is fine at this size.
      - Every landed row gets _batch_id = batch_id and _source = SOURCE_NAME.
        (One way: select them as constants in the source query, so they're just two
        more columns in the COPY stream.)
      - NULL must survive the trip as NULL, not as the string 'None' or ''.
      - Use the column list from SOURCE_TABLES[table] on both sides. Never SELECT *.
      - Build identifiers with psycopg2.sql.Identifier, not f-strings.
      - Commit once per table, so a failure leaves no half-loaded table behind.
    """
    raise NotImplementedError("extract_load_table")


def extract_load(src, lake, batch_id):
    for table in SOURCE_TABLES:
        with step(lake, batch_id, f"bronze.{table}") as s:
            s["rows"] = extract_load_table(src, lake, table, batch_id)


# ─────────────────────────────────────────────────────────────────────────────
# T — Transform inside the database  (provided runner; you write the SQL)
# ─────────────────────────────────────────────────────────────────────────────

def run_sql_file(lake, batch_id, path):
    """Run one layer's SQL file as one transaction: the whole layer builds or none of it does.

    The file can read the current batch id as current_setting('elt.batch_id')::BIGINT.
    """
    text = path.read_text()
    if not any(line.strip() and not line.strip().startswith("--") for line in text.splitlines()):
        logger.warning(f"{path.name} has no SQL yet — skipped")
        return
    with step(lake, batch_id, path.stem) as s:
        with lake.cursor() as cur:
            cur.execute("SELECT set_config('elt.batch_id', %s, true)", (str(batch_id),))
            cur.execute(text)
            s["rows"] = cur.rowcount if cur.rowcount >= 0 else None   # rowcount of the LAST statement only
        lake.commit()


def main():
    parser = argparse.ArgumentParser(description="ride_prod -> ride_lakehouse ELT")
    parser.add_argument("--skip-extract", action="store_true",
                        help="don't touch the source; rebuild silver and gold from what bronze already has")
    args = parser.parse_args()

    lake = psycopg2.connect(**LAKE_DB_CONFIG)
    batch_id = start_run(lake)
    try:
        if not args.skip_extract:
            src = psycopg2.connect(**SOURCE_DB_CONFIG)
            try:
                extract_load(src, lake, batch_id)
            finally:
                src.close()

        for path in sorted((HERE / "sql").glob("[1-9]*.sql")):   # 10_silver, 20_gold; not 00 / 01
            run_sql_file(lake, batch_id, path)

        finish_run(lake, batch_id, "success")
        logger.info(f"Batch {batch_id} finished")
    except Exception as e:
        finish_run(lake, batch_id, "failed", str(e))
        logger.error(f"Batch {batch_id} failed: {e}")
        sys.exit(1)
    finally:
        lake.close()


if __name__ == "__main__":
    main()
