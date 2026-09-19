from decimal import Decimal
import inspect
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine

from python_app.routers import sales
from python_app.routers.authz import DataScope
from python_app.services import inventory_detail_report as service


class CapturingSession:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), dict(params)))
        return self

    def mappings(self):
        return self

    def one(self):
        return {"total_count": 1, "inventory_quantity": Decimal("2.5"),
                "retail_amount": Decimal("123.45")}

    def all(self):
        return []


def test_department_filter_is_exact_parameterized_and_preserves_positive_inventory():
    params = {}
    sql = service.build_inventory_filter_sql({"department_code": " D'1 "}, params)
    assert "area_node.mfcode = :department_code" in sql
    assert "gs.gstkcsl > 0" in sql
    assert "D'1" not in sql
    assert params == {"department_code": "D'1"}


def test_department_candidates_use_same_scoped_inventory_without_truncating_options():
    db = CapturingSession()
    service.load_inventory_departments(
        db, scope_sql=" AND gs.gstsupid = :allowed_supplier", scope_params={"allowed_supplier": "S1"},
    )
    sql, params = db.calls[0]
    assert "gs.gstkcsl > 0" in sql
    assert "gs.gstsupid = :allowed_supplier" in sql
    assert "area_code AS value" in sql
    assert "GROUP BY area_code" in sql
    assert "LIMIT" not in sql
    assert params == {"allowed_supplier": "S1"}


def test_summary_applies_scope_and_department_before_grouping_and_pagination():
    db = CapturingSession()
    report = service.load_inventory_department_summary(
        db, department_code=" D1 ", scope_sql=" AND gs.gstmfid = :allowed_group",
        scope_params={"allowed_group": "G1"}, limit=1, offset=2,
    )
    for sql, params in db.calls:
        assert "area_node.mfcode = :department_code" in sql
        assert "gs.gstmfid = :allowed_group" in sql
        assert "SUM(retail_amount) AS retail_amount" in sql
        assert "SUM(inventory_purchase_amount_tax_included)" not in sql
        assert sql.index("gs.gstmfid = :allowed_group") < sql.index("GROUP BY store_code, supplier_code, group_code")
        assert params["department_code"] == "D1"
        assert params["allowed_group"] == "G1"
    assert "LIMIT" not in db.calls[0][0]
    assert db.calls[1][1]["offset"] == 2
    assert report["summary"]["retail_amount"] == 123.45
    assert "零售价金额" in report["source_note"]
    assert report["department_code"] == "D1"


def test_blank_department_never_falls_back_to_all_inventory():
    db = CapturingSession()
    with pytest.raises(ValueError, match="部门编码不能为空"):
        service.load_inventory_department_summary(db, department_code=" ", scope_sql="", scope_params={}, limit=50, offset=0)
    assert db.calls == []


def test_executed_aggregation_preserves_supplier_group_grain_and_full_totals():
    # Exercise the actual aggregation/page SQL over deterministic rows, while
    # separate tests above verify the PostgreSQL inventory joins and scope.
    base_sql = """
        SELECT * FROM (
          SELECT '601' AS store_code, 'S1' AS supplier_code, 'G1' AS group_code,
                 '门店' AS store_display, '供应商一' AS supplier_display,
                 '柜组一' AS group_name, '[G1] 柜组一' AS group_display,
                 2.5 AS inventory_quantity, 100.25 AS retail_amount,
                 50 AS inventory_purchase_amount_tax_included
          UNION ALL SELECT '601', 'S1', 'G1', '门店', '供应商一', '柜组一', '[G1] 柜组一', 1.25, 20.25, 10
          UNION ALL SELECT '601', 'S2', 'G1', '门店', '供应商二', '柜组一', '[G1] 柜组一', 4, 200.50, 150
          UNION ALL SELECT '601', 'S1', 'G2', '门店', '供应商一', '柜组二', '[G2] 柜组二', 1, -10, -5
        ) fixture WHERE :department_code = 'D1'
    """
    engine = create_engine("sqlite://")
    with engine.connect() as db, patch.object(service, "inventory_base_sql", return_value=base_sql):
        pages = [service.load_inventory_department_summary(
            db, department_code="D1", scope_sql="", scope_params={}, limit=1, offset=offset,
        ) for offset in range(4)]
        assert [page["rows"][0]["group_code"] for page in pages[:3]] == ["G1", "G2", "G1"]
        assert pages[0]["rows"][0]["inventory_quantity"] == 3.75
        assert pages[0]["rows"][0]["retail_amount"] == 120.50
        assert pages[1]["rows"][0]["retail_amount"] == -10
        assert all(page["summary"] == {
            "total_count": 3, "inventory_quantity": 8.75, "retail_amount": 311,
        } for page in pages)
        assert pages[3]["rows"] == []
        empty = service.load_inventory_department_summary(db, department_code="OTHER", scope_sql="", scope_params={}, limit=50, offset=0)
        assert empty["summary"] == {"total_count": 0, "inventory_quantity": 0, "retail_amount": 0}
        assert empty["rows"] == []


@pytest.mark.parametrize("allow", [{"department": {"D1"}}, {"group": {"G1"}}, {"supplier": {"S1"}}, {"store": {"1"}}])
def test_new_routes_share_existing_inventory_row_scope(allow):
    db = CapturingSession()
    scope = DataScope(allow=allow, deny={"group": {"DENIED"}})
    with patch.object(sales, "require_permission") as permission, patch.object(sales, "_table_exists", return_value=True), patch.object(sales, "load_business_scope", return_value=scope):
        sales.inventory_departments(db=db, current_user=object())
        sales.inventory_department_summary(department_code="D1", limit=1, offset=0, db=db, current_user=object())
    assert permission.call_count == 2
    assert all(call.args[2] == "sales.inventory.view" for call in permission.call_args_list)
    for sql, params in db.calls:
        dimension = next(iter(allow))
        assert params[f"inventory_detail_allow_{dimension}"] == sorted(allow[dimension])
        assert params["inventory_detail_deny_group"] == ["DENIED"]
        assert "AND NOT" in sql


@pytest.mark.parametrize("scope", [DataScope(), DataScope(all_access=True, deny={"__all__": {"*"}})])
def test_no_scope_and_explicit_deny_fail_closed_for_both_routes(scope):
    db = CapturingSession()
    with patch.object(sales, "require_permission"), patch.object(sales, "_table_exists", return_value=True), patch.object(sales, "load_business_scope", return_value=scope):
        sales.inventory_departments(db=db, current_user=object())
        sales.inventory_department_summary(department_code="D1", limit=1, offset=0, db=db, current_user=object())
    assert all("AND 1=0" in sql for sql, _ in db.calls)


def test_routes_require_permission_and_reject_blank_department():
    db = CapturingSession()
    with patch.object(sales, "require_permission", side_effect=HTTPException(status_code=403, detail="无功能权限")):
        with pytest.raises(HTTPException) as error:
            sales.inventory_departments(db=db, current_user=object())
        assert error.value.status_code == 403
        with pytest.raises(HTTPException) as error:
            sales.inventory_department_summary(department_code="D1", limit=50, offset=0, db=db, current_user=object())
        assert error.value.status_code == 403
    with patch.object(sales, "_inventory_request_scope", return_value=(None, " AND 1=0", {})):
        with pytest.raises(HTTPException) as error:
            sales.inventory_department_summary(department_code=" ", limit=50, offset=0, db=db, current_user=object())
        assert error.value.status_code == 422
    assert db.calls == []


def test_route_declares_required_department_and_bounded_pagination():
    parameters = inspect.signature(sales.inventory_department_summary).parameters
    assert any(getattr(item, "min_length", None) == 1 for item in parameters["department_code"].default.metadata)
    assert any(getattr(item, "ge", None) == 1 for item in parameters["limit"].default.metadata)
    assert any(getattr(item, "le", None) == 200 for item in parameters["limit"].default.metadata)
    assert any(getattr(item, "ge", None) == 0 for item in parameters["offset"].default.metadata)
