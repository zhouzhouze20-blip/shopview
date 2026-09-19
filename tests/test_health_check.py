"""Exercise the real health handler without starting services or connecting to a database."""
import ast
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

from fastapi import FastAPI, Response
import pytest


@pytest.fixture
def probe(monkeypatch):
    # Importing main initializes upload storage. Load only its decorated handler instead.
    path = Path(__file__).resolve().parents[1] / "python_app/main.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    handler = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "health_check")
    app = FastAPI()
    namespace = {"app": app, "APP_VERSION": "test", "datetime": datetime, "Response": Response}
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(path), "exec"), namespace)

    session = Mock()
    factory = Mock(return_value=session)
    database = ModuleType("models.database")
    database.SessionLocal = factory
    monkeypatch.setitem(sys.modules, "models.database", database)

    async def request():
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        await app({
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "http", "path": "/api/health",
            "raw_path": b"/api/health", "query_string": b"", "root_path": "",
            "headers": [], "client": ("127.0.0.1", 12345), "server": ("test", 80),
        }, receive, send)
        status = next(item["status"] for item in messages if item["type"] == "http.response.start")
        body = b"".join(item.get("body", b"") for item in messages if item["type"] == "http.response.body")
        return status, json.loads(body)

    return lambda: asyncio.run(request()), session, factory


def test_healthy_database_returns_200_and_closes_session(probe):
    request, session, _ = probe
    status, body = request()
    assert status == 200
    assert body["status"] == "healthy"
    assert body["database"]["status"] == "connected"
    assert body["version"] == "test"
    assert str(session.execute.call_args.args[0]) == "SELECT 1"
    session.close.assert_called_once()


def test_database_query_failure_returns_503_and_recovers(probe):
    request, session, _ = probe
    session.execute.side_effect = RuntimeError("database unavailable")
    status, body = request()
    assert status == 503
    assert body["status"] == "degraded"
    assert body["database"]["status"] == "error"
    session.close.assert_called_once()
    session.execute.side_effect = None
    status, body = request()
    assert status == 200
    assert body["status"] == "healthy"
    assert session.close.call_count == 2


def test_session_creation_failure_returns_503(probe):
    request, _, factory = probe
    factory.side_effect = RuntimeError("connection pool unavailable")
    status, body = request()
    assert status == 503
    assert body["status"] == "unhealthy"


def test_session_cleanup_failure_returns_503(probe):
    request, session, _ = probe
    session.close.side_effect = RuntimeError("cleanup failed")
    status, body = request()
    assert status == 503
    assert body["status"] == "unhealthy"
