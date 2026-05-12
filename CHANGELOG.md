# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
