# ride_lakehouse — ELT with a medallion architecture

<!-- Week 5 Assignment, Part 3. Answer the three questions at the bottom.
     A few sentences each is enough. -->

```
ride_prod ──COPY──▶ bronze ──SQL──▶ silver ──SQL──▶ gold
           (Python)        (in Postgres)    (in Postgres)
```

| Layer | Holds | Written by |
|---|---|---|
| `bronze` | Every row the source sent, as TEXT, never changed | `run_elt.py` (COPY) |
| `silver` | One clean, typed row per entity; bad rows in `silver.trips_quarantine` | `sql/10_silver.sql` |
| `gold` | Star schema + mart for analysts | `sql/20_gold.sql` |
| `ops` | Log of each run and step | `run_elt.py` |

## Setup

```bash
createdb ride_lakehouse
psql -d ride_lakehouse -f sql/00_bronze.sql      # provided: bronze + ops
psql -d ride_lakehouse -f sql/01_schema.sql      # yours: silver + gold tables
cp .env.example .env                             # fill in passwords
```

## Run

```bash
python run_elt.py                    # copy the source into bronze, then build silver + gold
python run_elt.py --skip-extract     # rebuild silver + gold from bronze only
```

## Questions

### 1. ETL vs ELT
In Part 1 the transformation is Python. Here it is SQL inside the database. Give one advantage
of each approach.

### 2. Why keep bronze?
In step (c) you changed a rule and rebuilt gold. How would you have done that in the Part 1
pipeline, which keeps no raw copy?

### 3. Quarantine vs reject
Part 1 logs rejected rows and drops them. Here they go to a table. What can you do with the
table that you can't do with a log line?
