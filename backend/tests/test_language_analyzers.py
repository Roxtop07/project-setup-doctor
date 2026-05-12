from __future__ import annotations

import pytest
from detectors.project_detector import ProjectDetector
from analyzers.go_analyzer import GoAnalyzer
from analyzers.rust_analyzer import RustAnalyzer
from analyzers.jvm_analyzer import JvmAnalyzer
from analyzers.ruby_analyzer import RubyAnalyzer
from analyzers.php_analyzer import PhpAnalyzer
from analyzers.csharp_analyzer import CsharpAnalyzer
from analyzers.dart_analyzer import DartAnalyzer


class TestGoAnalyzer:
    @pytest.mark.asyncio
    async def test_go_no_sum(self, go_project: str):
        info = ProjectDetector(go_project).detect()
        issues = await GoAnalyzer().analyze(go_project, info)
        ids = [i.id for i in issues]
        assert "go-no-sum" in ids

    @pytest.mark.asyncio
    async def test_go_gitignore_binary(self, go_project: str):
        info = ProjectDetector(go_project).detect()
        issues = await GoAnalyzer().analyze(go_project, info)
        ids = [i.id for i in issues]
        assert "go-gitignore-binary" in ids

    @pytest.mark.asyncio
    async def test_skips_non_go(self, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await GoAnalyzer().analyze(empty_project, info)
        assert issues == []


class TestRustAnalyzer:
    @pytest.mark.asyncio
    async def test_rust_no_lockfile(self, rust_project: str):
        info = ProjectDetector(rust_project).detect()
        issues = await RustAnalyzer().analyze(rust_project, info)
        ids = [i.id for i in issues]
        assert "rust-no-lockfile" in ids

    @pytest.mark.asyncio
    async def test_rust_gitignore_target(self, rust_project: str):
        info = ProjectDetector(rust_project).detect()
        issues = await RustAnalyzer().analyze(rust_project, info)
        ids = [i.id for i in issues]
        assert "rust-gitignore-target" in ids


class TestJvmAnalyzer:
    @pytest.mark.asyncio
    async def test_java_gitignore_incomplete(self, java_project: str):
        info = ProjectDetector(java_project).detect()
        issues = await JvmAnalyzer().analyze(java_project, info)
        ids = [i.id for i in issues]
        assert "jvm-gitignore-incomplete" in ids

    @pytest.mark.asyncio
    async def test_java_no_maven_wrapper(self, java_project: str):
        info = ProjectDetector(java_project).detect()
        issues = await JvmAnalyzer().analyze(java_project, info)
        ids = [i.id for i in issues]
        assert "jvm-no-maven-wrapper" in ids


class TestRubyAnalyzer:
    @pytest.mark.asyncio
    async def test_ruby_no_lockfile(self, ruby_project: str):
        info = ProjectDetector(ruby_project).detect()
        issues = await RubyAnalyzer().analyze(ruby_project, info)
        ids = [i.id for i in issues]
        assert "ruby-no-lockfile" in ids

    @pytest.mark.asyncio
    async def test_ruby_no_version(self, ruby_project: str):
        info = ProjectDetector(ruby_project).detect()
        issues = await RubyAnalyzer().analyze(ruby_project, info)
        ids = [i.id for i in issues]
        assert "ruby-no-version-file" in ids


class TestPhpAnalyzer:
    @pytest.mark.asyncio
    async def test_php_no_lockfile(self, php_project: str):
        info = ProjectDetector(php_project).detect()
        issues = await PhpAnalyzer().analyze(php_project, info)
        ids = [i.id for i in issues]
        assert "php-no-lockfile" in ids

    @pytest.mark.asyncio
    async def test_php_no_vendor(self, php_project: str):
        info = ProjectDetector(php_project).detect()
        issues = await PhpAnalyzer().analyze(php_project, info)
        ids = [i.id for i in issues]
        assert "php-no-vendor" in ids

    @pytest.mark.asyncio
    async def test_php_gitignore_vendor(self, php_project: str):
        info = ProjectDetector(php_project).detect()
        issues = await PhpAnalyzer().analyze(php_project, info)
        ids = [i.id for i in issues]
        assert "php-gitignore-vendor" in ids


class TestCsharpAnalyzer:
    @pytest.mark.asyncio
    async def test_csharp_gitignore_incomplete(self, csharp_project: str):
        info = ProjectDetector(csharp_project).detect()
        issues = await CsharpAnalyzer().analyze(csharp_project, info)
        ids = [i.id for i in issues]
        assert "csharp-gitignore-incomplete" in ids


class TestDartAnalyzer:
    @pytest.mark.asyncio
    async def test_dart_no_lockfile(self, dart_project: str):
        info = ProjectDetector(dart_project).detect()
        issues = await DartAnalyzer().analyze(dart_project, info)
        ids = [i.id for i in issues]
        assert "dart-no-lockfile" in ids

    @pytest.mark.asyncio
    async def test_dart_gitignore_incomplete(self, dart_project: str):
        info = ProjectDetector(dart_project).detect()
        issues = await DartAnalyzer().analyze(dart_project, info)
        ids = [i.id for i in issues]
        assert "dart-gitignore-incomplete" in ids
