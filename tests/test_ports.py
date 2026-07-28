"""Tests that demonstrate the point of Protocol.

The interesting part is FakeStore below. It does not inherit ReportStore, does
not import a single adapter, and uses no mocking library. It is simply a class
of the right shape. mypy checks the match statically; isinstance works at
runtime because the protocols are marked runtime_checkable.
"""

from __future__ import annotations

from netshift.adapters.csproj_reader import CsprojReader
from netshift.adapters.memory_store import InMemoryReportStore, SystemClock
from netshift.domain import ProjectReport, ProjectStyle
from netshift.ports import Clock, ProjectSource, ReportStore


class FakeStore:
    """A ReportStore test double. No inheritance required."""

    def __init__(self) -> None:
        self.saved: list[ProjectReport] = []

    def save(self, report: ProjectReport) -> None:
        self.saved.append(report)

    def get(self, name: str) -> ProjectReport | None:
        return next((r for r in reversed(self.saved) if r.name == name), None)

    def list_names(self) -> list[str]:
        return sorted({r.name for r in self.saved})


class FrozenClock:
    """A Clock test double: time does not move."""

    def now_iso(self) -> str:
        return "2026-01-01T00:00:00+00:00"


def test_adapters_satisfy_their_protocols() -> None:
    # None of these classes lists a protocol among its bases -- compatibility
    # comes from the set of methods, not from the name of a base class.
    assert isinstance(CsprojReader(), ProjectSource)
    assert isinstance(InMemoryReportStore(), ReportStore)
    assert isinstance(SystemClock(), Clock)


def test_test_doubles_satisfy_their_protocols() -> None:
    assert isinstance(FakeStore(), ReportStore)
    assert isinstance(FrozenClock(), Clock)


def test_class_without_required_methods_does_not_satisfy_protocol() -> None:
    class NotAStore:
        def save(self, report: ProjectReport) -> None: ...

    # No get() and no list_names(), so it is not a ReportStore.
    assert not isinstance(NotAStore(), ReportStore)


def test_store_contract_holds_for_both_implementations() -> None:
    """One set of expectations, applied to the real adapter and to the double.

    The technique is called a contract test: when PostgresReportStore arrives,
    adding it to this list is all the coverage it needs.
    """
    report = ProjectReport(name="Contoso", style=ProjectStyle.SDK, target_frameworks=["net8.0"])

    stores: list[ReportStore] = [InMemoryReportStore(), FakeStore()]
    for store in stores:
        assert store.get("Contoso") is None
        assert store.list_names() == []

        store.save(report)

        assert store.get("Contoso") is report
        assert store.list_names() == ["Contoso"]
