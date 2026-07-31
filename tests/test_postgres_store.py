from collections.abc import Iterator

import psycopg
import pytest

from netshift.adapters.postgres_store import PostgresReportStore
from netshift.config import load_settings
from tests.test_ports import assert_store_contract

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