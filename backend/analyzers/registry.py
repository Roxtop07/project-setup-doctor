from __future__ import annotations

from analyzers.base import BaseAnalyzer


class AnalyzerRegistry:
    _analyzers: dict[str, BaseAnalyzer] = {}

    @classmethod
    def register(cls, analyzer: BaseAnalyzer) -> None:
        cls._analyzers[analyzer.name] = analyzer

    @classmethod
    def get(cls, name: str) -> BaseAnalyzer | None:
        return cls._analyzers.get(name)

    @classmethod
    def list_names(cls) -> list[str]:
        return list(cls._analyzers.keys())

    @classmethod
    def all(cls) -> list[BaseAnalyzer]:
        return list(cls._analyzers.values())


def _register_defaults() -> None:
    from analyzers.env_analyzer import EnvAnalyzer
    from analyzers.dependency_analyzer import DependencyAnalyzer
    from analyzers.readme_analyzer import ReadmeAnalyzer
    from analyzers.security_analyzer import SecurityAnalyzer
    from analyzers.docker_analyzer import DockerAnalyzer

    for cls in [
        EnvAnalyzer,
        DependencyAnalyzer,
        ReadmeAnalyzer,
        SecurityAnalyzer,
        DockerAnalyzer,
    ]:
        AnalyzerRegistry.register(cls())


_register_defaults()
