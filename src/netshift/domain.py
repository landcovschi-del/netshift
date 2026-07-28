"""Domain model.

This is the core. No files, no database, no HTTP here — only types and rules.
The closest analogy from C# is the Domain layer in Clean Architecture: entities
and value objects that reference nothing outside themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProjectStyle(StrEnum):
    """The format of a .csproj file.

    LEGACY -- the old verbose format with
              <Import Project="...Microsoft.CSharp.targets" />
    SDK    -- the modern <Project Sdk="Microsoft.NET.Sdk">
    """

    LEGACY = "legacy"
    SDK = "sdk"


class Severity(StrEnum):
    """How much a finding gets in the way of migrating."""

    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class RefKind(StrEnum):
    """Where a dependency comes from.

    PACKAGE  -- <PackageReference>, i.e. NuGet.
    ASSEMBLY -- <Reference>, an assembly from the GAC or from disk. A Framework
                leftover: those routinely omit the version and that is normal,
                so the "pin your versions" rule does not apply to them.
    """

    PACKAGE = "package"
    ASSEMBLY = "assembly"


@dataclass(frozen=True, slots=True)
class PackageRef:
    """A project dependency.

    frozen=True makes the object immutable, which turns it into a value object
    in the DDD sense: two PackageRefs with equal fields are equal.
    In C# this would be `record PackageRef(string Name, string? Version)`.
    """

    name: str
    version: str | None = None
    kind: RefKind = RefKind.PACKAGE

    def __str__(self) -> str:
        return f"{self.name} {self.version}" if self.version else self.name


@dataclass(frozen=True, slots=True)
class Finding:
    """One observation about a project: what we found, how bad, what to do."""

    code: str
    message: str
    severity: Severity = Severity.INFO
    hint: str | None = None


@dataclass(slots=True)
class ProjectReport:
    """The result of inspecting a single .csproj."""

    name: str
    style: ProjectStyle
    target_frameworks: list[str] = field(default_factory=list)
    packages: list[PackageRef] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.BLOCKER]

    @property
    def is_migratable(self) -> bool:
        """Whether the project can move without manual intervention."""
        return not self.blockers


# Frameworks Microsoft no longer supports.
_DEAD_FRAMEWORKS = frozenset({"net40", "net45", "net451", "net452", "net46", "net461"})

# .NET Framework namespaces with no direct counterpart in .NET 8+.
# Matching is by prefix, which is a known simplification -- see docs/roadmap.md.
_WINDOWS_ONLY_MARKERS = frozenset(
    {"System.Web", "System.ServiceModel", "System.Drawing", "System.Configuration.Install"}
)


def analyse(report: ProjectReport) -> ProjectReport:
    """Run the rules over a parsed project and fill in its findings.

    A pure function over data: no I/O, so it can be tested without mocks,
    files or a database. Returns the same object to keep call chains readable.
    """
    findings: list[Finding] = []

    if report.style is ProjectStyle.LEGACY:
        findings.append(
            Finding(
                code="NS001",
                message="Project uses the old csproj format",
                severity=Severity.WARNING,
                hint='Move to SDK-style: <Project Sdk="Microsoft.NET.Sdk">',
            )
        )

    if not report.target_frameworks:
        findings.append(
            Finding(
                code="NS002",
                message="Target framework could not be determined",
                severity=Severity.BLOCKER,
                hint="Check <TargetFrameworkVersion> or <TargetFramework>",
            )
        )

    for tfm in report.target_frameworks:
        if tfm.lower() in _DEAD_FRAMEWORKS:
            findings.append(
                Finding(
                    code="NS003",
                    message=f"Framework {tfm} is out of support",
                    severity=Severity.BLOCKER,
                    hint="Target net8.0 or newer for anything new",
                )
            )

    for pkg in report.packages:
        if any(pkg.name.startswith(marker) for marker in _WINDOWS_ONLY_MARKERS):
            findings.append(
                Finding(
                    code="NS004",
                    message=f"{pkg.name} is tied to Windows and .NET Framework",
                    severity=Severity.BLOCKER,
                    hint="Needs a replacement: no counterpart in cross-platform .NET",
                )
            )
        elif pkg.version is None and pkg.kind is RefKind.PACKAGE:
            findings.append(
                Finding(
                    code="NS005",
                    message=f"Dependency {pkg.name} has no version",
                    severity=Severity.WARNING,
                    hint="The build is not reproducible -- pin the version",
                )
            )

    report.findings = findings
    return report
