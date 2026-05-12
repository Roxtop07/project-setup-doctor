# SecureCode

A cross-IDE extension that scans repositories and detects setup, environment, dependency, and configuration problems before you run the project.

Works with VS Code, Cursor, Windsurf, VSCodium, and other VS Code ecosystem editors.

## Features

- **Project Type Detection** — auto-detects Next.js, React, Node.js, Express, FastAPI, Flask, Django, Python, Docker
- **Environment Validator** — checks for missing `.env` variables, malformed values, missing runtimes
- **Dependency Health Scanner** — detects outdated, duplicate, unpinned, and missing packages (npm + pip)
- **README Health Checker** — verifies install instructions, setup sections, env var documentation
- **Security Scanner** — finds hardcoded secrets, missing `.gitignore` entries, dangerous scripts
- **Docker Analyzer** — checks Dockerfile best practices, missing `.dockerignore`
- **Health Score** — weighted 0-100 score with A-F grading across 5 categories
- **Auto Fixes** — one-click fixes for common issues (create `.env.example`, install deps, generate Dockerfile)
- **JSON Export** — export full scan results for CI integration



## Architecture

```
securecode/
├── extension/          # VS Code extension (TypeScript)
│   ├── src/
│   │   ├── commands/   # Scan, AutoFix, HealthReport, GenerateEnv, Export
│   │   ├── providers/  # Sidebar, StatusBar, Diagnostics
│   │   └── services/   # BackendClient, BackendManager, ScanCache
│   └── media/          # Icons
├── backend/            # Analysis engine (Python/FastAPI)
│   ├── api/            # REST routes
│   ├── analyzers/      # Modular analyzers (env, deps, readme, security, docker)
│   ├── detectors/      # Project type detection
│   ├── scoring/        # Health score engine
│   └── models/         # Pydantic contracts
├── shared/             # API type definitions (TS + Python)
└── docs/               # Documentation
```

## Prerequisites

- Node.js >= 18
- Python >= 3.10
- npm
- pip

## Quick Start

### 1. Install backend dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install extension dependencies

```bash
cd extension
npm install
```

### 3. Run in development mode

Start the backend:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 18120 --reload
```

In a separate terminal, build and watch the extension:

```bash
cd extension
npm run watch
```

Then press **F5** in VS Code to launch the Extension Development Host.

### 4. Using the extension

1. Open a project in VS Code
2. The extension auto-scans on workspace open (configurable)
3. Use the **SecureCode** icon in the Activity Bar to view the sidebar
4. Run commands from the Command Palette: `SecureCode: Scan Project`

## Commands

| Command | Description |
|---------|-------------|
| `SecureCode: Scan Project` | Full project analysis |
| `SecureCode: Show Health Report` | Open detailed health report |
| `SecureCode: Run Auto Fixes` | Apply available auto-fixes |
| `SecureCode: Generate Env Template` | Create `.env.example` from code |
| `SecureCode: Export JSON Report` | Save scan results as JSON |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `secureCode.backendPort` | `18120` | Backend server port |
| `secureCode.autoScanOnOpen` | `true` | Auto-scan on workspace open |
| `secureCode.scanDebounceMs` | `2000` | Debounce for file-change re-scans |
| `secureCode.enableTelemetry` | `false` | Anonymous telemetry (off by default) |
| `secureCode.enableAI` | `false` | AI analysis (disabled by default) |
| `secureCode.excludePaths` | `[...]` | Paths excluded from scanning |

## API Endpoints

The backend runs on `http://127.0.0.1:18120` by default.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Backend status and registered analyzers |
| `POST` | `/scan` | Full project scan |
| `POST` | `/health-score` | Health score calculation |
| `POST` | `/project-info` | Project type detection only |
| `POST` | `/autofix` | Apply auto-fixes |

## Building for Production

### Package the extension

```bash
cd extension
npm run build
npm run package    # Creates .vsix file
```

### Publish to VS Code Marketplace

```bash
cd extension
# Login first: npx vsce login <publisher>
npm run publish:vscode
```

### Publish to OpenVSX (for Cursor, VSCodium, etc.)

```bash
cd extension
# Set token: export OVSX_PAT=<your-token>
npm run publish:openvsx
```

## Extending

### Adding a custom analyzer

1. Create a new file in `backend/analyzers/`:

```python
from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo

class MyAnalyzer(BaseAnalyzer):
    name = "my-analyzer"

    async def analyze(self, root_path: str, project_info: ProjectInfo) -> list[Issue]:
        issues = []
        # Your analysis logic here
        return issues
```

2. Register it in `backend/analyzers/registry.py`:

```python
from analyzers.my_analyzer import MyAnalyzer
AnalyzerRegistry.register(MyAnalyzer())
```

## Design Principles

- **Offline-first** — no network required for core analysis
- **Fast** — incremental scanning, caching, debounced file watching
- **Minimal UI** — sidebar, status bar, problems panel — no popup spam
- **Extensible** — plugin analyzer registry, modular architecture
- **Cross-IDE** — works in any VS Code ecosystem editor

## License

MIT

## Made with Claude Code
Made By Manish Srivastav
