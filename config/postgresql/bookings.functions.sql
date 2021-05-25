SET search_path TO bookings,public;

CREATE FUNCTION bookings.qty(aircraft_code char, fare_conditions varchar)
RETURNS bigint AS $$
  SELECT count(*)
  FROM bookings.flights f
    JOIN bookings.boarding_passes bp ON bp.flight_id = f.flight_id
    JOIN bookings.seats s ON s.aircraft_code = f.aircraft_code AND s.seat_no = bp.seat_no
  WHERE f.aircraft_code = qty.aircraft_code AND s.fare_conditions = qty.fare_conditions;
$$ STABLE LANGUAGE sql;


CREATE FUNCTION bookings.report()
RETURNS TABLE(model text, economy bigint, comfort bigint, business bigint)
AS $$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT a.aircraft_code, a.model FROM bookings.aircrafts a ORDER BY a.model LOOP
    report.model := r.model;
    report.economy := qty(r.aircraft_code, 'Economy');
    report.comfort := qty(r.aircraft_code, 'Comfort');
    report.business := qty(r.aircraft_code, 'Business');
    RETURN NEXT;
  END LOOP;
END;
$$ STABLE LANGUAGE plpgsql;

CREATE USER qpt_02_query_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_03_seqscan_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_04_indexscan_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_05_bitmapscan_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_06_nestloop_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_07_hashjoin_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_08_mergejoin_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_09_statistics_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_10_profiling_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_11_technics_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_transaction_user WITH ENCRYPTED PASSWORD 'pass';
CREATE USER qpt_idle_user WITH ENCRYPTED PASSWORD 'pass';

CREATE ROLE demo_users;

GRANT demo_users TO 
qpt_02_query_user, 
qpt_03_seqscan_user, 
qpt_04_indexscan_user, 
qpt_05_bitmapscan_user, 
qpt_06_nestloop_user,
qpt_07_hashjoin_user,
qpt_08_mergejoin_user,
qpt_09_statistics_user,
qpt_10_profiling_user,
qpt_11_technics_user,
qpt_transaction_user,
qpt_idle_user;


GRANT USAGE ON SCHEMA bookings TO demo_users;
GRANT ALL ON TABLE bookings.aircrafts_data TO demo_users;
GRANT ALL ON TABLE bookings.airports_data TO demo_users;
GRANT ALL ON TABLE bookings.boarding_passes TO demo_users;
GRANT ALL ON TABLE bookings.bookings TO demo_users;
GRANT ALL ON TABLE bookings.flights TO demo_users;
GRANT ALL ON TABLE bookings.seats TO demo_users;
GRANT ALL ON TABLE bookings.ticket_flights TO demo_users;
GRANT ALL ON TABLE bookings.tickets TO demo_users;
GRANT ALL ON TABLE bookings.aircrafts TO demo_users;
GRANT ALL ON TABLE bookings.airports TO demo_users;
GRANT ALL ON TABLE bookings.flights_v TO demo_users;
GRANT ALL ON TABLE bookings.routes TO demo_users;
GRANT ALL ON FUNCTION bookings.lang() TO demo_users;
GRANT ALL ON FUNCTION bookings.now() TO demo_users;
GRANT ALL ON FUNCTION bookings.qty(bpchar,varchar) TO demo_users;
GRANT ALL ON FUNCTION bookings.report() TO demo_users;
GRANT ALL ON SEQUENCE bookings.flights_flight_id_seq TO demo_users;

