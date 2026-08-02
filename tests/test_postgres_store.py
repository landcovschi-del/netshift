from collections.abc import Iterator

import pytest

from netshift.adapters.postgres_store import PostgresReportStore
from netshift.config import load_settings
from tests.test_ports import assert_store_contract

# Not `import psycopg`. The driver is an optional extra, and CI installs with
# a plain `uv sync --locked`, so on a clean machine it is absent. A missing
# module at import time kills collection of this file, and the integration
# marker cannot save it: the marker is read when a test runs, the import when
# the module is collected. The .NET parallel is [Fact(Skip=...)] on a class
# that never loads because an assembly is missing.
psycopg = pytest.importorskip("psycopg")

pytestmark = pytest.mark.integration


@pytest.fixture
def pg_store() -> Iterator[PostgresReportStore]:
    dsn = load_settings().postgres_dsn
    try:
        store = PostgresReportStore(dsn)
    except Exception as exc:
        pytest.skip(f"Postgres is not available: {exc}")
    with psycopg.connect(dsn) as conn:
        conn.execute("TRUNCATE reports")
    yield store



def test_postgres_store_satisfies_the_contract(pg_store: PostgresReportStore) -> None:
    assert_store_contract(pg_store)