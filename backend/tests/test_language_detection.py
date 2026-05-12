from __future__ import annotations

import pytest
from detectors.project_detector import ProjectDetector
from models.contracts import ProjectType


class TestGoDetection:
    def test_detect_go(self, go_project: str):
        info = ProjectDetector(go_project).detect()
        assert ProjectType.GO in info.types
        assert info.has_go_mod is True
        assert "Gin" in info.detected_frameworks

    def test_go_no_sum(self, go_project: str):
        info = ProjectDetector(go_project).detect()
        assert info.has_go_mod is True


class TestRustDetection:
    def test_detect_rust(self, rust_project: str):
        info = ProjectDetector(rust_project).detect()
        assert ProjectType.RUST in info.types
        assert info.has_cargo_toml is True
        assert "Actix" in info.detected_frameworks
        assert "Tokio" in info.detected_frameworks
        assert "Serde" in info.detected_frameworks

    def test_rust_no_lockfile(self, rust_project: str):
        info = ProjectDetector(rust_project).detect()
        assert info.has_cargo_toml is True


class TestJavaDetection:
    def test_detect_java(self, java_project: str):
        info = ProjectDetector(java_project).detect()
        assert ProjectType.JAVA in info.types
        assert info.has_pom_xml is True
        assert "Spring" in info.detected_frameworks


class TestRubyDetection:
    def test_detect_ruby(self, ruby_project: str):
        info = ProjectDetector(ruby_project).detect()
        assert ProjectType.RUBY in info.types
        assert info.has_gemfile is True
        assert "Rails" in info.detected_frameworks
        assert "RSpec" in info.detected_frameworks
        assert "Sidekiq" in info.detected_frameworks


class TestPhpDetection:
    def test_detect_php(self, php_project: str):
        info = ProjectDetector(php_project).detect()
        assert ProjectType.PHP in info.types
        assert info.has_composer_json is True
        assert "Laravel" in info.detected_frameworks
        assert "PHPUnit" in info.detected_frameworks


class TestCsharpDetection:
    def test_detect_csharp(self, csharp_project: str):
        info = ProjectDetector(csharp_project).detect()
        assert ProjectType.CSHARP in info.types
        assert info.has_csproj is True


class TestDartDetection:
    def test_detect_dart(self, dart_project: str):
        info = ProjectDetector(dart_project).detect()
        assert ProjectType.DART in info.types
        assert info.has_pubspec_yaml is True
        assert "Flutter" in info.detected_frameworks
        assert "Riverpod" in info.detected_frameworks
