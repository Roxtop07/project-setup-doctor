# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-05-13

### Fixed

- **Backend startup failures across all platforms** — resolved "backend failed to start" errors in production
- **macOS Gatekeeper blocking**: quarantine attribute now removed recursively from entire binary directory, not just the main executable — fixes blocked .dylib/.so files
- **File permissions**: execute permissions now fixed recursively for all files in the binary bundle
- **Python fallback path**: corrected path resolution for production VSIX installs where backend source may be at different relative paths
- **Port conflict detection**: pre-checks if the configured port is already in use before attempting to start, with actionable error message
- **Python dependency validation**: checks that uvicorn, fastapi, and pydantic are importable before spawning Python fallback
- **Windows Python discovery**: now also tries `py -3` (Windows Python Launcher) in addition to `python3`/`python`
- **Immediate exit detection**: if the backend process exits immediately, fails fast with diagnosis instead of waiting the full timeout

### Added

- **linux-arm64 distribution** — new platform support for Raspberry Pi, AWS Graviton, and other ARM64 Linux systems
- **Universal VSIX package** — fallback package without bundled binary for unsupported platforms (uses Python)
- **Platform-specific error diagnostics** — exit codes and stderr are analyzed to provide actionable troubleshooting:
  - macOS: Gatekeeper/quarantine guidance with System Settings instructions
  - Windows: Defender/SmartScreen guidance with Security settings path
  - Linux: Permission and shared library (ldd) guidance
- **Startup progress logging** — logs progress every 5 seconds during backend startup
- **Troubleshoot button** — crash dialog now includes direct link to GitHub issues
- **Increased startup timeout** — 30 seconds (was 15) to accommodate slower machines

### Changed

- Build matrix now produces **6 distributions**: darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64, universal
- Build script now supports Windows (MSYS/MinGW/Cygwin) and applies recursive chmod

## [0.3.0] - 2026-05-12

### Added

- **Full multi-language support** — project detection, dependency analysis, and health scanning for all major programming languages
- **New project types**: Go, Rust, Java, Kotlin, Scala, Ruby, PHP, C#/.NET, Swift, Dart/Flutter, Elixir, C/C++, EPL, Perl, Lua, Haskell, Clojure
- **New analyzers** with lockfile, runtime, and .gitignore checks:
  - Go: go.sum lockfile, Go compiler, binary gitignore
  - Rust: Cargo.lock, rustc compiler, target/ gitignore
  - JVM (Java/Kotlin/Scala): Java runtime, Gradle/Maven wrapper, build artifact gitignore
  - Ruby: Gemfile.lock, Ruby runtime, .ruby-version
  - PHP: composer.lock, vendor/ directory, PHP runtime, vendor gitignore
  - C#/.NET: dotnet SDK, bin/obj gitignore
  - Swift: Package.resolved, Swift compiler, .build/ gitignore
  - Dart/Flutter: pubspec.lock, Dart SDK, .dart_tool/build gitignore
  - Elixir: mix.lock, Elixir runtime, _build/deps gitignore
  - C/C++: build system detection (CMake/Make/Meson), compiler check, object file gitignore
  - EPL: eplang dependency, EPL CLI, main.epl entry point, cache gitignore
- **Framework detection** for 50+ frameworks: Gin, Fiber, Echo, Actix, Tokio, Rocket, Axum, Spring, Quarkus, Ktor, Rails, Sinatra, Laravel, Symfony, ASP.NET Core, Blazor, Vapor, Flutter, Phoenix, Ecto, CMake, and more
- **Runtime version detection** for 19 runtimes: node, npm, python, pip, docker, epl, go, rust, cargo, java, ruby, php, dotnet, swift, dart, elixir, gcc, g++, perl
- **Security scanner** now scans 40+ file extensions across all languages for hardcoded secrets
- **Smart .gitignore generation** includes language-specific entries when creating .gitignore
- Extension activates on all supported manifest files (go.mod, Cargo.toml, pom.xml, build.gradle, Gemfile, composer.json, *.csproj, Package.swift, pubspec.yaml, mix.exs, CMakeLists.txt, *.cabal, project.clj)
- File watcher triggers re-scan when any manifest or lockfile changes

## [0.1.0] - 2026-05-12

### Added

- Project type detection for Next.js, React, Node.js, Express, FastAPI, Flask, Django, Python, Docker
- Environment variable validation (missing vars, malformed values, missing runtimes)
- Dependency health scanning for npm and pip (duplicates, unpinned, missing lockfiles)
- README health checker (install instructions, setup sections, env documentation)
- Security scanner (hardcoded secrets, missing .gitignore, dangerous npm scripts)
- Docker analyzer (Dockerfile best practices, missing .dockerignore)
- Weighted health score (0-100) with A-F grading across 5 categories
- Auto-fix system for common issues (create .env.example, generate Dockerfile, install deps)
- VS Code sidebar webview with score ring, issue list, and fix buttons
- Status bar health score indicator
- Problems panel integration via diagnostics
- JSON report export
- File watcher with debounced re-scanning
- Scan caching with 60-second TTL
- Multi-root workspace support
- Extensible analyzer registry
- FastAPI backend with REST API endpoints
