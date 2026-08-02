from pathlib import Path
import inspect

from python_app.routers.authz import CORE_PERMISSION_DEFINITIONS
from python_app.routers import sales


REPORT_PERMISSIONS = {
    "sales.commodity_detail.view",
    "sales.settled_gross_profit.view",
    "sales.od0002.view",
    "sales.od0001.view",
    "sales.od0003.view",
    "sales.od0004.view",
    "sales.od0005.view",
    "sales.hy0001.view",
    "sales.hdyy01.view",
}


def test_all_sales_report_permissions_are_registered_independently():
    registered = {permission[0] for permission in CORE_PERMISSION_DEFINITIONS}
    assert REPORT_PERMISSIONS <= registered


def test_sales_report_permission_migration_preserves_existing_role_access():
    migration = Path(
        "python_app/alembic/versions/l0a1b2c3d4e5_add_sales_report_permissions.py"
    ).read_text(encoding="utf-8")

    assert "'sales.commodity_detail.view'" in migration
    assert "'sales.settled_gross_profit.view'" in migration
    assert "'sales.od0001.view'" in migration
    assert "('sales.view', 'sales.commodity_detail.view')" in migration
    assert (
        "('sales.od0002.view', 'sales.settled_gross_profit.view')" in migration
    )
    assert "('sales.od0002.view', 'sales.od0001.view')" in migration


def test_commodity_detail_endpoints_use_their_own_permission():
    departments_source = inspect.getsource(sales.commodity_sales_detail_departments)
    report_source = inspect.getsource(sales.commodity_sales_detail_report)

    assert sales.COMMODITY_DETAIL_PERMISSION == "sales.commodity_detail.view"
    assert "COMMODITY_DETAIL_PERMISSION" in departments_source
    assert "COMMODITY_DETAIL_PERMISSION" in report_source
