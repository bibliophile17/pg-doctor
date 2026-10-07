# Ticket 1: "Looking up one device's recent readings is slow"

**Reported symptom:** A dashboard widget showing the latest readings for one device (`device_id = 42`, last 3 days) feels slow, taking roughly a quarter of a second per request.

## Investigation

1. Ran the query through PG Doctor and saved the plan:
   `python -m pgdoctor diagnose --file queries/before/q1_device_lookup.sql`
2. Compared two timings: the time measured from the client, and the server-side execution time from `EXPLAIN (ANALYZE, BUFFERS)`.
3. Client-measured time was about 266 ms. Server-side execution time was only 1.5 ms.

## Root cause

The database was not the bottleneck. `ORDER BY time DESC LIMIT 100` lets the query stop early, so it was already fast. The remaining ~265 ms was network round-trip time between the client and the cloud database.

## Fix

- Run the application in the same region as the database, and reuse connections (a connection pool) so the connection handshake is not paid on every request.
- Optional: the `(device_id, time DESC)` index (`sql/03_fixes.sql`) still helps, lowering server time from 1.5 ms to 0.1 ms.

## Evidence

- Server-side execution time: 1.5 ms before, 0.1 ms after the index.
- Client-measured time from my laptop stayed at about 266-295 ms both before and after, which points at the network and not the query.
- Data set: 720,050 rows, 50 devices, 5 days, on a free Tiger Cloud service.

## Customer-facing explanation

Your query itself finishes in a couple of milliseconds, so the database is doing its job. Most of the time you see is the trip between your application and the database. Hosting your application in the same region as the database, and keeping connections open between requests, will remove most of that delay. We also added an index that makes the lookup a little faster still.
