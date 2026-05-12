from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from models.contracts import BackendStatus

VERSION = "0.1.0"

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SecureCode",
    version=VERSION,
    docs_url="/docs" if os.environ.get("ENABLE_DOCS") else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        "vscode-webview://*",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)


@app.get("/health")
async def health() -> BackendStatus:
    from analyzers.registry import AnalyzerRegistry

    return BackendStatus(
        status="ok",
        version=VERSION,
        analyzers=AnalyzerRegistry.list_names(),
    )
