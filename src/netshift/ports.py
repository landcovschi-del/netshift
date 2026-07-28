"""Ports -- the boundary between the core and the outside world.

A port describes WHAT the system needs from outside, never WHO provides it.
Implementations live in adapters/. The core (domain.py) imports only from here,
so swapping Postgres for SQLite, or a file for HTTP, touches no business logic.

Why Protocol and not an abstract base class
===========================================
In C# you would write `interface IProjectSource` and require every
implementation to declare `: IProjectSource`. That is nominal typing:
compatibility by name.

Protocol gives structural typing -- compatibility by shape. A class satisfies
a protocol if it has the right methods with the right signatures. No
inheritance, no declaration. It is close to duck typing via C# `dynamic`,
except it is checked statically: mypy catches a mismatch before you run.

What that buys in practice:

1. A third-party class becomes an adapter with no wrapper. If some library
   object already has load(path) -> ProjectReport, it satisfies the port as is.
   With an ABC you would need a shim class.

2. A test double is ten lines and imports no production code. No inheritance,
   no mocking library.

3. Dependencies point inward. The adapter knows about the port; the port does
   not know about the adapter. Same rule as Dependency Inversion in Clean
   Architecture, except here you do not have to hold it in your head --
   the edge simply does not exist.

When an ABC is still the right call: when subclasses need shared behaviour
(a template method, a common __init__, validation in the constructor).
Protocol cannot do that. There is no shared behaviour here, so Protocol wins.

runtime_checkable enables isinstance(). It only verifies that methods exist,
not their signatures -- fine as a guard at a boundary, useless as a
replacement for mypy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from netshift.domain import ProjectReport


@runtime_checkable
class ProjectSource(Protocol):
    """Where a project description comes from: file, archive, git repo, API."""

    def load(self, path: Path) -> ProjectReport:
        """Read a project and return a parsed report.

        Raises:
            FileNotFoundError: the source does not exist.
            ValueError: the content could not be parsed.
        """
        ...


@runtime_checkable
class ReportStore(Protocol):
    """Where reports are kept: memory, Postgres, a file, S3."""

    def save(self, report: ProjectReport) -> None:
        """Store a report. Saving the same name again overwrites it."""
        ...

    def get(self, name: str) -> ProjectReport | None:
        """Return the report for a project name, or None if there is none."""
        ...

    def list_names(self) -> list[str]:
        """Names of every stored project."""
        ...


@runtime_checkable
class Clock(Protocol):
    """A source of the current time.

    Looks like overkill right up until you need to test "thirty days from now".
    C# has ISystemClock / TimeProvider for the same reason: a bare DateTime.Now
    in production code makes the test non-deterministic.
    """

    def now_iso(self) -> str:
        """Current time as ISO 8601, UTC."""
        ...
