-- =============================================================================
-- partner_feed_batch.sql — Week 5 Assignment, Part 3 (PROVIDED — do not change)
--
-- Simulates two things that happen to every real pipeline:
--
--   1. A second source. A partner fleet sends us its trips through a CSV drop,
--      and the CSV is messy. These rows land in bronze with _source = 'partner_feed'.
--   2. A correction. ride_prod fixed the driver_rating on trip 2 (4.5 -> 3.0) and
--      sent the row again. Bronze now holds a newer copy of trip 2 from ride_prod.
--
-- Run it AFTER your first run of run_elt.py, then run `python run_elt.py --skip-extract`
-- and compare silver, quarantine and gold with the expected table in the assignment.
--
--     psql -d ride_lakehouse -f partner_feed_batch.sql
-- =============================================================================

BEGIN;

INSERT INTO ops.elt_run_log (status, finished_at, detail)
VALUES ('success', now(), 'partner_feed_batch.sql: simulated partner CSV drop + ride_prod correction');

-- ── 1. Partner CSV drop ──────────────────────────────────────────────────────
INSERT INTO bronze.trips (
    trip_id, driver_id, passenger_id, vehicle_id, pickup_location_id, dropoff_location_id,
    payment_method_id, promo_code_id, base_fare, tip_amount, discount_amount, surge_multiplier,
    distance_km, status, requested_at, completed_at, driver_rating, passenger_rating,
    _batch_id, _source
)
SELECT v.*, currval('ops.elt_run_log_batch_id_seq'), 'partner_feed'
FROM (VALUES
    -- P1  clean once trimmed: status has spaces and capitals, timestamps use 'T', empty string for "no promo"
    ('900001', '3', '7',  '', '1', '2', '1', '',  '18.40', '2.50', '0.00', '1.00', '7.20',  ' Completed ', '2026-06-30T08:37:00', '2026-06-30T08:55:30', '4.5', '5.0'),
    -- P2  exact duplicate of P1 (the partner sent the same line twice)
    ('900001', '3', '7',  '', '1', '2', '1', '',  '18.40', '2.50', '0.00', '1.00', '7.20',  ' Completed ', '2026-06-30T08:37:00', '2026-06-30T08:55:30', '4.5', '5.0'),
    -- P3  driver 9999 does not exist
    ('900003', '9999', '7', '', '1', '2', '1', '', '12.00', '0.00', '0.00', '1.00', '4.10', 'completed', '2026-06-30 09:10:00', '2026-06-30 09:24:00', '', ''),
    -- P4  base_fare is not a number
    ('900004', '3', '7',  '', '1', '2', '1', '',  'twelve', '0.00', '0.00', '1.00', '4.10', 'completed', '2026-06-30 09:30:00', '2026-06-30 09:41:00', '', ''),
    -- P5  requested_at is not a valid timestamp (there is no June 31st)
    ('900005', '3', '7',  '', '1', '2', '1', '',  '15.00', '0.00', '0.00', '1.00', '5.00', 'completed', '2026-06-31 10:00:00', '2026-06-31 10:20:00', '', ''),
    -- P6  unknown status
    ('900006', '3', '7',  '', '1', '2', '1', '',  '22.00', '0.00', '0.00', '1.00', '9.80', 'refunded',  '2026-06-30 11:00:00', '', '', ''),
    -- P7  completed before it was requested
    ('900007', '3', '7',  '', '1', '2', '1', '',  '30.00', '0.00', '0.00', '1.00', '12.0', 'completed', '2026-06-30 12:00:00', '2026-06-30 11:15:00', '', ''),
    -- P8  negative tip
    ('900008', '3', '7',  '', '1', '2', '1', '',  '25.00', '-3.00', '0.00', '1.00', '10.5', 'completed', '2026-06-30 13:00:00', '2026-06-30 13:35:00', '', ''),
    -- P9  valid cancelled trip; its cancellation row below says ' PASSENGER'
    ('900009', '4', '8',  '', '3', '4', '2', '',  '9.75', '0.00', '0.00', '1.50', '3.10',  'cancelled', '2026-06-30 18:05:00', '', '', ''),
    -- P10 surge below 1.00 (ride_prod's CHECK would never allow this)
    ('900010', '4', '8',  '', '3', '4', '2', '',  '14.00', '0.00', '0.00', '0.00', '6.00', 'completed', '2026-06-30 19:00:00', '2026-06-30 19:22:00', '', '')
) AS v;

INSERT INTO bronze.trip_cancellations (trip_id, cancelled_at, cancelled_by, cancellation_reason, _batch_id, _source)
VALUES ('900009', '2026-06-30 18:07:00', ' PASSENGER', 'changed plans',
        currval('ops.elt_run_log_batch_id_seq'), 'partner_feed');

-- ── 2. ride_prod correction: trip 2 re-extracted with a new driver_rating ────
-- Copies the latest ride_prod version of trip 2 already in bronze, changes the
-- rating, and stamps it one minute later so "latest wins" has something to pick.
INSERT INTO bronze.trips (
    trip_id, driver_id, passenger_id, vehicle_id, pickup_location_id, dropoff_location_id,
    payment_method_id, promo_code_id, base_fare, tip_amount, discount_amount, surge_multiplier,
    distance_km, status, requested_at, completed_at, driver_rating, passenger_rating,
    _batch_id, _source, _ingested_at
)
SELECT
    trip_id, driver_id, passenger_id, vehicle_id, pickup_location_id, dropoff_location_id,
    payment_method_id, promo_code_id, base_fare, tip_amount, discount_amount, surge_multiplier,
    distance_km, status, requested_at, completed_at, '3.0', passenger_rating,
    currval('ops.elt_run_log_batch_id_seq'), 'ride_prod', now() + INTERVAL '1 minute'
FROM bronze.trips
WHERE trip_id = '2' AND _source = 'ride_prod'
ORDER BY _ingested_at DESC
LIMIT 1;

COMMIT;
