from pathlib import Path
import inspect

from python_app.routers.authz import CORE_PERMISSION_DEFINITIONS
from python_app.routers import system_management


BASELINE_MOBILE_PERMISSIONS = {
    "mobile.sales.view",
    "mobile.contracts.view",
    "mobile.inventory.view",
}
MOBILE_PERMISSIONS = {
    *BASELINE_MOBILE_PERMISSIONS,
    "mobile.revenue_dashboard.view",
    "mobile.rental_receivables.view",
    "mobile.coupon_followup.view",
    "mobile.supplier_payments.view",
}


def test_all_mobile_module_permissions_are_registered():
    registered = {permission[0] for permission in CORE_PERMISSION_DEFINITIONS}
    assert MOBILE_PERMISSIONS <= registered


def test_mobile_permission_migration_preserves_existing_role_access():
    migration = Path(
        "python_app/alembic/versions/n2c3d4e5f6a7_add_mobile_module_permissions.py"
    ).read_text(encoding="utf-8")

    for permission_code in BASELINE_MOBILE_PERMISSIONS:
        assert f"'{permission_code}'" in migration

    assert "('sales.view', 'mobile.sales.view')" in migration
    assert "('contract.view', 'mobile.contracts.view')" in migration
    assert "('sales.inventory.view', 'mobile.inventory.view')" in migration


def test_baseline_mobile_permissions_are_opened_for_all_roles_and_revenue_inherits_safely():
    migration = Path(
        "python_app/alembic/versions/o3d4e5f6a7b8_add_mobile_revenue_dashboard.py"
    ).read_text(encoding="utf-8")

    assert "FROM roles role_row" in migration
    assert "'mobile.sales.view'" in migration
    assert "'mobile.contracts.view'" in migration
    assert "'mobile.inventory.view'" in migration
    assert "'mobile.revenue_dashboard.view'" in migration
    assert "desktop_revenue.permission_code = 'revenue.dashboard.view'" in migration


def test_new_roles_receive_the_three_baseline_mobile_permissions_by_default():
    create_role_source = inspect.getsource(system_management.create_role)

    assert system_management.DEFAULT_ROLE_PERMISSION_CODES == BASELINE_MOBILE_PERMISSIONS
    assert "_default_role_permission_ids(db)" in create_role_source
    assert "_sync_role_permissions(db, role.id, permission_ids)" in create_role_source


def test_mobile_rental_receivables_permission_inherits_only_from_settlement_access():
    migration = Path(
        "python_app/alembic/versions/e4f5a6b7c8d9_add_mobile_rental_receivables.py"
    ).read_text(encoding="utf-8")

    assert "'mobile.rental_receivables.view'" in migration
    assert "desktop_settlement.permission_code = 'settlement.view'" in migration


def test_mobile_coupon_followup_permission_uses_a_dedicated_assignment_role():
    migration = Path(
        "python_app/alembic/versions/g6b7c8d9e0f1_add_mobile_coupon_followup.py"
    ).read_text(encoding="utf-8")

    assert "'mobile.coupon_followup.view'" in migration
    assert "'category_coupon_followup_manager'" in migration
    assert "FROM category_manager_brand_assignments assignment" in migration


def test_mobile_supplier_payment_permission_uses_category_assignments_and_existing_payment_roles():
    migration = Path(
        "python_app/alembic/versions/k0f1a2b3c4d5_add_mobile_supplier_payments.py"
    ).read_text(encoding="utf-8")

    assert "'mobile.supplier_payments.view'" in migration
    assert "'category_supplier_payment_viewer'" in migration
    assert "FROM category_manager_brand_assignments assignment" in migration
    assert "assignment.is_active" in migration
    assert "desktop_payment.permission_code = 'settlement.joint_payment_confirmation.view'" in migration
