from __future__ import annotations

from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture
def legacy() -> Path:
    return SAMPLES / "Legacy.csproj"


@pytest.fixture
def modern() -> Path:
    return SAMPLES / "Modern.csproj"


@pytest.fixture
def mixed() -> Path:
    return SAMPLES / "Mixed.csproj"
