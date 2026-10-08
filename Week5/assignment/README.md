# Week 5 Assignment

This continues Week 4. The class pipeline in [`../`](../) (`etl.py`, `extract.py`, `transform.py`,
`load.py`, `quality.py`) is correct, but it processes one row at a time, its quality checks have
never been tested, and it's the only way you've built a pipeline so far.

**[Assignment](assignment.md)**: three parts.

- **Vectorize** ([`pipeline/`](pipeline/)): rewrite the pipeline with pandas, with no loops
  over rows, and load with `execute_values`. [`benchmark_transform.py`](benchmark_transform.py)
  checks it's still correct and measures how much faster it is. The obvious pandas fare
  calculation is wrong on 605 of 10,000 trips, and finding out why is part of the exercise.
- **Test** ([`tests/`](tests/)): fix the bugs in the class `quality.py`, add four new checks,
  and unit-test every check with pytest.
- **ELT + medallion** ([`elt_medallion/`](elt_medallion/)): a separate project. Copy the raw
  source into a `bronze` layer, then clean it into `silver` and build the star schema in
  `gold`, all in SQL. A messy partner feed tests that bad rows are quarantined, not lost.

## Setup

You need `ride_prod` and `ride_warehouse` from Week 4, **with your Week 4 migration applied**:

```sql
-- in ride_warehouse: must return 3 rows
SELECT column_name FROM information_schema.columns
WHERE table_name = 'fact_trips' AND column_name IN ('time_key', 'trip_status', 'cancelled_by');
```

```bash
pip install -r requirements.txt
cp ../etl.py ../extract.py ../transform.py ../load.py ../quality.py pipeline/
```

Scripts in this folder read the same `SRC_DB_*` / `DEST_DB_*` variables as the class ETL.
`load_dotenv()` searches upward from the script's folder, so your `Week5/.env` is found
automatically. The ELT project has its own `.env`: see
[`elt_medallion/README.md`](elt_medallion/README.md).

## What to submit

| File | Start from |
|---|---|
| `pipeline/*.py` | copies of the class modules |
| `benchmark_log.txt` | output of [`benchmark_transform.py`](benchmark_transform.py) + answers |
| `tests/test_quality.py`, `tests/test_transform.py` | the provided examples (fill in the `TODO`s) |
| `pytest_output.txt` | `pytest -v` output |
| `elt_medallion/run_elt.py` | [`run_elt.py`](elt_medallion/run_elt.py) (fill in the `TODO`) |
| `elt_medallion/sql/01_schema.sql`, `10_silver.sql`, `20_gold.sql` | the templates in [`elt_medallion/sql/`](elt_medallion/sql/) |
| `elt_medallion/elt_checks.sql`, `elt_medallion/elt_run_log.txt` | new |
| `elt_medallion/README.md` | the template (answer the three questions) |

Every written answer goes as a comment in the file it's about, or in the README where the
assignment says so.

## How to submit

Same workflow as previous weeks:

```bash
git checkout main
git pull upstream main
git checkout -b week5-assignment

# ... complete the three parts ...

git add Week5/assignment
git status          # make sure no .env and no __pycache__ are staged
git commit -m "Complete week 5 assignment"
git push -u origin week5-assignment
```

Then open a pull request **on your own fork** (base: `main`, compare: `week5-assignment`) and
share the link with your instructor. Submit before the Week 6 session begins.
