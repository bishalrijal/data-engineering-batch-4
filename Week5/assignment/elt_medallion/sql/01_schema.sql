-- =============================================================================
-- 01_schema.sql — Week 5 Assignment, Part 3
-- Name:
--
-- DDL for silver and gold. Run ONCE, after 00_bronze.sql:
--     psql -d ride_lakehouse -f sql/01_schema.sql
--
-- run_elt.py does not run this file (it skips 0*.sql), so plain CREATE TABLE is fine.
-- =============================================================================


-- ── Silver: one clean, typed, current row per business entity ────────────────
--
-- TODO S0: create these tables. Real types (INTEGER, NUMERIC, TIMESTAMP, BOOLEAN),
-- NOT NULL where the business says so, a PRIMARY KEY on the natural key, CHECKs
-- for the allowed values.
--
--   silver.drivers            driver_id PK, name, status, joined_at  (no email / phone_number)
--   silver.passengers         passenger_id PK, name, status, created_at
--   silver.locations          location_id PK, ..., region (derived, same rule as class extract_location)
--   silver.payment_methods
--   silver.promo_codes
--   silver.trips              trip_id PK, source (ride_prod / partner_feed), all trip columns typed,
--                             cancelled_by folded in from trip_cancellations,
--                             fare_amount and duration_minutes computed,
--                             _batch_id of the bronze row it came from
--
--   silver.trips_quarantine   rows that failed a rule:
--                             raw_row JSONB (the bronze row as-is: to_jsonb(b)), reason TEXT
--
-- Casting 'twelve'::NUMERIC raises an error and would fail the whole run. Use these
-- two helpers (provided) instead: they return NULL when the text doesn't cast.
--     ops.try_numeric('twelve')            -> NULL
--     ops.try_timestamp('2026-06-31 10:00') -> NULL

CREATE FUNCTION ops.try_numeric(t TEXT) RETURNS NUMERIC LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN NULLIF(trim(t), '')::NUMERIC;
EXCEPTION WHEN others THEN
    RETURN NULL;
END $$;

CREATE FUNCTION ops.try_timestamp(t TEXT) RETURNS TIMESTAMP LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN NULLIF(trim(t), '')::TIMESTAMP;
EXCEPTION WHEN others THEN
    RETURN NULL;
END $$;


-- ── Gold: the star schema, built from silver ─────────────────────────────────
--
-- TODO G0: create gold.dim_date, gold.dim_time, gold.dim_driver, gold.dim_passenger,
-- gold.dim_location, gold.dim_payment_method, gold.dim_promo_code, gold.fact_trips.
--
-- Start from Week4/warehouse.sql, with your Week 4 fixes built in:
--   - UNIQUE on every dimension's natural key
--   - fact_trips.time_key, trip_status, cancelled_by
-- Copy the dim_date and dim_time INSERTs from warehouse.sql here too; they only
-- need loading once.
