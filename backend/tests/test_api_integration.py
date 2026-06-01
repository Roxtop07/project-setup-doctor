from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
class TestAPI:
    async def test_health_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "environment" in data["analyzers"]
            assert "dependencies" in data["analyzers"]
            assert "readme" in data["analyzers"]
            assert "security" in data["analyzers"]
            assert "docker" in data["analyzers"]

    async def test_scan_node_project(self, node_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={"root_path": node_project})
            assert resp.status_code == 200
            data = resp.json()
            assert "project_info" in data
            assert "issues" in data
            assert "health_score" in data
            assert data["health_score"]["total"] > 0
            assert data["scan_duration_ms"] > 0
            assert "express" in data["project_info"]["types"]

    async def test_scan_empty_project(self, empty_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={"root_path": empty_project})
            assert resp.status_code == 200
            data = resp.json()
            assert data["project_info"]["types"] == ["unknown"]

    async def test_scan_fullstack_project(self, fullstack_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={"root_path": fullstack_project})
            assert resp.status_code == 200
            data = resp.json()
            types = data["project_info"]["types"]
            assert "express" in types or "react" in types
            assert "flask" in types
            assert "docker" in types
            assert len(data["issues"]) > 0

    async def test_health_score_endpoint(self, node_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/health-score", json={"root_path": node_project})
            assert resp.status_code == 200
            data = resp.json()
            assert "health_score" in data
            bd = data["health_score"]["breakdown"]
            assert "dependency_hygiene" in bd
            assert "docs_quality" in bd
            assert "setup_readiness" in bd
            assert "security" in bd
            assert "environment_completeness" in bd

    async def test_project_info_endpoint(self, python_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/project-info", json={"root_path": python_project})
            assert resp.status_code == 200
            data = resp.json()
            assert "fastapi" in data["types"]
            assert data["has_requirements_txt"] is True

    async def test_scan_specific_analyzers(self, node_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={
                "root_path": node_project,
                "analyzers": ["environment"],
            })
            assert resp.status_code == 200
            data = resp.json()
            analyzers_used = {i["analyzer"] for i in data["issues"]}
            if analyzers_used:
                assert analyzers_used == {"environment"}

    async def test_autofix_endpoint(self, empty_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/autofix", json={
                "root_path": empty_project,
                "fix_ids": ["nonexistent-fix"],
            })
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["failed"]) == 1
            assert data["failed"][0]["id"] == "nonexistent-fix"

    async def test_scan_invalid_path(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={"root_path": "/nonexistent/path"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["issues"][0]["id"] == "scan-init-error"

    async def test_autofix_rejects_too_many_ids(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/autofix", json={
                "root_path": "/tmp",
                "fix_ids": [f"fix-{i}" for i in range(100)],
            })
            assert resp.status_code == 422

    async def test_scan_without_ai_config_omits_ai_fields(self, node_project: str):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/scan", json={"root_path": node_project})
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("ai_summary") is None
            assert data.get("ai_score") is None
            assert data.get("ai_error") is None
            assert not any(i["analyzer"] == "ai" for i in data["issues"])

    async def test_scan_with_ai_config_roundtrips_summary(self, node_project: str):
        """Stub the AI provider via the override ContextVar and confirm the
        ai_summary / ai_score round-trip through the API response."""
        from ai.runtime import override_ai_provider

        class _Stub:
            async def complete(self, system, user, schema, client=None):
                return {
                    "findings": [
                        {"severity": "info", "message": "Add a CONTRIBUTING.md"},
                    ],
                    "ai_score": 77,
                    "ai_summary": "Looks solid — minor docs gaps.",
                }

        token = override_ai_provider.set(_Stub())
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/scan",
                    json={
                        "root_path": node_project,
                        "ai_config": {
                            "provider": "openai",
                            "api_key": "sk-test",
                            "model": "gpt-4o-mini",
                            "enabled": True,
                        },
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["ai_summary"] == "Looks solid — minor docs gaps."
                assert data["ai_score"] == 77
                assert data["ai_provider"] == "openai"
                assert data["ai_model"] == "gpt-4o-mini"
                ai_issues = [i for i in data["issues"] if i["analyzer"] == "ai"]
                assert len(ai_issues) == 1
                assert ai_issues[0]["id"] == "ai-1"
        finally:
            override_ai_provider.reset(token)
