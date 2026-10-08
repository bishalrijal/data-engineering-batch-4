import psycopg2
import logging

import os 
from dotenv import load_dotenv
import argparse
import time 

def parse_args():
    parser = argparse.ArgumentParser(description="Rides ETL pipeline config")
    parser.add_argument("--full-reload", action="store_true",help="Truncate warehouse and reload all data")
    return parser.parse_args()

from extract import (extract_driver,
                      extract_location,
                      extract_passenger,
                      extract_payment_method,
                      extract_promo_code,
                      extract_trips_full,
                      extract_trips_incremental,
                      extract_lookup_dim,
                      get_watermark)

from transform import transform_trip


from load import (
    load_fact_trips,
    load_dim_promo_code,
    load_dim_passenger,
    load_dim_payment_method,
    load_dim_location,
    load_dim_driver
)

from quality import run_quality_check

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s %(filename)s:%(lineno)d %(message)s",
    # filename='logs/etl_{date}_{run}.log'
)
logger = logging.getLogger(__name__)


SOURCE_DB_CONFIG = dict(
    host=    os.getenv("SRC_DB_HOST"),
    port =   os.getenv("SRC_DB_PORT"),
    dbname = os.getenv("SRC_DB_NAME"),
    user=    os.getenv("SRC_DB_USER"),
    password=os.getenv("SRC_DB_PASSWORD")
)

DEST_DB_CONFIG = dict(
    host=    os.getenv("DEST_DB_HOST"),
    port =   os.getenv("DEST_DB_PORT"),
    dbname = os.getenv("DEST_DB_NAME"),
    user=    os.getenv("DEST_DB_USER"),
    password=os.getenv("DEST_DB_PASSWORD")
)



# TODO: research on arg vs kwarg
def main():
    args = parse_args()
    mode = 'FULL' if args.full_reload else 'INCREMENTAL'
    src_conn = psycopg2.connect(**SOURCE_DB_CONFIG)
    dst_conn = psycopg2.connect(**DEST_DB_CONFIG)

    time0 = time.time()
    driver_data = extract_driver(src_conn)
    load_dim_driver(dst_conn, driver_data)

    passenger_data = extract_passenger(src_conn)
    load_dim_passenger(dst_conn, passenger_data)

    location_data = extract_location(src_conn)
    load_dim_location(dst_conn, location_data)

    payment_method_data = extract_payment_method(src_conn)
    load_dim_payment_method(dst_conn, payment_method_data)

    promo_code_data = extract_promo_code(src_conn)
    load_dim_promo_code(dst_conn, promo_code_data)

    watermark = get_watermark(dst_conn)
    time1 = time.time()
    logger.info(f"Dimension table runs completed on {time1-time0:.3f}s")

    time0 = time.time()
    if mode == "INCREMENTAL":
        trip_data = extract_trips_incremental(src_conn,watermark)
    else:
        trip_data = extract_trips_full(src_conn)
    time1 = time.time()
    logger.info(f"trips extraction runs completed on {time1-time0:.3f}s")

    lookups = extract_lookup_dim(dst_conn)
    print(lookups["driver"].get(2))
    fact_row = transform_trip(trip_data, lookups)
    run_quality_check(fact_row)
    load_fact_trips(dst_conn,fact_row)

if __name__ == '__main__':
    main()