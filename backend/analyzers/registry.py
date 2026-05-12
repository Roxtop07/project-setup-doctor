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
    from analyzers.epl_analyzer import EplAnalyzer
    from analyzers.go_analyzer import GoAnalyzer
    from analyzers.rust_analyzer import RustAnalyzer
    from analyzers.jvm_analyzer import JvmAnalyzer
    from analyzers.ruby_analyzer import RubyAnalyzer
    from analyzers.php_analyzer import PhpAnalyzer
    from analyzers.csharp_analyzer import CsharpAnalyzer
    from analyzers.swift_analyzer import SwiftAnalyzer
    from analyzers.dart_analyzer import DartAnalyzer
    from analyzers.elixir_analyzer import ElixirAnalyzer
    from analyzers.c_cpp_analyzer import CCppAnalyzer

    for cls in [
        EnvAnalyzer,
        DependencyAnalyzer,
        ReadmeAnalyzer,
        SecurityAnalyzer,
        DockerAnalyzer,
        EplAnalyzer,
        GoAnalyzer,
        RustAnalyzer,
        JvmAnalyzer,
        RubyAnalyzer,
        PhpAnalyzer,
        CsharpAnalyzer,
        SwiftAnalyzer,
        DartAnalyzer,
        ElixirAnalyzer,
        CCppAnalyzer,
    ]:
        AnalyzerRegistry.register(cls())


_register_defaults()
