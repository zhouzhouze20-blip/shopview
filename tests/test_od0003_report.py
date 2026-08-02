import asyncio
from pathlib import Path


def test_od0003_permission_is_registered_and_migrated():
    from python_app.routers.authz import CORE_PERMISSION_DEFINITIONS

    registered = {permission[0] for permission in CORE_PERMISSION_DEFINITIONS}
    assert "sales.od0003.view" in registered

    migration = Path(
        "python_app/alembic/versions/m1b2c3d4e5f6_add_od0003_permission.py"
    ).read_text(encoding="utf-8")
    assert "down_revision" in migration
    assert '"l0a1b2c3d4e5"' in migration
    assert "'sales.od0003.view'" in migration
    assert "'sales.od0001.view'" in migration


def test_od0003_filter_options_use_independent_permission(monkeypatch):
    from python_app.routers import sales

    calls = []
    monkeypatch.setattr(
        sales,
        "_load_report_store_options",
        lambda db, user, **kwargs: calls.append(("stores", kwargs)) or [],
    )
    monkeypatch.setattr(
        sales,
        "_load_report_department_options",
        lambda db, user, store_id, **kwargs: (
            calls.append(("departments", store_id, kwargs)) or []
        ),
    )

    asyncio.run(sales.od0003_stores(object(), object()))
    asyncio.run(sales.od0003_departments("603", object(), object()))

    assert calls == [
        (
            "stores",
            {
                "permission_code": "sales.od0003.view",
                "prefix": "od0003_stores",
            },
        ),
        (
            "departments",
            "603",
            {
                "permission_code": "sales.od0003.view",
                "prefix": "od0003_departments",
            },
        ),
    ]


def test_od0003_report_uses_group_grain_and_selected_center(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    calls = {}
    monkeypatch.setattr(
        sales,
        "require_permission",
        lambda db, user, code: calls.setdefault("permission", code),
    )
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda db, user, **kwargs: DataScope(all_access=True),
    )
    monkeypatch.setattr(
        sales,
        "_business_scope_filter_sql",
        lambda scope, params, **kwargs: calls.setdefault("scope", kwargs) and "",
    )
    monkeypatch.setattr(
        sales,
        "load_daily_followup_report",
        lambda db, scope_sql, params, **kwargs: calls.setdefault("report", kwargs)
        and {"rows": []},
    )

    result = asyncio.run(
        sales.od0003_report(
            financial_year=2026,
            financial_month=7,
            store_id="603",
            department_id="6030101",
            db=object(),
            current_user=object(),
        )
    )

    assert calls["permission"] == "sales.od0003.view"
    assert calls["report"]["dimension"] == "groups"
    assert calls["report"]["selected_store"] == "603"
    assert calls["report"]["selected_department"] == "6030101"
    assert calls["report"]["include_ytd"] is True
    assert "scope_description" in result


def test_od0003_report_allows_all_stores_and_all_departments(monkeypatch):
    from python_app.routers import sales
    from python_app.routers.authz import DataScope

    report_calls = []
    monkeypatch.setattr(sales, "require_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        sales,
        "load_business_scope",
        lambda *args, **kwargs: DataScope(allow={"store": {"2"}}),
    )
    monkeypatch.setattr(
        sales,
        "_business_scope_filter_sql",
        lambda scope, params, **kwargs: " AND st.store_id::text = ANY(:allowed_stores)",
    )
    monkeypatch.setattr(
        sales,
        "load_daily_followup_report",
        lambda db, scope_sql, params, **kwargs: (
            report_calls.append(kwargs) or {"rows": []}
        ),
    )

    result = asyncio.run(
        sales.od0003_report(
            financial_year=2026,
            financial_month=7,
            store_id=None,
            department_id=None,
            db=object(),
            current_user=object(),
        )
    )

    assert report_calls[0]["selected_store"] is None
    assert report_calls[0]["selected_department"] is None
    assert result["rows"] == []


def test_daily_followup_query_exposes_od0003_brand_columns():
    from datetime import date

    from python_app.services.daily_followup_report import build_daily_followup_query
    from python_app.services.od0002_report import TrustedScopeSql

    sql, _ = build_daily_followup_query(
        date(2026, 6, 29),
        date(2026, 7, 28),
        date(2025, 6, 29),
        date(2025, 7, 28),
        "groups",
        TrustedScopeSql(""),
        {},
        "603",
        "6030101",
    )
    compact = " ".join(sql.split())
    assert "mf.mflc" in compact
    assert "manaframe_key_brand" in compact
    assert "category_manager_brand_assignments" in compact
    assert "manager_name" in compact
