import psycopg2
import logging

import os 
from dotenv import load_dotenv


from extract import (extract_driver,
                      extract_location,
                      extract_passenger,
                      extract_payment_method,
                      extract_promo_code,
                      extract_trips,
                      extract_lookup_dim)

from transform import transform_trip


from load import (
    load_fact_trips,
    load_dim_promo_code,
    load_dim_passenger,
    load_dim_payment_method,
    load_dim_location,
    load_dim_driver
)

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
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
    src_conn = psycopg2.connect(**SOURCE_DB_CONFIG)
    dst_conn = psycopg2.connect(**DEST_DB_CONFIG)

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

    trip_data = extract_trips(src_conn)
    lookups = extract_lookup_dim(dst_conn)
    print(lookups["driver"].get(2))
    fact_row = transform_trip(trip_data, lookups)
    load_fact_trips(dst_conn,fact_row)

if __name__ == '__main__':
    main()