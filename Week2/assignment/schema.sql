-- Week 2 Schema & Migration — Answers
-- See sql_assignment.md Part 1 for the full instructions.
-- Rename this file to schema.sql before committing.


-- Step 1: CREATE TABLE statements, in dependency order
-- (locations, drivers, passengers, payment_methods, then trips)
CREATE TABLE locations (
    location_id   SERIAL        PRIMARY KEY,
    city_name     VARCHAR(100)   NOT NULL UNIQUE
);

CREATE TABLE drivers (
    driver_id     SERIAL        PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL
);

CREATE TABLE passengers (
    passenger_id     SERIAL        PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL
);

CREATE TABLE payment_methods (
	payment_method_id SERIAL PRIMARY KEY,
	name VARCHAR(30) NOT NULL UNIQUE 
);

CREATE TABLE trips (
    trip_id              SERIAL        PRIMARY KEY,
    driver_id            INTEGER       NOT NULL REFERENCES drivers(driver_id),
    passenger_id         INTEGER       NOT NULL REFERENCES passengers(passenger_id),
    pickup_location_id   INTEGER       NOT NULL REFERENCES locations(location_id),
    dropoff_location_id  INTEGER       NOT NULL REFERENCES locations(location_id),
    fare_amount          NUMERIC(10,2) NOT NULL CHECK (fare_amount > 0),
    distance_km          NUMERIC(6,2)  NOT NULL,
    status               varchar(50)   NOT NULL CHECK (status IN ('completed','cancelled','no_show')),
    requested_at         TIMESTAMP     NOT NULL,
    completed_at         TIMESTAMP,
    rating               NUMERIC(2,1)  CHECK (rating BETWEEN 1.0 AND 5.0),
    payment_method_id    INTEGER       REFERENCES payment_methods(payment_method_id)
);




-- Step 2: populate drivers and passengers (INSERT ... SELECT DISTINCT ... FROM rides, cleaned names)
-- Remember: INITCAP(TRIM(REGEXP_REPLACE(name, '\s+', ' ', 'g')))

---drivers
insert
	into
	drivers (name)
select distinct initcap(trim(regexp_replace(
r.driver_name, '\s+', ' ', 'g')))from rides r;

---passengers
insert
	into
	passengers (name)
select distinct initcap(trim(regexp_replace(
r.passenger_name, '\s+', ' ', 'g')))from rides r;


-- Step 3: populate locations (UNION of pickup_city and dropoff_city, from rides)
insert into locations(city_name)
select distinct(pickup_city)from rides r
union 
select distinct(dropoff_city)from rides r;


-- Step 4: populate payment_methods (from rides)

insert into payment_methods(name)
select distinct payment_method
from rides where payment_method is not null;

-- Step 5: migrate rides into trips (scalar subqueries resolve each ID)

INSERT INTO trips (
	driver_id,
	passenger_id,
	pickup_location_id,
	dropoff_location_id,
	fare_amount,
	distance_km,
	status,
	requested_at,
	completed_at,
	rating,
	payment_method_id
)
SELECT 
(SELECT  driver_id 
	FROM drivers d 
	 WHERE d.name = INITCAP(TRIM(REGEXP_REPLACE(r.driver_name, '\s+', ' ', 'g')))) driver_id,
(SELECT  passenger_id 
		FROM passengers p
	 WHERE p.name = INITCAP(TRIM(REGEXP_REPLACE(r.passenger_name, '\s+', ' ', 'g')))) passenger_id,
(SELECT  location_id  
		FROM locations p
	 WHERE p.city_name = r.pickup_city ) pickup_location_id,
(SELECT  location_id  
		FROM locations p
	 WHERE p.city_name = r.dropoff_city ) dropoff_location_id,
fare_amount,
ride_distance_km,
ride_status,
requested_at,
completed_at,
rating,
(SELECT  payment_method_id  
		FROM payment_methods pm  
		WHERE pm.name = r.payment_method  ) payment_method_id
FROM rides r;

-- Step 6: verification query — COUNT(*) FROM trips should equal COUNT(*) FROM rides

SELECT COUNT(*) FROM trips;

-- Step 7: manually insert one driver with no matching trip (needed for Q2)
insert into drivers(name)
values('Sujata Khanal');
