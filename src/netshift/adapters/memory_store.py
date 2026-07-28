"""ReportStore adapter: everything in process memory.

Not a stub for tests but the real default: with no Docker installed, netshift
is fully usable. When Postgres arrives, one line in the factory changes and
neither domain nor cli notices.
"""

from __future__ import annotations

from datetime import UTC, datetime

from netshift.domain import ProjectReport


class InMemoryReportStore:
    """Implements the ports.ReportStore protocol."""

    def __init__(self) -> None:
        self._items: dict[str, ProjectReport] = {}

    def save(self, report: ProjectReport) -> None:
        self._items[report.name] = report

    def get(self, name: str) -> ProjectReport | None:
        return self._items.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._items)


class SystemClock:
    """Implements the ports.Clock protocol on top of the system clock."""

    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")
