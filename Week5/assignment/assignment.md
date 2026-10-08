# Assignment — Week 5

In Week 4 you made the warehouse correct. In class this week we split the pipeline into
modules (`extract.py`, `transform.py`, `load.py`, `quality.py`). This assignment has three parts:

1. **Vectorize** the pipeline with pandas (`pipeline/`)
2. **Test** the quality checks with pytest (`tests/`)
3. **Rebuild it as ELT** with a medallion architecture, as a separate project (`elt_medallion/`)

Part 2 tests the code you write in Part 1. Part 3 is independent, so you can start it any time.

> **Prerequisite:** your Week 4 migration must be applied to `ride_warehouse`, because Part 1
> loads `time_key`, `trip_status` and `cancelled_by`.

---

## Part 1 — Vectorize the pipeline with pandas

Copy the class modules into `pipeline/` and work there. Don't edit the originals, because the
benchmark compares against them.

```bash
cp ../etl.py ../extract.py ../transform.py ../load.py ../quality.py pipeline/
```

"Vectorized" means pandas works on whole columns at once. In `transform.py` and `quality.py`,
don't use `for row in ...`, `iterrows()`, `itertuples()` or `apply(..., axis=1)`.
`.map(dict)` on a column is fine.

### V1 — Extract into DataFrames

Change the `extract_*` functions to return DataFrames using `pd.read_sql`. Keep the SQL as it
is. Pass `pd.read_sql` a SQLAlchemy engine built with `sqlalchemy.engine.URL.create(...)`.

In a comment: `payment_method_id` is an `INTEGER` in Postgres. Why is it `float64` in your
DataFrame?

### V2 — `transform_trips_df()`

Write it in `pipeline/transform.py`. The exact contract is in the docstring of
[`benchmark_transform.py`](benchmark_transform.py):

```python
transform_trips_df(trips: pd.DataFrame, lookups: dict) -> tuple[pd.DataFrame, pd.DataFrame]
#                                                         (facts,       rejects)
```

It must:

1. Produce the same columns as the class `transform_trip()`, **plus** `time_key`,
   `trip_status` and `cancelled_by`.
2. Map natural keys to surrogate keys with the `lookups` dicts. A trip with an unknown driver,
   passenger, location or date goes to `rejects`, with a `reject_reason` column. A `NULL`
   `payment_method_id` or `promo_code_id` is **not** a reject.
3. Match `v_trips.fare_amount` **to the cent for every trip**.

> **Expect the fare to be wrong at first.** The obvious version,
> `(base_fare * surge_multiplier + tip_amount - discount_amount).round(2)`, is wrong on
> **605 of the 10,000 trips**. Try these two in Python and explain what you see:
> 1. `np.round(42.10 * 1.25 - 5.00, 2)`. The exact answer is 47.625. Which way did it round?
> 2. `93.78 * 1.25 + 11.17` (trip 37). The exact answer is 128.395. What does Python print?
>
> Then fix it without leaving pandas. Hint: do the arithmetic in whole cents (integers), then
> divide by 100 at the end.

### V3 — Bulk load

Rewrite `load_fact_trips()` to send the whole DataFrame in one go with
`psycopg2.extras.execute_values` instead of `executemany`. Use
`ON CONFLICT (source_trip_id) DO UPDATE`.

Watch out for two things:

- psycopg2 can't send NumPy types. A `numpy.int64` raises `can't adapt type 'numpy.int64'`.
- A `NaN` sent to a `NUMERIC` column is stored as `NaN`, not `NULL`, and there's **no error**.
  Every non-completed trip has a `NaN` rating in your DataFrame. Convert missing values to
  `None` before loading, then prove it worked:
  ```sql
  SELECT COUNT(*) FROM fact_trips
  WHERE driver_rating = 'NaN' OR passenger_rating = 'NaN' OR duration_minutes = 'NaN';  -- must be 0
  ```

### V4 — Measure it

```bash
python benchmark_transform.py
```

It checks your transform against the class one and against `v_trips`, then times both at
10k, 100k and 1M rows. All checks must `PASS`. Save the output in `benchmark_log.txt`, and also
time the class `load_fact_trips()` against yours on the 10,000 trips.

As a rough guide, expect about **5–10×** faster on the transform at 1M rows and about **4×**
on the load.

At the bottom of `benchmark_log.txt`, answer: at 10,000 rows, is the pandas version worth it?
Which step (extract, transform or load) takes the most time?

---

## Part 2 — Tested quality checks

### Q1 — Find the bugs

The class `quality.py` has at least two bugs. To find them, build a batch with one `NULL`
`driver_key` and call `run_quality_check()`: which exception do you actually get? Then think
about an incremental run on a night with no new trips.

Describe each bug in the docstring at the top of `pipeline/quality.py`.

### Q2 — Rewrite and extend

Rewrite `pipeline/quality.py` to work on DataFrames. Every check takes the facts DataFrame and
returns a dict with **exactly** these keys:

```python
{"check": "no_negative_fare", "passed": True, "detail": "0 rows with fare_amount < 0"}
```

`run_quality_checks(facts, rejects=None)` runs every check and logs one line per check. If any
check failed, it raises `DataQualityError` naming **every** failed check, not just the first.

Required checks: the five from class, fixed, plus four new ones.

| Check | Fails when |
|---|---|
| `row_count` | never fails. An empty batch is normal; log the count |
| `no_negative_fare` | any `fare_amount < 0` |
| `no_null_required_keys` | driver, passenger, pickup or dropoff key, or `date_key`, is NULL |
| `completed_have_duration` | a completed trip has no `duration_minutes` |
| `valid_status` | `trip_status` is not `completed` / `cancelled` / `no_show` |
| `unique_source_trip_id` | **new:** a `source_trip_id` appears twice |
| `fare_formula` | **new:** `fare_amount` ≠ `base_fare × surge + tip − discount`, rounded half-up to the cent |
| `cancellation_consistent` | **new:** a cancelled trip has no `cancelled_by`, or a non-cancelled trip has one |
| `reject_rate` | **new:** `rejects` is more than 1% of the input |

Call `run_quality_checks()` in `pipeline/etl.py` between transform and load.

### Q3 — Unit tests

[`tests/conftest.py`](tests/conftest.py) gives you `good_facts` (four valid rows) and
`empty_facts`. [`tests/test_quality.py`](tests/test_quality.py) and
[`tests/test_transform.py`](tests/test_transform.py) each have examples and a `TODO` list.

- Every check gets one test where it passes and one where it fails. A failing test copies
  `good_facts` and breaks **one** thing.
- Complete the transform tests in the `TODO` list.
- No test touches the database.

```bash
pytest -v | tee pytest_output.txt
```

Last, switch your fare back to `.round(2)` and run `pytest` again. A test must fail. If none
does, add one. Then switch the fare back.

---

## Part 3 — ELT with a medallion architecture

Parts 1–2 are **ETL**: Python transforms the data, then loads the result. **ELT** loads the raw
data first and transforms it afterwards with SQL, inside the database.

The medallion architecture splits that database into three layers:

| Layer | What it holds |
|---|---|
| **Bronze** | Raw rows exactly as the source sent them. New rows are added; nothing is ever changed or deleted. |
| **Silver** | Clean, typed rows: one per trip, driver and so on. Bad rows go to a quarantine table instead of being dropped. |
| **Gold** | The star schema analysts query, built from silver |

Because bronze keeps the raw data, a bug in a transformation is easy to fix: correct the SQL
and rebuild silver and gold from bronze, without touching the source.

The project is in [`elt_medallion/`](elt_medallion/), with its own database,
`ride_lakehouse`. Setup is in its [README](elt_medallion/README.md).

### M1 — Extract + Load (`run_elt.py`)

Complete `extract_load_table()`. It copies one source table into `bronze.<table>` with `COPY`
and tags each row with `_batch_id` and `_source`. The docstring lists the requirements. Every
run copies every table in full.

The bronze tables are provided in [`sql/00_bronze.sql`](elt_medallion/sql/00_bronze.sql).
Every column is `TEXT`, so bronze accepts anything the source sends.

### M2 — Silver (`sql/01_schema.sql`, `sql/10_silver.sql`)

Create the silver tables, then write the SQL that fills them from bronze. The templates list
the tables and rules. The key ideas:

- **Latest copy wins.** Every run adds another copy of each row to bronze, so silver keeps only
  the newest per id: `ROW_NUMBER() OVER (PARTITION BY trip_id ORDER BY _ingested_at DESC)`.
- **Bad rows are quarantined.** A trip that fails a rule goes to `silver.trips_quarantine` with
  a reason. It is never silently dropped.
- **No email or phone number** in silver.

### M3 — Gold (`sql/01_schema.sql`, `sql/20_gold.sql`)

Build your Week 4 star schema in the `gold` schema: dimensions, `fact_trips` (with
`time_key`, `trip_status`, `cancelled_by`), and **one** mart, `gold.mart_monthly_region_revenue`.
Upsert the dimensions with `ON CONFLICT ... DO UPDATE`, so running gold twice doesn't create
duplicates or change keys.

### M4 — Run it

From `elt_medallion/`, run these steps. Paste the log output and each check query's result into
`elt_run_log.txt`, and put the check queries in `elt_checks.sql`.

```bash
python run_elt.py                                   # (a) first load
psql -d ride_lakehouse -f partner_feed_batch.sql    # (b) a messy partner feed + a correction
python run_elt.py --skip-extract                    #     rebuild silver + gold from bronze
# (c) change one silver rule (below), then:
python run_elt.py --skip-extract
```

| Step | Your check query must show |
|---|---|
| (a) | 10,000 trips in `gold.fact_trips`; completed revenue in gold equals `SUM(fare_amount)` from `ride_prod`'s `v_trips`, to the cent |
| (b) | the outcomes in the table below |
| (c) | Product decides Texas and Arizona are a new region, `Southwest`. Change only the region rule in `10_silver.sql` and rebuild. `gold.mart_monthly_region_revenue` now has `Southwest` rows. |

**Expected after step (b).** Each row is described in `partner_feed_batch.sql`.

| Partner row | Expected |
|---|---|
| `900001`, sent twice, status `' Completed '` | **one** row in `silver.trips`, status `completed`, fare `20.90` |
| `900009`, cancelled by `' PASSENGER'` | in `silver.trips`, `cancelled_by = 'passenger'`, fare `14.63` |
| `900003`–`900008`, `900010` | in `silver.trips_quarantine`, each with its own reason |
| trip `2`, re-sent by `ride_prod` with a new rating | `driver_rating = 3.0` in silver and in gold |

That makes 7 quarantined rows and 10,002 trips in silver and in gold.

### M5 — Short answers

Answer the questions in [`elt_medallion/README.md`](elt_medallion/README.md).

---

## What to submit

| File | Contents |
|---|---|
| `pipeline/*.py` | Vectorized pipeline |
| `benchmark_log.txt` | Benchmark output (all `PASS`), load timings, V4 answer |
| `tests/test_quality.py`, `tests/test_transform.py` | Your tests |
| `pytest_output.txt` | `pytest -v` output, all passing |
| `elt_medallion/run_elt.py` | M1 completed |
| `elt_medallion/sql/01_schema.sql`, `10_silver.sql`, `20_gold.sql` | Silver + gold |
| `elt_medallion/elt_checks.sql`, `elt_medallion/elt_run_log.txt` | M4 queries and results |
| `elt_medallion/README.md` | M5 answers |

Don't commit `.env` files or `__pycache__`.

## Grading checklist

- [ ] V1: extract returns DataFrames; float64 question answered
- [ ] V2: no row loops; new columns included; rejects with reasons; fare matches `v_trips` for all trips; both rounding examples explained
- [ ] V3: `execute_values` load; NumPy types and `NaN` handled; `NaN` query returns 0
- [ ] V4: benchmark all `PASS`; load timed both ways; question answered
- [ ] Q1: two real bugs found and explained
- [ ] Q2: nine checks with the same dict keys; every failure reported; wired into `etl.py`
- [ ] Q3: pass + fail test per check; transform tests; all green without a database; `.round(2)` turns a test red
- [ ] M1: `COPY` into bronze with `_batch_id` / `_source`
- [ ] M2: typed silver; latest copy wins; bad rows quarantined with reasons; no PII
- [ ] M3: gold star schema; dimensions upserted; mart built
- [ ] M4: (a)–(c) shown; revenue matches to the cent; partner outcomes match
- [ ] M5: questions answered
