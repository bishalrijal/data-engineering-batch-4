import psycopg2
import os

# ── CONNECTION SETTINGS ───────────────────────────────────────────
# Update these if your PostgreSQL setup is different.
DB_HOST     = "localhost"
DB_PORT     = 5433
DB_NAME     = "ride_share"  # replace with your actual database name
DB_USER     = "postgres"  # replace with your actual database user
DB_PASSWORD = "Test123"  # replace with your actual database password

# Path to the CSV file (same folder as this script by default)
CSV_PATH = os.path.join(os.path.dirname(__file__), "rides.csv")
# ─────────────────────────────────────────────────────────────────


# ── STEP 1: CREATE TABLE SQL ──────────────────────────────────────
# Defines the schema for the rides table.
# Notice: each column has a specific type, and some have constraints.
# We talked about why each choice was made in class.

CREATE_TABLE_SQL = """
DROP TABLE IF EXISTS rides;

CREATE TABLE rides (
    ride_id          INTEGER       PRIMARY KEY,
    driver_name      VARCHAR(100)          NOT NULL,
    passenger_name   VARCHAR(100)          NOT NULL,
    pickup_city      VARCHAR(100)          NOT NULL,
    dropoff_city     VARCHAR(100)          NOT NULL,
    fare_amount      NUMERIC(10,2) NOT NULL CHECK (fare_amount >= 0),
    ride_distance_km NUMERIC(6,2)  NOT NULL CHECK (ride_distance_km >= 0),
    ride_status      VARCHAR(50)   NOT NULL default 'pending' CHECK (ride_status IN ('no_show', 'completed', 'cancelled')),
    requested_at     TIMESTAMP     NOT NULL,
    completed_at     TIMESTAMP,
    rating           NUMERIC(2,1) CHECK (rating >= 1.0 AND rating <= 5.0),
    payment_method   VARCHAR(50)
);
"""
# Note: completed_at, rating, and payment_method are nullable (no NOT NULL).
# Can you think of why? What does a NULL value mean for each of these?
# ─────────────────────────────────────────────────────────────────


def get_connection():
    """Open and return a database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def create_table(conn):
    """Drop and recreate the rides table."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    print("Table created")


def load_csv(conn, csv_path):
    """
    Load the CSV into the rides table using PostgreSQL's COPY command.

    COPY is much faster than inserting rows one by one -- it streams
    the file directly into the table at the database level.

    The 'with open(...)' block safely closes the file even if an
    error occurs mid-load.
    """
    with conn.cursor() as cur:
        with open(csv_path, "r", encoding="utf-8") as f:
            next(f)  # skip the header row -- COPY doesn't want it
            cur.copy_from(
                file=f,
                table="rides",
                sep=",",
                null=""   # treat empty string as NULL
            )
        row_count = cur.rowcount
    conn.commit()
    return row_count


def verify(conn):
    """Run a quick sanity check -- print counts by ride status."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ride_status, COUNT(*) AS total
            FROM rides
            GROUP BY ride_status
            ORDER BY total DESC;
        """)
        rows = cur.fetchall()

    print("\nRides by status:")
    for status, count in rows:
        print(f"  {status:<12} {count:>6}")


def main():
    print(f"Connecting to {DB_NAME} on {DB_HOST}:{DB_PORT}...")

    conn = get_connection()
    print("Connected")

    create_table(conn)

    print(f"Loading {CSV_PATH}...")
    loaded = load_csv(conn, CSV_PATH)
    print(f"Loaded {loaded:,} rows")

    verify(conn)

    conn.close()
    print("\nDone. Open DBeaver and run:  SELECT * FROM rides LIMIT 10;")


if __name__ == "__main__":
    main()
