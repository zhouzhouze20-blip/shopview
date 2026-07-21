import asyncio
import inspect
import json
import time
from datetime import date
from unittest.mock import patch

from fastapi import FastAPI

from python_app.routers import sales


def test_mobile_sales_database_handlers_run_outside_the_event_loop():
    handlers = [
        sales.latest_sales_date,
        sales.store_summary,
        sales.department_summary,
        sales.group_summary,
        sales.department_goods_summary,
        sales.department_supplier_summary,
        sales.map_group_summary,
        sales.group_tickets,
        sales.ticket_detail,
    ]

    async_handlers = [handler.__name__ for handler in handlers if inspect.iscoroutinefunction(handler)]

    assert async_handlers == [], (
        "Synchronous PostgreSQL work must not run on Uvicorn's event loop; "
        f"async handlers found: {', '.join(async_handlers)}"
    )


def test_slow_sales_query_does_not_block_async_health_probe():
    app = FastAPI()
    app.include_router(sales.router)

    def override_db():
        yield object()

    def override_user():
        return object()

    app.dependency_overrides[sales.get_db] = override_db
    app.dependency_overrides[sales.get_current_user] = override_user

    @app.get("/probe")
    async def probe():
        return {"status": "ok"}

    def slow_latest_date(_db):
        time.sleep(0.4)
        return date(2026, 7, 18)

    async def asgi_get(path: str):
        messages = []
        request_delivered = False

        async def receive():
            nonlocal request_delivered
            if not request_delivered:
                request_delivered = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [],
                "client": ("127.0.0.1", 12345),
                "server": ("test", 80),
            },
            receive,
            send,
        )
        status_code = next(message["status"] for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
        return status_code, json.loads(body)

    async def exercise_concurrency():
        with (
            patch.object(sales, "require_permission", lambda *_args, **_kwargs: None),
            patch.object(sales, "_latest_sales_accounting_date", slow_latest_date),
        ):
            sales_request = asyncio.create_task(asgi_get("/api/sales/summary/latest-date"))
            await asyncio.sleep(0.05)

            started_at = time.perf_counter()
            probe_status, probe_body = await asgi_get("/probe")
            probe_elapsed = time.perf_counter() - started_at
            sales_status, sales_body = await sales_request

        assert probe_status == 200
        assert probe_body == {"status": "ok"}
        assert probe_elapsed < 0.2
        assert sales_status == 200
        assert sales_body["latest_date"] == "2026-07-18"

    asyncio.run(exercise_concurrency())
