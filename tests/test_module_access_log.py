import asyncio
from types import SimpleNamespace

from starlette.requests import Request

from python_app.routers.system_management import create_module_access_log


class RecordingDb:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True


def make_request() -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/system/module-access-log",
        "headers": [(b"x-forwarded-for", b"192.0.2.10")],
        "client": ("127.0.0.1", 12345),
    })


def test_mobile_module_access_log_keeps_mobile_source_and_path():
    db = RecordingDb()
    result = asyncio.run(create_module_access_log(
        payload={
            "module_id": "mobile-sales-dashboard",
            "module_name": "手机端销售看板",
            "client_type": "mobile",
            "path": "/mobile/sales",
        },
        request=make_request(),
        db=db,
        current_user=SimpleNamespace(user_id=7),
    ))

    assert result == {"message": "模块访问日志已记录"}
    assert db.committed is True
    assert len(db.added) == 1
    log = db.added[0]
    assert log.user_id == 7
    assert log.action_code == "enter"
    assert log.resource_code == "mobile-sales-dashboard"
    assert log.target_id == "mobile-sales-dashboard"
    assert log.detail == {
        "module_id": "mobile-sales-dashboard",
        "module_name": "手机端销售看板",
        "client_type": "mobile",
        "path": "/mobile/sales",
    }
    assert log.ip_address == "192.0.2.10"


def test_module_access_log_ignores_untrusted_external_path():
    db = RecordingDb()
    asyncio.run(create_module_access_log(
        payload={
            "module_id": "mobile-home",
            "module_name": "手机端工作台",
            "client_type": "unknown",
            "path": "https://example.com/collect",
        },
        request=make_request(),
        db=db,
        current_user=SimpleNamespace(user_id=7),
    ))

    assert db.added[0].detail == {
        "module_id": "mobile-home",
        "module_name": "手机端工作台",
    }


def test_module_query_log_keeps_bounded_readable_query_conditions():
    db = RecordingDb()
    asyncio.run(create_module_access_log(
        payload={
            "module_id": "mobile-sales-dashboard",
            "module_name": "手机端销售看板",
            "client_type": "mobile",
            "path": "/mobile/sales",
            "action_code": "query",
            "query_conditions": {
                "start_date": "2026-08-01",
                "end_date": "2026-08-01",
                "store_name": "半山店",
                "empty": "   ",
                "nested": {"not": "accepted"},
            },
        },
        request=make_request(),
        db=db,
        current_user=SimpleNamespace(user_id=7),
    ))

    log = db.added[0]
    assert log.action_code == "query"
    assert log.target_id == "mobile-sales-dashboard"
    assert log.detail["query_conditions"] == {
        "start_date": "2026-08-01",
        "end_date": "2026-08-01",
        "store_name": "半山店",
    }
