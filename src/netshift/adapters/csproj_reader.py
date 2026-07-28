"""ProjectSource adapter: reads .csproj files from disk.

Handles both formats -- the old MSBuild one with a namespace, and SDK-style.

On XML parsing safety: xml.etree in the standard library does not expand
external entities and raises on unknown ones, so classic XXE does not apply
here. For untrusted input (phase 3, files pulled from the internet) switch to
defusedxml, which also covers billion laughs.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from netshift.domain import PackageRef, ProjectReport, ProjectStyle, RefKind, analyse

# Namespace of the legacy format. SDK-style projects have none at all.
_MSBUILD_NS = "http://schemas.microsoft.com/developer/msbuild/2003"

# v4.7.2 -> net472, v4.5 -> net45, v2.0 -> net20
_TFV_RE = re.compile(r"^v(\d+(?:\.\d+)*)$")


def _localname(tag: str) -> str:
    """Strip the {namespace} prefix so the code does not fork on format."""
    return tag.rsplit("}", 1)[-1]


def _tfv_to_moniker(value: str) -> str | None:
    """v4.7.2 -> net472. Returns None if the string is not a version."""
    match = _TFV_RE.match(value.strip())
    if not match:
        return None
    return "net" + match.group(1).replace(".", "")


class CsprojReader:
    """Implements the ports.ProjectSource protocol.

    Note that this class inherits nothing and never mentions ProjectSource.
    Compatibility is decided by shape -- see the explanation in ports.py.
    """

    def load(self, path: Path) -> ProjectReport:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise ValueError(f"{path} is not valid XML: {exc}") from exc

        if _localname(root.tag) != "Project":
            raise ValueError(
                f"{path}: root element is {_localname(root.tag)}, expected Project"
            )

        style = ProjectStyle.SDK if root.get("Sdk") else ProjectStyle.LEGACY

        report = ProjectReport(
            name=path.stem,
            style=style,
            target_frameworks=self._read_frameworks(root),
            packages=self._read_packages(root),
        )
        return analyse(report)

    def _read_frameworks(self, root: ET.Element) -> list[str]:
        frameworks: list[str] = []

        for element in root.iter():
            name = _localname(element.tag)
            text = (element.text or "").strip()
            if not text:
                continue

            if name == "TargetFramework":
                frameworks.append(text)
            elif name == "TargetFrameworks":
                frameworks.extend(part.strip() for part in text.split(";") if part.strip())
            elif name == "TargetFrameworkVersion" and (moniker := _tfv_to_moniker(text)):
                frameworks.append(moniker)

        # dict.fromkeys rather than set: removes duplicates but keeps order.
        return list(dict.fromkeys(frameworks))

    def _read_packages(self, root: ET.Element) -> list[PackageRef]:
        packages: list[PackageRef] = []

        for element in root.iter():
            name = _localname(element.tag)

            if name == "PackageReference":
                include = element.get("Include")
                if not include:
                    continue
                # The version may be an attribute or a child element.
                # Both are legal MSBuild.
                version = element.get("Version")
                if version is None:
                    for child in element:
                        if _localname(child.tag) == "Version" and child.text:
                            version = child.text.strip()
                            break
                packages.append(
                    PackageRef(name=include, version=version, kind=RefKind.PACKAGE)
                )

            elif name == "Reference":
                include = element.get("Include")
                if not include:
                    continue
                # Legacy format packs metadata into the attribute:
                # Include="System.Web, Version=4.0.0.0, Culture=neutral, ..."
                assembly, _, tail = include.partition(",")
                version = None
                for part in tail.split(","):
                    key, _, value = part.partition("=")
                    if key.strip().lower() == "version":
                        version = value.strip()
                        break
                packages.append(
                    PackageRef(name=assembly.strip(), version=version, kind=RefKind.ASSEMBLY)
                )

        return packages
