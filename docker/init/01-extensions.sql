-- Runs exactly once, when the pgdata volume is first created.
-- If you edit this file you need `docker compose down -v`, otherwise Postgres
-- simply will not re-read it. Classic source of "why did nothing happen".

CREATE EXTENSION IF NOT EXISTS vector;
