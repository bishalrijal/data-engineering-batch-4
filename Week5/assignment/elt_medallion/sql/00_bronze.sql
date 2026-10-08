-- =============================================================================
-- 00_bronze.sql — Week 5 Assignment, Part 3 (PROVIDED — do not change)
--
-- Run once against a NEW, empty database:
--     createdb ride_lakehouse
--     psql -d ride_lakehouse -f sql/00_bronze.sql
--
-- This is the landing contract. Bronze is a faithful, append-only copy of what
-- each source sent us, plus three columns describing the load itself:
--
--   _batch_id     one id per run of run_elt.py (from ops.elt_run_log)
--   _source       which feed the row came from: 'ride_prod', 'partner_feed', ...
--   _ingested_at  when we received it
--
-- Every business column is TEXT. Bronze never rejects a row for having the
-- wrong type: a value that isn't a valid number or timestamp is still evidence
-- of what the source sent, and silver decides what to do with it.
--
-- Bronze is never UPDATEd or DELETEd. Every run appends a new copy of each row.
-- No primary keys on business columns for the same reason.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS ops;


-- ── Run log: one row per run_elt.py execution ────────────────────────────────
CREATE TABLE ops.elt_run_log (
    batch_id        BIGSERIAL    PRIMARY KEY,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT         NOT NULL DEFAULT 'running'
                                 CHECK (status IN ('running', 'success', 'failed')),
    detail          TEXT
);

-- One row per step per run (copying a table into bronze, building silver, building gold).
-- Filled by run_elt.py.
CREATE TABLE ops.elt_step_log (
    batch_id        BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    step            TEXT         NOT NULL,          -- e.g. 'bronze.trips', 'silver.trips', 'gold.fact_trips'
    started_at      TIMESTAMPTZ  NOT NULL,
    finished_at     TIMESTAMPTZ,
    rows_affected   BIGINT,
    status          TEXT         NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    error           TEXT,
    PRIMARY KEY (batch_id, step)
);


-- ── Bronze tables: source columns as TEXT + load metadata ────────────────────

CREATE TABLE bronze.drivers (
    driver_id       TEXT,
    name            TEXT,
    email           TEXT,
    phone_number    TEXT,
    status          TEXT,
    joined_at       TEXT,
    _batch_id       BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source         TEXT         NOT NULL,
    _ingested_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.passengers (
    passenger_id    TEXT,
    name            TEXT,
    email           TEXT,
    phone_number    TEXT,
    status          TEXT,
    created_at      TEXT,
    _batch_id       BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source         TEXT         NOT NULL,
    _ingested_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.locations (
    location_id     TEXT,
    city_name       TEXT,
    state_province  TEXT,
    country         TEXT,
    latitude        TEXT,
    longitude       TEXT,
    _batch_id       BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source         TEXT         NOT NULL,
    _ingested_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.payment_methods (
    payment_method_id TEXT,
    name            TEXT,
    type            TEXT,
    is_active       TEXT,
    _batch_id       BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source         TEXT         NOT NULL,
    _ingested_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.promo_codes (
    promo_code_id   TEXT,
    code            TEXT,
    discount_type   TEXT,
    discount_value  TEXT,
    valid_from      TEXT,
    valid_until     TEXT,
    max_uses        TEXT,
    is_active       TEXT,
    _batch_id       BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source         TEXT         NOT NULL,
    _ingested_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.trips (
    trip_id             TEXT,
    driver_id           TEXT,
    passenger_id        TEXT,
    vehicle_id          TEXT,
    pickup_location_id  TEXT,
    dropoff_location_id TEXT,
    payment_method_id   TEXT,
    promo_code_id       TEXT,
    base_fare           TEXT,
    tip_amount          TEXT,
    discount_amount     TEXT,
    surge_multiplier    TEXT,
    distance_km         TEXT,
    status              TEXT,
    requested_at        TEXT,
    completed_at        TEXT,
    driver_rating       TEXT,
    passenger_rating    TEXT,
    _batch_id           BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source             TEXT         NOT NULL,
    _ingested_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE bronze.trip_cancellations (
    trip_id             TEXT,
    cancelled_at        TEXT,
    cancelled_by        TEXT,
    cancellation_reason TEXT,
    _batch_id           BIGINT       NOT NULL REFERENCES ops.elt_run_log(batch_id),
    _source             TEXT         NOT NULL,
    _ingested_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Silver's "latest copy wins" dedup scans by source and batch.
CREATE INDEX ON bronze.trips (_source, _batch_id);
CREATE INDEX ON bronze.trip_cancellations (_source, _batch_id);
