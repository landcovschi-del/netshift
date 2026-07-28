"""Tests for the analysis rules.

No files, no database, no mocks -- analyse() is a pure function and data is
all it needs. This is what you get for keeping I/O out of the core.
"""

from __future__ import annotations

from netshift.domain import (
    PackageRef,
    ProjectReport,
    ProjectStyle,
    RefKind,
    Severity,
    analyse,
)


def _report(**kwargs: object) -> ProjectReport:
    defaults: dict[str, object] = {
        "name": "Test",
        "style": ProjectStyle.SDK,
        "target_frameworks": ["net8.0"],
        "packages": [],
    }
    return ProjectReport(**(defaults | kwargs))  # type: ignore[arg-type]


def test_modern_project_has_no_findings() -> None:
    # A modern SDK project on net8.0 with a pinned version is clean.
    report = analyse(_report(packages=[PackageRef("Serilog", "4.2.0")]))

    assert report.findings == []
    assert report.is_migratable


def test_dead_framework_is_blocker() -> None:
    # net45 is out of support: no migration without manual work.
    report = analyse(_report(style=ProjectStyle.LEGACY, target_frameworks=["net45"]))

    codes = {f.code for f in report.findings}
    assert "NS001" in codes, "old csproj format should raise a warning"
    assert "NS003" in codes, "a dead framework should raise a blocker"
    assert not report.is_migratable


def test_missing_framework_is_blocker() -> None:
    report = analyse(_report(target_frameworks=[]))

    assert [f.code for f in report.findings] == ["NS002"]
    assert report.blockers[0].severity is Severity.BLOCKER


def test_windows_only_dependency_blocks_migration() -> None:
    # System.Web does not exist in cross-platform .NET; it has to be replaced.
    report = analyse(_report(packages=[PackageRef("System.Web", "4.0.0.0", RefKind.ASSEMBLY)]))

    assert [f.code for f in report.findings] == ["NS004"]
    assert not report.is_migratable


def test_version_rule_applies_to_packages_not_assemblies() -> None:
    # A NuGet package with no version is a reproducibility problem.
    # A GAC assembly with no version is normal for Framework -- nothing to flag.
    report = analyse(
        _report(
            packages=[
                PackageRef("AutoMapper", None, RefKind.PACKAGE),
                PackageRef("System.Core", None, RefKind.ASSEMBLY),
            ]
        )
    )

    findings = report.findings
    assert len(findings) == 1, "the version rule must not touch <Reference>"
    assert findings[0].code == "NS005"
    assert findings[0].severity is Severity.WARNING
    assert report.is_migratable, "a warning must not block migration"


def test_package_ref_is_value_object() -> None:
    # frozen=True gives equality by value and hashability -- like a C# record.
    assert PackageRef("Serilog", "4.2.0") == PackageRef("Serilog", "4.2.0")
    assert len({PackageRef("Serilog", "4.2.0"), PackageRef("Serilog", "4.2.0")}) == 1
