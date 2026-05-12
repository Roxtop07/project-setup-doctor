from __future__ import annotations

import os
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def node_project() -> str:
    return str(FIXTURES_DIR / "node_project")


@pytest.fixture
def python_project() -> str:
    return str(FIXTURES_DIR / "python_project")


@pytest.fixture
def nextjs_project() -> str:
    return str(FIXTURES_DIR / "nextjs_project")


@pytest.fixture
def fullstack_project() -> str:
    return str(FIXTURES_DIR / "fullstack_project")


@pytest.fixture
def empty_project() -> str:
    return str(FIXTURES_DIR / "empty_project")


@pytest.fixture
def broken_project() -> str:
    return str(FIXTURES_DIR / "broken_project")
