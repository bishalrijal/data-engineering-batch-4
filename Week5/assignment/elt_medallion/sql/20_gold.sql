-- =============================================================================
-- 20_gold.sql — Week 5 Assignment, Part 3
-- Name:
--
-- silver -> gold. Runs after 10_silver.sql, as one transaction, on every run.
--
-- Running it twice must not create duplicates or change any surrogate key,
-- so upsert (ON CONFLICT ... DO UPDATE) instead of truncating.
-- =============================================================================


-- ── G1 Dimensions (SCD Type 1) ───────────────────────────────────────────────
-- TODO: upsert each gold.dim_* from silver:
--     INSERT ... SELECT ... FROM silver.<table>
--     ON CONFLICT (<natural key>) DO UPDATE SET <attributes> = EXCLUDED.<attributes>


-- ── G2 Fact ──────────────────────────────────────────────────────────────────
-- TODO: upsert gold.fact_trips from silver.trips joined to the gold dimensions.
--   - the surrogate key lookups are JOINs here, not Python dicts
--   - time_key and date_key computed in SQL
--   - ON CONFLICT (source_trip_id) DO UPDATE, so trip 2's corrected rating lands


-- ── G3 Mart ──────────────────────────────────────────────────────────────────
-- TODO: CREATE OR REPLACE VIEW gold.mart_monthly_region_revenue
--   month, region (pickup location), completed_trips, revenue, avg_fare, cancellation_rate_pct
