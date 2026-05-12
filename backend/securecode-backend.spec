# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "analyzers.env_analyzer",
    "analyzers.dependency_analyzer",
    "analyzers.readme_analyzer",
    "analyzers.security_analyzer",
    "analyzers.docker_analyzer",
    "api",
    "api.routes",
    "detectors",
    "detectors.project_detector",
    "models",
    "models.contracts",
    "scoring",
    "scoring.scoring_engine",
    "utils",
    "utils.fs",
    "analyzers",
    "analyzers.base",
    "analyzers.registry",
]

hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("pydantic_core")

a = Analysis(
    ["__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "test",
        "xmlrpc",
        "pydoc",
        "doctest",
        "lib2to3",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="securecode-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=True,
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    name="securecode-backend",
)
