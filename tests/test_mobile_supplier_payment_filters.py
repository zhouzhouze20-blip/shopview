import asyncio
import importlib
import json
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit

import pytest
from fastapi import FastAPI, HTTPException

from python_app.routers import erp_settlements as router
from python_app.services import joint_payment_confirmation as svc


@pytest.fixture
def mobile_client(monkeypatch):
    app = FastAPI()
    app.include_router(router.router)
    app.dependency_overrides[router.get_db] = lambda: object()
    app.dependency_overrides[router.get_current_user] = lambda: SimpleNamespace(user_id=1)
    monkeypatch.setattr(router, "require_permission", lambda *_: None)
    monkeypatch.setattr(router, "_mobile_supplier_payment_scope", lambda *_: svc.BusinessScope(
        department_allow=frozenset({"60201"}), group_deny=frozenset({"6020102"}),
    ))
    def get(url, params=None):
        parsed = urlsplit(url)
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(app({
            "type": "http", "http_version": "1.1", "method": "GET", "scheme": "http",
            "path": parsed.path, "raw_path": parsed.path.encode(), "root_path": "",
            "query_string": (urlencode(params) if params else parsed.query).encode(),
            "headers": [], "server": ("testserver", 80), "client": ("testclient", 1234),
        }, receive, send))
        status_code = next(message["status"] for message in messages if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages)
        return SimpleNamespace(status_code=status_code, json=lambda: json.loads(body))

    return SimpleNamespace(get=get)


def test_mobile_filters_and_detail_use_department_without_replacing_permissions(mobile_client, monkeypatch):
    captured = {}

    def query(_db, filters, scope):
        captured.update(filters=filters, scope=scope)
        return {"items": [], "total": 0}

    monkeypatch.setattr(router.payment_confirmation_svc, "query_joint_payments", query)
    response = mobile_client.get("/api/erp-settlements/mobile/supplier-payments", params={
        "market": "602", "department_code": "60201", "supplier_code": "00050", "page": 2,
        "financial_month": "2026-08",
    })
    assert response.status_code == 200
    filters = captured["filters"]
    assert (filters.market, filters.market_exact, filters.department_code, filters.page) == ("602", True, "60201", 2)
    assert filters.supplier_code == "00050"
    assert filters.include_banshan is True
    assert filters.financial_month == "2026-08"
    assert captured["scope"].group_deny == frozenset({"6020102"})

    def detail(_db, bill, scope, department_code=None, include_banshan=False):
        assert include_banshan is True
        assert bill == "PAY-001"
        assert department_code == "60201"
        assert scope.department_allow == frozenset({"60201"})
        return {"head": {}, "lines": [], "charges": []}

    monkeypatch.setattr(router.payment_confirmation_svc, "get_joint_payment_detail", detail)
    assert mobile_client.get("/api/erp-settlements/mobile/supplier-payments/PAY-001?department_code=60201").status_code == 200


def test_options_route_precedes_detail_and_requires_mobile_permission(mobile_client, monkeypatch):
    def options(_db, scope):
        assert scope.group_deny == frozenset({"6020102"})
        return {"stores": [{"store_code": "602", "store_name": "新世纪"}], "departments": []}

    monkeypatch.setattr(router.payment_confirmation_svc, "query_mobile_supplier_payment_options", options)
    response = mobile_client.get("/api/erp-settlements/mobile/supplier-payments/options")
    assert response.status_code == 200
    assert response.json()["stores"][0]["store_code"] == "602"

    def deny(_db, _user, permission):
        assert permission == "mobile.supplier_payments.view"
        raise HTTPException(status_code=403, detail="没有权限")

    monkeypatch.setattr(router, "require_permission", deny)
    assert mobile_client.get("/api/erp-settlements/mobile/supplier-payments/options").status_code == 403


def test_all_amount_queries_keep_exact_store_department_and_deny_scope(monkeypatch):
    statements = []
    results = [
        SimpleNamespace(fetchone=lambda: None),
        SimpleNamespace(fetchone=lambda: None),
        SimpleNamespace(fetchone=lambda: SimpleNamespace(n=0)),
        SimpleNamespace(fetchall=lambda: []),
    ]

    class Db:
        def execute(self, statement, params):
            statements.append((str(statement), dict(params)))
            return results[len(statements) - 1]

    monkeypatch.setattr(svc, "_table_exists", lambda *_: True)
    svc.query_joint_payments(Db(), svc.JointPaymentFilters(
        market="602", market_exact=True, department_code="60201", date_from="2026-07-01",
    ), svc.BusinessScope(department_allow=frozenset({"60201"}), group_deny=frozenset({"6020102"})))
    assert len(statements) == 4
    for sql, params in statements:
        assert "= :joint_payment_market" in sql
        assert params["joint_payment_market"] == "602"
        assert "= :joint_payment_department_code" in sql
        assert params["joint_payment_department_code"] == "60201"
        assert "NOT (" in sql and "joint_payment_deny_group_0" in sql
        assert params["joint_payment_deny_group_0"] == "6020102"
    current_start, current_end = svc.current_financial_month_period()
    assert "joint_payment_date_from" not in statements[1][0]
    assert statements[1][1]["joint_payment_head_audit_start"] == current_start
    assert statements[1][1]["joint_payment_head_audit_end"] == current_end


def test_options_preserve_store_department_pairs_and_scope(monkeypatch):
    captured = {}
    rows = [
        {"store_code": "602", "store_name": "新世纪", "department_code": "60201", "department_name": "新世纪一部"},
        {"store_code": "602", "store_name": "新世纪", "department_code": "60202", "department_name": "新世纪二部"},
        {"store_code": "601", "store_name": "中心", "department_code": None, "department_name": None},
    ]

    class Db:
        def execute(self, statement, params):
            captured.update(sql=str(statement), params=params)
            return SimpleNamespace(fetchall=lambda: [SimpleNamespace(_mapping=row) for row in rows])

    monkeypatch.setattr(svc, "_table_exists", lambda *_: True)
    result = svc.query_mobile_supplier_payment_options(Db(), svc.BusinessScope(
        group_allow=frozenset({"6020101"}), department_deny=frozenset({"60209"}),
    ))
    assert len(result["stores"]) == 2
    assert len(result["departments"]) == 2
    assert all(item["store_code"] == "602" for item in result["departments"])
    assert "joint_payment_allow_group_0" in captured["sql"]
    assert "joint_payment_deny_department_code_0" in captured["sql"]
    assert "TRIM(COALESCE(pb.pbwmid::text, '')) = '4'" in captured["sql"]


def test_department_detail_filters_head_lines_and_charges(monkeypatch):
    statements = []
    captured = {}
    line = {"group_code": "6020101", "fee_amount_1": 10, "fee_amount_2": 20, "payment_amount": 70}

    class Db:
        def execute(self, statement, params):
            statements.append((str(statement), dict(params)))
            if len(statements) == 1:
                return SimpleNamespace(fetchone=lambda: SimpleNamespace(_mapping={"payment_amount": 70}))
            return SimpleNamespace(fetchall=lambda: [SimpleNamespace(_mapping=line)])

    def charges(_db, **kwargs):
        captured.update(kwargs)
        return []

    erp_settlement_charge_display = importlib.import_module("services.erp_settlement_charge_display")
    monkeypatch.setattr(erp_settlement_charge_display, "query_supsetcharge_enriched", charges)
    monkeypatch.setattr(svc, "_table_exists", lambda *_: True)
    result = svc.get_joint_payment_detail(Db(), "PAY-001", svc.BusinessScope(
        department_allow=frozenset({"60201"}), group_deny=frozenset({"6020102"}),
    ), department_code="60201")
    assert result["head"]["payment_amount"] == 70
    for sql, params in statements:
        assert "= :joint_payment_department_code" in sql
        assert params["joint_payment_department_code"] == "60201"
    assert captured["params"]["joint_payment_selected_department_group_0"] == "6020101"
    assert captured["params"]["joint_payment_charge_deny_group_0"] == "6020102"
    assert "joint_payment_selected_department_group_0" in captured["where_sql"]


@pytest.mark.parametrize("month,start,end", [
    ("2026-08", date(2026, 8, 1), date(2026, 8, 31)),
    ("2026-09", date(2026, 9, 1), date(2026, 9, 30)),
    ("2024-02", date(2024, 2, 1), date(2024, 2, 29)),
    ("2026-02", date(2026, 2, 1), date(2026, 2, 28)),
    ("2026-12", date(2026, 12, 1), date(2026, 12, 31)),
    ("2027-01", date(2027, 1, 1), date(2027, 1, 31)),
])
def test_payment_generation_month_includes_month_end_without_overlap(month, start, end):
    assert svc.payment_generation_month_period(month) == (start, end)


@pytest.mark.parametrize("month", ["2026-00", "2026-13", "2026-8", "0000-01", "2026-08-29", "", "invalid"])
def test_invalid_financial_month_is_rejected_by_api(mobile_client, month):
    response = mobile_client.get("/api/erp-settlements/mobile/supplier-payments", params={"financial_month": month})
    assert response.status_code == 422


def test_financial_month_cannot_mix_with_old_status_date_filters(mobile_client):
    response = mobile_client.get("/api/erp-settlements/mobile/supplier-payments", params={
        "financial_month": "2026-08", "date_from": "2026-08-29",
    })
    assert response.status_code == 422


@pytest.mark.parametrize("status_code", ["M", "Y"])
def test_generation_month_predicate_keeps_august_29_to_31_even_after_september_audit(status_code):
    _, where, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(financial_month="2026-08", status=status_code), svc.BusinessScope(all_access=True),
    )
    assert "h.inputdate >= CAST(:joint_payment_generation_start AS date)" in where
    assert "h.inputdate < CAST(:joint_payment_generation_end AS date) + INTERVAL '1 day'" in where
    assert "h.auditdate" not in where
    start = datetime.fromisoformat(params["joint_payment_generation_start"])
    until = datetime.fromisoformat(params["joint_payment_generation_end"]) + timedelta(days=1)
    generated_dates = [datetime(2026, 7, 31, 23, 59), datetime(2026, 8, 1), datetime(2026, 8, 28),
                       datetime(2026, 8, 29), datetime(2026, 8, 30), datetime(2026, 8, 31, 23, 59, 59), datetime(2026, 9, 1)]
    assert [start <= generated < until for generated in generated_dates] == [False, True, True, True, True, True, False]


def test_selected_month_summary_and_list_share_generation_period(monkeypatch):
    statements = []
    results = [
        SimpleNamespace(fetchone=lambda: SimpleNamespace(
            generated_count=3,
            generated_supplier_count=2,
            generated_amount=100,
            audited_count=4,
            audited_supplier_count=3,
            audited_amount=250,
        )),
        SimpleNamespace(fetchone=lambda: SimpleNamespace(audited_amount=999)),
        SimpleNamespace(fetchone=lambda: SimpleNamespace(n=2)),
        SimpleNamespace(fetchall=lambda: []),
    ]

    class Db:
        def execute(self, statement, params):
            statements.append((str(statement), dict(params)))
            return results[len(statements) - 1]

    monkeypatch.setattr(svc, "_table_exists", lambda *_: True)
    result = svc.query_joint_payments(Db(), svc.JointPaymentFilters(
        financial_month="2026-08", market="602", market_exact=True, department_code="60201",
    ), svc.BusinessScope(group_allow=frozenset({"6020101"}), group_deny=frozenset({"6020102"})))
    for index in (0, 2, 3):
        sql, params = statements[index]
        assert "h.inputdate >= CAST(:joint_payment_generation_start AS date)" in sql
        assert params["joint_payment_generation_start"] == "2026-08-01"
        assert params["joint_payment_generation_end"] == "2026-08-31"
        assert params["joint_payment_market"] == "602"
        assert params["joint_payment_department_code"] == "60201"
        assert params["joint_payment_deny_group_0"] == "6020102"
    assert "joint_payment_generation_start" not in statements[1][0]
    assert "COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), ''))" in statements[0][0]
    assert result["summary"]["generated_count"] == 3
    assert result["summary"]["generated_supplier_count"] == 2
    assert result["summary"]["audited_count"] == 4
    assert result["summary"]["audited_supplier_count"] == 3
    assert result["summary"]["audited_amount"] == 250
    assert result["summary"]["current_financial_month_audited_amount"] == 999


def test_payment_head_filters_run_before_batch_department_aggregation():
    cte_sql, _, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(
            financial_month="2026-08",
            market="601",
            market_exact=True,
            department_code="60101",
        ),
        svc.BusinessScope(all_access=True),
    )

    assert "FROM suppayhead h_prefilter" in cte_sql
    assert "INNER JOIN paybatch pb ON pb.pbpaybillno = h_prefilter.sphbillno" in cte_sql
    assert "h_prefilter.inputdate >= CAST(:joint_payment_generation_start AS date)" in cte_sql
    assert "TRIM(COALESCE(h_prefilter.sphmkt::text, '')) = :joint_payment_market" in cte_sql
    assert "LEFT JOIN manaframe group_mf ON group_mf.mfcode = pb.pbmfid" in cte_sql
    assert "LEFT JOIN manaframe dept ON dept.mfcode = group_mf.mfpcode" in cte_sql
    assert params["joint_payment_department_code"] == "60101"


@pytest.mark.parametrize("payment_status", ["C", "N", "U", "P"])
def test_mobile_confirmation_filter_and_response(mobile_client, monkeypatch, payment_status):
    def query(_db, filters, scope):
        assert filters.status == payment_status
        assert filters.include_supplier_confirmation is True
        assert filters.financial_month == "2026-08"
        assert scope.group_deny == frozenset({"6020102"})
        return {"summary": {
            "total_generated_count": 5, "total_generated_supplier_count": 3,
            "total_generated_amount": 500,
            "supplier_confirmation_available": True,
            "supplier_confirmed_count": 3, "supplier_confirmed_supplier_count": 2,
            "supplier_confirmed_amount": 250,
        }, "items": [{"payment_bill_no": "P1", "supplier_confirmed": True}], "total": 3}

    monkeypatch.setattr(router.payment_confirmation_svc, "query_joint_payments", query)
    response = mobile_client.get("/api/erp-settlements/mobile/supplier-payments", params={
        "payment_status": payment_status, "financial_month": "2026-08",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["supplier_confirmed_supplier_count"] == 2
    assert data["summary"]["total_generated_supplier_count"] == 3
    assert data["items"][0]["supplier_confirmed"] is True


@pytest.mark.parametrize("payment_status", ["C", "N", "U", "P"])
def test_mobile_confirmation_unavailable_is_not_zero_confirmations(mobile_client, monkeypatch, payment_status):
    def unavailable(*_):
        raise ValueError("供应商确认数据尚未就绪，请稍后重试")

    monkeypatch.setattr(router.payment_confirmation_svc, "query_joint_payments", unavailable)
    response = mobile_client.get(f"/api/erp-settlements/mobile/supplier-payments?payment_status={payment_status}")
    assert response.status_code == 503
    assert "确认数据尚未就绪" in response.json()["detail"]


@pytest.mark.parametrize("confirmation_available", [True, False])
@pytest.mark.parametrize("payment_status", ["C", "N", "U", "P"])
def test_confirmation_summary_and_list_keep_month_and_visible_amount_scope(monkeypatch, confirmation_available, payment_status):
    statements = []
    summary_row = SimpleNamespace(
        total_generated_count=4, total_generated_supplier_count=2, total_generated_amount=400,
        supplier_confirmed_count=3, supplier_confirmed_supplier_count=2, supplier_confirmed_amount=300,
        supplier_unreported_count=1, supplier_unreported_supplier_count=1, supplier_unreported_amount=100,
        generated_count=3, generated_supplier_count=2, generated_amount=300,
        audited_count=1, audited_supplier_count=1, audited_amount=100,
    )
    results = [SimpleNamespace(fetchone=lambda: summary_row),
               SimpleNamespace(fetchone=lambda: None),
               SimpleNamespace(fetchone=lambda: SimpleNamespace(n=3)),
               SimpleNamespace(fetchall=lambda: [])]

    class Db:
        def execute(self, statement, params):
            statements.append((str(statement), dict(params)))
            return results[len(statements) - 1]

    monkeypatch.setattr(svc, "_table_exists", lambda *_: True)
    monkeypatch.setattr(svc, "_supplier_confirmation_available", lambda *_: confirmation_available)
    result = svc.query_joint_payments(Db(), svc.JointPaymentFilters(
        financial_month="2026-08", status=payment_status if confirmation_available else "Y",
        market="602", market_exact=True, department_code="60201", include_supplier_confirmation=True,
    ), svc.BusinessScope(group_allow=frozenset({"6020101"}), group_deny=frozenset({"6020102"})))
    summary = result["summary"]
    assert summary["total_generated_count"] == 4
    assert summary["total_generated_supplier_count"] == 2
    assert summary["supplier_confirmation_available"] is confirmation_available
    assert summary["supplier_confirmed_count"] == (3 if confirmation_available else None)
    assert summary["supplier_confirmed_amount"] == (300 if confirmation_available else None)
    assert summary["supplier_unreported_count"] == (1 if confirmation_available else None)
    assert summary["supplier_unreported_supplier_count"] == (1 if confirmation_available else None)
    assert summary["supplier_unreported_amount"] == (100 if confirmation_available else None)
    for index in (0, 2, 3):
        sql, params = statements[index]
        assert params["joint_payment_generation_start"] == "2026-08-01"
        assert params["joint_payment_generation_end"] == "2026-08-31"
        assert params["joint_payment_department_code"] == "60201"
        assert params["joint_payment_deny_group_0"] == "6020102"
        if confirmation_available:
            assert "EXISTS (" in sql
            assert "TRIM(supplier_confirmation.id::text) = TRIM(h.sphbillno::text)" in sql
            assert "TRIM(supplier_confirmation.status::text) = '0'" in sql
            assert "TRIM(supplier_confirmation.invoice_status::text) = '1'" in sql
            assert "JOIN ods.js_supplier_order_head_rela" not in sql
        else:
            assert "ods.js_supplier_order_head_rela" not in sql
    assert "SUM(vb.payment_amount) FILTER" in statements[0][0]
    assert "invoice_money" not in statements[0][0]
    assert "COUNT(DISTINCT NULLIF(TRIM(h.sphsupid::text), '')) AS total_generated_supplier_count" in statements[0][0]

    if confirmation_available and payment_status in {"U", "P"}:
        for index in (2, 3):
            sql, params = statements[index]
            assert params["joint_payment_status"] == "M"
            assert "TRIM(h.sphflag::text) = :joint_payment_status" in sql
            assert ("NOT (EXISTS" in sql) is (payment_status == "U")
        assert "joint_payment_status" not in statements[0][1]

    if confirmation_available and payment_status == "N":
        for index in (2, 3):
            sql, params = statements[index]
            assert "NOT (EXISTS" in sql
            assert "joint_payment_status" not in params


@pytest.mark.parametrize("include_banshan", [False, True])
def test_banshan_consignment_is_mobile_only_and_keeps_scope(include_banshan):
    cte, _, params = svc.build_joint_payment_query_parts(
        svc.JointPaymentFilters(financial_month="2026-08", include_banshan=include_banshan),
        svc.BusinessScope(department_allow=frozenset({"60401"}), group_deny=frozenset({"6040102"})),
    )
    assert "joint_payment_deny_group_0" in cte
    assert params["joint_payment_deny_group_0"] == "6040102"
    assert "joint_payment_allow_department_code_0" in cte
    assert "TRIM(COALESCE(pb.pbwmid::text, '')) = '4'" in cte
    if include_banshan:
        assert "TRIM(COALESCE(pb.pbwmid::text, '')) = '3'" in cte
        assert "TRIM(h_prefilter.sphmkt::text) = '604'" in cte
        assert "FROM suppayhead banshan_head" not in cte
    else:
        assert "banshan_head" not in cte


def test_banshan_charge_bridge_uses_same_store_and_business_mode():
    sql = svc._payment_business_where(True, "charge_pb")
    assert "charge_pb.pbwmid" in sql
    assert "banshan_head.sphbillno = charge_pb.pbpaybillno" in sql
    assert "'604'" in sql
