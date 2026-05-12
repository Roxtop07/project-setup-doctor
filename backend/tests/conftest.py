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
def epl_project() -> str:
    return str(FIXTURES_DIR / "epl_project")


@pytest.fixture
def go_project() -> str:
    return str(FIXTURES_DIR / "go_project")


@pytest.fixture
def rust_project() -> str:
    return str(FIXTURES_DIR / "rust_project")


@pytest.fixture
def java_project() -> str:
    return str(FIXTURES_DIR / "java_project")


@pytest.fixture
def ruby_project() -> str:
    return str(FIXTURES_DIR / "ruby_project")


@pytest.fixture
def php_project() -> str:
    return str(FIXTURES_DIR / "php_project")


@pytest.fixture
def csharp_project() -> str:
    return str(FIXTURES_DIR / "csharp_project")


@pytest.fixture
def dart_project() -> str:
    return str(FIXTURES_DIR / "dart_project")


@pytest.fixture
def broken_project() -> str:
    return str(FIXTURES_DIR / "broken_project")
