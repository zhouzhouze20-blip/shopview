from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.models import LoginLog, OperationLog, User
from python_app.routers.system_management import (
    _build_audit_statistics,
    _build_audit_usage_trend,
    _same_time_previous_year,
    _yoy_percent,
)


def test_audit_statistics_use_successful_logins_and_like_for_like_yoy_periods():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, LoginLog.__table__, OperationLog.__table__],
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for user_id in (1, 2, 3):
            db.add(User(
                user_id=user_id,
                username=f"user-{user_id}",
                password_hash="x",
                real_name=f"用户{user_id}",
                status="ACTIVE",
                is_active=True,
            ))

        login_rows = [
            (1, 1, "SUCCESS", datetime(2026, 8, 3, 8, 0)),
            (2, 1, "SUCCESS", datetime(2026, 8, 3, 9, 0)),
            (3, 2, "SUCCESS", datetime(2026, 8, 3, 10, 0)),
            (4, 3, "FAILED", datetime(2026, 8, 3, 11, 0)),
            (5, 3, "SUCCESS", datetime(2026, 8, 2, 10, 0)),
            (6, 1, "SUCCESS", datetime(2025, 8, 1, 10, 0)),
            (7, 2, "SUCCESS", datetime(2025, 8, 3, 14, 0)),
            (8, 3, "SUCCESS", datetime(2025, 8, 3, 16, 0)),
        ]
        for log_id, user_id, result, created_at in login_rows:
            db.add(LoginLog(
                id=log_id,
                user_id=user_id,
                identity_type="password",
                identifier=f"user-{user_id}",
                login_result=result,
                created_at=created_at,
            ))

        operation_rows = [
            (1, 1, datetime(2026, 8, 3, 8, 5)),
            (2, 1, datetime(2026, 8, 3, 8, 10)),
            (3, 2, datetime(2026, 8, 3, 9, 5)),
            (4, 3, datetime(2026, 8, 2, 10, 0)),
            (5, 3, datetime(2026, 8, 2, 10, 5)),
            (6, 1, datetime(2025, 8, 2, 10, 0)),
            (7, 2, datetime(2025, 8, 3, 16, 0)),
        ]
        for log_id, user_id, created_at in operation_rows:
            db.add(OperationLog(
                id=log_id,
                user_id=user_id,
                action_code="query",
                resource_code="mobile-sales-dashboard",
                created_at=created_at,
            ))
        db.commit()

        result = _build_audit_statistics(db, datetime(2026, 8, 3, 15, 0))

        assert result["today"] == {
            "login_users": 2,
            "login_count": 3,
            "operation_users": 2,
            "operation_count": 3,
        }
        assert result["month_to_date"] == {
            "login_users": 3,
            "login_count": 4,
            "operation_users": 3,
            "operation_count": 5,
        }
        assert result["last_year_same_period"] == {
            "login_users": 2,
            "login_count": 2,
            "operation_users": 1,
            "operation_count": 1,
        }
        assert result["yoy"] == {
            "login_users": 50.0,
            "login_count": 100.0,
            "operation_users": 200.0,
            "operation_count": 400.0,
        }
    finally:
        db.close()
        Base.metadata.drop_all(
            engine,
            tables=[OperationLog.__table__, LoginLog.__table__, User.__table__],
        )
        engine.dispose()


def test_yoy_and_previous_year_helpers_cover_zero_baseline_and_leap_day():
    assert _yoy_percent(10, 0) is None
    assert _yoy_percent(5, 10) == -50.0
    assert _same_time_previous_year(datetime(2024, 2, 29, 12, 30)) == datetime(2023, 2, 28, 12, 30)


def test_audit_usage_trend_groups_daily_and_monthly_operation_metrics_and_fills_gaps():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, LoginLog.__table__, OperationLog.__table__],
    )
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        for user_id in (1, 2):
            db.add(User(
                user_id=user_id,
                username=f"user-{user_id}",
                password_hash="x",
                real_name=f"用户{user_id}",
                status="ACTIVE",
                is_active=True,
            ))
        for log_id, user_id, created_at in (
            (1, 1, datetime(2026, 8, 2, 8, 0)),
            (2, 1, datetime(2026, 8, 2, 9, 0)),
            (3, 2, datetime(2026, 8, 2, 10, 0)),
            (4, 2, datetime(2026, 8, 3, 10, 0)),
            (5, 1, datetime(2026, 4, 10, 10, 0)),
            (6, 1, datetime(2025, 8, 2, 10, 0)),
        ):
            db.add(OperationLog(
                id=log_id,
                user_id=user_id,
                action_code="query",
                resource_code="mobile-sales-dashboard",
                created_at=created_at,
            ))
        for log_id, user_id, result, created_at in (
            (1, 1, "SUCCESS", datetime(2026, 8, 2, 7, 0)),
            (2, 1, "SUCCESS", datetime(2026, 8, 2, 8, 0)),
            (3, 2, "SUCCESS", datetime(2026, 8, 2, 9, 0)),
            (4, 2, "FAILED", datetime(2026, 8, 3, 9, 0)),
            (5, 2, "SUCCESS", datetime(2026, 8, 3, 10, 0)),
            (6, 1, "SUCCESS", datetime(2026, 4, 10, 10, 0)),
            (7, 1, "SUCCESS", datetime(2025, 8, 2, 10, 0)),
        ):
            db.add(LoginLog(
                id=log_id,
                user_id=user_id,
                identity_type="password",
                identifier=f"user-{user_id}",
                login_result=result,
                created_at=created_at,
            ))
        db.commit()

        monthly = _build_audit_usage_trend(db, "month", "2026-08", datetime(2026, 8, 21))
        assert len(monthly["series"]) == 21
        assert monthly["series"][0] == {
            "bucket": "2026-08-01",
            "usage_users": 0,
            "operation_count": 0,
        }
        assert monthly["series"][1] == {
            "bucket": "2026-08-02",
            "usage_users": 2,
            "operation_count": 3,
        }
        assert monthly["series"][2] == {
            "bucket": "2026-08-03",
            "usage_users": 1,
            "operation_count": 1,
        }

        yearly = _build_audit_usage_trend(db, "year", "2026", datetime(2026, 8, 21))
        assert len(yearly["series"]) == 8
        assert yearly["series"][3] == {
            "bucket": "2026-04",
            "usage_users": 1,
            "operation_count": 1,
        }
        assert yearly["series"][7] == {
            "bucket": "2026-08",
            "usage_users": 2,
            "operation_count": 4,
        }
    finally:
        db.close()
        Base.metadata.drop_all(
            engine,
            tables=[OperationLog.__table__, LoginLog.__table__, User.__table__],
        )
        engine.dispose()


def test_usage_breakdown_full_period_identity_modules_and_boundaries():
    engine = create_engine("sqlite:///:memory:")
    tables = [User.__table__, LoginLog.__table__, OperationLog.__table__]
    Base.metadata.create_all(engine, tables=tables)
    now = datetime(2026, 8, 21, 12)
    with sessionmaker(bind=engine)() as db:
        db.add_all([User(user_id=i, username=f"user-{i}", real_name="同名用户",
                         password_hash="x", status="ACTIVE", is_active=True) for i in (1, 2, 3)])
        # More than the log page size, with a changed display name for the same module.
        for i in range(1, 206):
            db.add(OperationLog(id=i, user_id=1, action_code="query", resource_code="sales",
                                detail={"module_name": "销售" if i < 200 else "销售看板"},
                                created_at=datetime(2026, 8, 2, 8)))
        for i, uid, resource, action, at in [
            (206, 2, "sales", "enter", datetime(2026, 8, 3)),
            (207, None, "config", "update", datetime(2026, 8, 4)),
            (208, 1, "config", "update", datetime(2026, 8, 5)),
            (209, 1, "sales", "query", datetime(2026, 7, 31, 23, 59)),
            (210, 1, "sales", "query", now),
            (211, 1, "sales", "query", datetime(2026, 9, 1)),
        ]:
            db.add(OperationLog(id=i, user_id=uid, resource_code=resource, action_code=action, created_at=at))
        for i, uid, identifier, result in [
            (1, 1, "user-1", "SUCCESS"), (2, 1, "another-login", "SUCCESS"),
            (3, None, "1", "SUCCESS"), (4, 2, "user-2", "FAILED"),
            (5, 3, "user-3", "SUCCESS"),
        ]:
            db.add(LoginLog(id=i, user_id=uid, identifier=identifier, login_result=result,
                            created_at=datetime(2026, 8, 6)))
        db.commit()
        people = _build_audit_usage_trend(db, "month", "2026-08", now, "person")["items"]
        by_key = {row["key"]: row for row in people}
        assert len(people) == 5
        assert people[0]["key"] == "user:1"
        assert by_key["user:1"]["operation_count"] == 206
        assert by_key["user:1"]["login_count"] == 2
        assert by_key["user:1"]["module_count"] == 2
        assert by_key["user:1"]["last_used_at"] == datetime(2026, 8, 6)
        assert by_key["user:2"]["login_count"] == 0
        assert by_key["user:3"]["operation_count"] == 0
        assert by_key["login:1"]["login_count"] == 1
        assert by_key["unknown:operation"]["operation_count"] == 1
        modules = _build_audit_usage_trend(db, "month", "2026-08", now, "module")["items"]
        assert len(modules) == 2
        assert modules[0]["key"] == "sales"
        assert modules[0]["operation_count"] == 206
        assert modules[0]["usage_users"] == 2
        assert modules[0]["query_count"] == 205
        assert modules[0]["enter_count"] == 1
        assert modules[1]["name"] == "config"
        assert modules[1]["usage_users"] == 1
        trend = _build_audit_usage_trend(db, "month", "2026-08", now)
        assert sum(row["operation_count"] for row in people) == sum(row["operation_count"] for row in modules) == sum(row["operation_count"] for row in trend["series"]) == 208
        yearly = _build_audit_usage_trend(db, "year", "2026", now, "module")
        assert sum(row["operation_count"] for row in yearly["items"]) == 209
        assert _build_audit_usage_trend(db, "month", "2026-06", now, "person")["items"] == []
        import pytest
        for granularity, period, dimension in [("month", "2026-09", "person"), ("year", "2027", "module"), ("month", "bad", "person"), ("year", "2026", "bad")]:
            with pytest.raises(ValueError):
                _build_audit_usage_trend(db, granularity, period, now, dimension)
    engine.dispose()


def test_breakdown_endpoint_requires_audit_permission_before_query(monkeypatch):
    import asyncio
    import pytest
    from fastapi import HTTPException
    from python_app.routers import system_management as module

    def deny(db, user, permission):
        assert permission == "system.audit_log.view"
        raise HTTPException(status_code=403, detail="forbidden")

    def unexpected_query(*args, **kwargs):
        raise AssertionError("Unauthorized statistics query")

    monkeypatch.setattr(module, "_require_system_permission", deny)
    monkeypatch.setattr(module, "_build_audit_usage_trend", unexpected_query)
    for dimension in ("trend", "person", "module"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(module.get_audit_statistics_trend(
                granularity="month", period="2026-08", dimension=dimension, db=None, current_user=None))
        assert error.value.status_code == 403
