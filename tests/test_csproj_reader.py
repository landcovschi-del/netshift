"""Tests for the adapter that reads .csproj files from disk."""

from __future__ import annotations

from pathlib import Path

import pytest

from netshift.adapters.csproj_reader import CsprojReader
from netshift.domain import ProjectStyle, RefKind


def test_reads_legacy_format(legacy: Path) -> None:
    report = CsprojReader().load(legacy)

    assert report.name == "Legacy"
    assert report.style is ProjectStyle.LEGACY
    # v4.5 from <TargetFrameworkVersion> becomes the net45 moniker.
    assert report.target_frameworks == ["net45"]
    assert not report.is_migratable

    names = {p.name for p in report.packages}
    assert {"System.Web", "System.ServiceModel", "Newtonsoft.Json"} <= names
    assert all(p.kind is RefKind.ASSEMBLY for p in report.packages)

    # The version is pulled out of "System.Web, Version=4.0.0.0, Culture=..."
    system_web = next(p for p in report.packages if p.name == "System.Web")
    assert system_web.version == "4.0.0.0"


def test_reads_sdk_format(modern: Path) -> None:
    report = CsprojReader().load(modern)

    assert report.style is ProjectStyle.SDK
    assert report.target_frameworks == ["net8.0"]
    assert all(p.kind is RefKind.PACKAGE for p in report.packages)
    assert report.findings == []
    assert report.is_migratable


def test_reads_multi_targeting_and_child_version(mixed: Path) -> None:
    report = CsprojReader().load(mixed)

    assert report.target_frameworks == ["net8.0", "net472"]

    dapper = next(p for p in report.packages if p.name == "Dapper")
    assert dapper.version == "2.1.35", "a version in a child <Version> must be read"

    automapper = next(p for p in report.packages if p.name == "AutoMapper")
    assert automapper.version is None
    assert "NS005" in {f.code for f in report.findings}


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        CsprojReader().load(tmp_path / "Nope.csproj")


def test_broken_xml_raises_value_error(tmp_path: Path) -> None:
    broken = tmp_path / "Broken.csproj"
    broken.write_text("<Project><PropertyGroup></Project>", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid XML"):
        CsprojReader().load(broken)


def test_wrong_root_element_raises_value_error(tmp_path: Path) -> None:
    wrong = tmp_path / "Wrong.csproj"
    wrong.write_text("<Solution />", encoding="utf-8")

    with pytest.raises(ValueError, match="expected Project"):
        CsprojReader().load(wrong)
