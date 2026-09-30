-- Q1 — Rides per driver
-- name, total_rides — completed rides only, ordered by total_rides desc



SELECT
    d.name,
    COUNT(r.ride_id) AS total_rides
FROM drivers d
JOIN rides r
    ON d.driver_id = r.driver_id
WHERE r.status = 'completed'
GROUP BY d.driver_id, d.name
ORDER BY total_rides DESC;


-- Q2 — Drivers with zero completed rides
-- LEFT JOIN, not a subquery

SELECT
    d.name
FROM drivers d
LEFT JOIN rides r
    ON d.driver_id = r.driver_id
    AND r.status = 'completed'
WHERE r.ride_id IS NULL
ORDER BY d.name;


-- Q3 — Average fare per pickup city

SELECT
    l.city_name,
    ROUND(AVG(r.fare), 2) AS avg_fare
FROM rides r
JOIN locations l
    ON r.pickup_location_id = l.location_id
WHERE r.status = 'completed'
GROUP BY l.location_id, l.city_name
ORDER BY avg_fare DESC;


-- Q4 — Same-city driver/passenger trips
--
-- The current schema does not store the driver's city/location
-- at the time of the trip.
--
-- We know the passenger/trip pickup city from rides.pickup_location_id,
-- but there is no driver_location_id (or equivalent) in the schema.
-- Therefore, we cannot reliably determine whether the driver
-- and passenger were in the same city.
--
-- A possible partial query is:

SELECT
    r.ride_id,
    d.name AS driver_name,
    p.name AS passenger_name,
    l.city_name AS pickup_city
FROM rides r
JOIN drivers d
    ON r.driver_id = d.driver_id
JOIN passengers p
    ON r.passenger_id = p.passenger_id
JOIN locations l
    ON r.pickup_location_id = l.location_id;


-- Q5 — Total revenue from completed rides

SELECT
    SUM(fare) AS total_revenue
FROM rides
WHERE status = 'completed';


-- Q6 — WHERE and HAVING together
-- Drivers with > 280 completed rides AND total revenue > NPR 140,000

SELECT
    d.driver_id,
    d.name,
    COUNT(r.ride_id) AS total_rides,
    SUM(r.fare) AS total_revenue
FROM drivers d
JOIN rides r
    ON d.driver_id = r.driver_id
WHERE r.status = 'completed'
GROUP BY d.driver_id, d.name
HAVING COUNT(r.ride_id) > 280
   AND SUM(r.fare) > 140000
ORDER BY total_revenue DESC;


-- Q7 — Clean the phone numbers
-- Scratch copy

DROP TABLE IF EXISTS temp_rides;

CREATE TEMP TABLE temp_rides AS
SELECT *
FROM rides;


-- Add messy phone numbers

ALTER TABLE temp_rides
ADD COLUMN messy_phone_number TEXT;


-- Example messy values
UPDATE temp_rides
SET messy_phone_number =
    CASE
        WHEN ride_id % 3 = 0 THEN '+977-9812345678'
        WHEN ride_id % 3 = 1 THEN '98123 45678'
        ELSE '(98123) 45678'
    END;


-- Digits-only phone numbers

SELECT
    ride_id,
    messy_phone_number,
    REGEXP_REPLACE(messy_phone_number, '[^0-9]', '', 'g')
        AS clean_phone_number
FROM temp_rides;


-- REPLACE() alone cannot remove all unwanted characters
-- because REPLACE() replaces one specific string/pattern at a time.
-- REGEXP_REPLACE() can remove every character that does not
-- match the required pattern, such as all non-digit characters.


-- Q8 — Prove the city data is clean

-- Version 1: STRPOS

SELECT DISTINCT city_name
FROM locations
WHERE STRPOS(city_name, '  ') > 0
   OR city_name <> TRIM(city_name);


-- Version 2: ILIKE

SELECT DISTINCT city_name
FROM locations
WHERE city_name ILIKE '%  %'
   OR city_name ILIKE ' %'
   OR city_name ILIKE '% ';


-- If these queries return zero rows, there are no leading/trailing
-- spaces or repeated spaces matching the tested patterns.


-- Q9 — Self-join
-- Pairs of different drivers, same pickup location, same calendar day

SELECT
    r1.driver_id AS driver_1,
    r2.driver_id AS driver_2,
    r1.pickup_location_id,
    DATE(r1.pickup_datetime) AS ride_date
FROM rides r1
JOIN rides r2
    ON r1.pickup_location_id = r2.pickup_location_id
    AND DATE(r1.pickup_datetime) = DATE(r2.pickup_datetime)
    AND r1.driver_id < r2.driver_id
ORDER BY ride_date, r1.pickup_location_id;


-- Q10 — Design challenge: promo codes
--
-- Instead of storing promo_code_1, promo_code_2, promo_code_3,
-- etc. directly in the rides table, create separate tables.
--
-- promo_codes
--   promo_code_id  PRIMARY KEY
--   code           UNIQUE
--   discount_type
--   discount_value
--
-- ride_promos
--   ride_id        FOREIGN KEY -> rides(ride_id)
--   promo_code_id  FOREIGN KEY -> promo_codes(promo_code_id)
--   PRIMARY KEY (ride_id, promo_code_id)
--
-- This creates a many-to-many relationship between rides and
-- promo codes if a ride can use multiple promotions.
--
-- A flat-column approach such as promo_code_1, promo_code_2,
-- promo_code_3 violates normalization principles because the
-- same type of information is repeated across multiple columns.
-- It also creates an arbitrary limit on how many promo codes
-- can be stored and makes querying, updating, and maintaining
-- the data more difficult.