"""ReportStore adapter backed by Postgres.

The module always imports; psycopg is imported inside the constructor instead.
That way the rest of the project works with no driver and no Docker: the only
thing that fails is the caller who asked for NETSHIFT_STORE=postgres, and it
fails with a clear message rather than an ImportError at startup.

The schema is created on first connection. Good enough for a learning project;
the moment a second table or a column change shows up you need a migration
tool (Alembic -- the .NET equivalent is EF Core Migrations).
"""

from __future__ import annotations

import json
from typing import Any

from netshift.domain import Finding, PackageRef, ProjectReport, ProjectStyle, RefKind, Severity

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    name        TEXT PRIMARY KEY,
    payload     JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_UPSERT = """
INSERT INTO reports (name, payload, updated_at)
VALUES (%s, %s, now())
ON CONFLICT (name) DO UPDATE
    SET payload = EXCLUDED.payload,
        updated_at = now();
"""


def _to_dict(report: ProjectReport) -> dict[str, Any]:
    return {
        "name": report.name,
        "style": str(report.style),
        "target_frameworks": report.target_frameworks,
        "packages": [
            {"name": p.name, "version": p.version, "kind": str(p.kind)} for p in report.packages
        ],
        "findings": [
            {"code": f.code, "message": f.message, "severity": str(f.severity), "hint": f.hint}
            for f in report.findings
        ],
    }


def _from_dict(raw: dict[str, Any]) -> ProjectReport:
    return ProjectReport(
        name=raw["name"],
        style=ProjectStyle(raw["style"]),
        target_frameworks=list(raw.get("target_frameworks", [])),
        packages=[
            PackageRef(
                name=p["name"],
                version=p.get("version"),
                kind=RefKind(p.get("kind", "package")),
            )
            for p in raw.get("packages", [])
        ],
        findings=[
            Finding(
                code=f["code"],
                message=f["message"],
                severity=Severity(f["severity"]),
                hint=f.get("hint"),
            )
            for f in raw.get("findings", [])
        ],
    )


class PostgresReportStore:
    """Implements the ports.ReportStore protocol."""

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "psycopg driver is not installed. Run: uv sync --extra postgres"
            ) from exc

        self._psycopg = psycopg
        self._dsn = dsn
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> Any:
        return self._psycopg.connect(self._dsn, autocommit=True)

    def save(self, report: ProjectReport) -> None:
        with self._connect() as conn:
            conn.execute(_UPSERT, (report.name, json.dumps(_to_dict(report))))

    def get(self, name: str) -> ProjectReport | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM reports WHERE name = %s", (name,)).fetchone()
        return _from_dict(row[0]) if row else None

    def list_names(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM reports ORDER BY name").fetchall()
        return [row[0] for row in rows]
