-- Week 1 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.

-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount
select
	ride_id,
	driver_name,
	passenger_name,
	fare_amount
from
	rides
where
	pickup_city = 'Kathmandu'
	and dropoff_city = 'Pokhara'
	and ride_status = 'completed';


-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending

select driver_name, passenger_name, fare_amount from rides
order by fare_amount desc 
limit 5;

-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive

SELECT *
FROM rides
WHERE driver_name LIKE Lower('%shrestha%');

-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides

SELECT
    COUNT(*) AS total_rides,
    COUNT(rating) AS rated_rides,
    COUNT(*) - COUNT(rating) AS unrated_rides
FROM rides;

-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods

SELECT ride_id, driver_name, payment_method FROM rides
WHERE payment_method != 'cash'
   OR payment_method IS NULL;

-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc
SELECT
    pickup_city,
    COUNT(*) AS total_rides,
    SUM(fare_amount) AS total_revenue,
    ROUND(AVG(fare_amount), 2) AS avg_fare
FROM rides
GROUP BY pickup_city
ORDER BY total_revenue DESC;


-- Q7 — Ride outcomes by status (Intermediate · Aggregation)
-- ride_status, ride_count, avg_distance_km (2 decimals) — sorted by ride_count desc
select  ride_status, count (*) as ride_count, 
round(avg(ride_distance_km), 2) as avg_distance_km from rides
group by ride_status 
order by ride_count desc;


-- Q8 — A new driver's first ride (Basic–Intermediate · DML)
-- 8a. INSERT the new ride (ride_id 9001, rating NULL)
INSERT INTO rides(
    ride_id,driver_name, passenger_name, pickup_city, dropoff_city,
     fare_amount, ride_distance_km, ride_status, requested_at, completed_at,
     rating, payment_method)
 values(
 9001,
 'Sunita Gurung',
 'Rajan Thapa',
 'Lalitpur',
 'Bhaktapur',
 350.00,
 12.40,
 'completed',
 '2026-09-15 12:10:03',
 '2026-09-15 13:30:23', 
 NULL,
 'cash');


-- 8b. UPDATE the rating to 4.8 for ride_id 9001
update rides 
   set rating = 4.8 where  ride_id = 9001;


-- Q9 — Locking down payment methods (Intermediate · DDL)
-- 9a. ALTER TABLE to restrict payment_method to a fixed set of values
ALTER TABLE rides
ADD CONSTRAINT payment_method_check
CHECK (
    payment_method IS NULL

-- 9b. INSERT using an invalid payment method — note the error you'd expect in a comment

----

-- Q10 — Rides priced above the platform average (Basic · Subquery)
-- ride_id, driver_name, fare_amount — fare_amount above the average of ALL rides (via subquery)

SELECT
    ride_id,
    driver_name,
    fare_amount
FROM rides
WHERE fare_amount > (
    SELECT AVG(fare_amount)
    FROM rides
);