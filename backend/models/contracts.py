from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ProjectType(str, Enum):
    NEXTJS = "nextjs"
    REACT = "react"
    NODEJS = "nodejs"
    EXPRESS = "express"
    FASTAPI = "fastapi"
    FLASK = "flask"
    DJANGO = "django"
    PYTHON = "python"
    EPL = "epl"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    KOTLIN = "kotlin"
    SCALA = "scala"
    RUBY = "ruby"
    PHP = "php"
    CSHARP = "csharp"
    SWIFT = "swift"
    DART = "dart"
    ELIXIR = "elixir"
    C = "c"
    CPP = "cpp"
    PERL = "perl"
    LUA = "lua"
    HASKELL = "haskell"
    CLOJURE = "clojure"
    DOCKER = "docker"
    UNKNOWN = "unknown"


class ProjectInfo(BaseModel):
    types: list[ProjectType]
    root_path: str
    name: str
    has_package_json: bool = False
    has_requirements_txt: bool = False
    has_pyproject_toml: bool = False
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_env_file: bool = False
    has_env_example: bool = False
    has_readme: bool = False
    has_gitignore: bool = False
    has_epl_files: bool = False
    has_go_mod: bool = False
    has_cargo_toml: bool = False
    has_pom_xml: bool = False
    has_build_gradle: bool = False
    has_gemfile: bool = False
    has_composer_json: bool = False
    has_csproj: bool = False
    has_sln: bool = False
    has_package_swift: bool = False
    has_pubspec_yaml: bool = False
    has_mix_exs: bool = False
    has_makefile: bool = False
    has_cmakelists: bool = False
    has_cabal: bool = False
    has_stack_yaml: bool = False
    detected_frameworks: list[str] = Field(default_factory=list)
    runtime_versions: dict[str, Optional[str]] = Field(default_factory=dict)


class AutoFix(BaseModel):
    id: str
    description: str
    command: Optional[str] = None
    file_create: Optional[dict[str, str]] = None
    file_edit: Optional[dict[str, str]] = None


class Issue(BaseModel):
    id: str
    analyzer: str
    severity: Severity
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    fix: Optional[AutoFix] = None


class ScoreBreakdown(BaseModel):
    dependency_hygiene: float = 0.0
    docs_quality: float = 0.0
    setup_readiness: float = 0.0
    security: float = 0.0
    environment_completeness: float = 0.0


class HealthScore(BaseModel):
    total: float = 0.0
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    grade: str = "F"


class ScanRequest(BaseModel):
    root_path: str
    analyzers: Optional[list[str]] = None
    incremental: bool = False


class ScanResult(BaseModel):
    project_info: ProjectInfo
    issues: list[Issue] = Field(default_factory=list)
    health_score: HealthScore = Field(default_factory=HealthScore)
    scan_duration_ms: float = 0.0
    timestamp: str = ""


class AutoFixRequest(BaseModel):
    root_path: str
    fix_ids: list[str] = Field(max_length=50)


class AutoFixResult(BaseModel):
    applied: list[str] = Field(default_factory=list)
    failed: list[dict[str, str]] = Field(default_factory=list)


class BackendStatus(BaseModel):
    status: str = "ok"
    version: str = "0.3.2"
    analyzers: list[str] = Field(default_factory=list)
