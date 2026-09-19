from datetime import date
from pathlib import Path

import pytest

from services.activity_analysis.birthday_coupon import (
    MAX_BIRTHDAY_COUPON_MONTHS,
    center_coupon_profile,
    month_end,
    month_window,
    normalize_coupon_type,
    normalize_month,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_normalize_month_accepts_valid_value():
    assert normalize_month("2026-08") == "2026-08"


@pytest.mark.parametrize("value", ["", "2026-8", "2026/08", "2026-13", "1999-12"])
def test_normalize_month_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        normalize_month(value)


def test_month_window_is_half_open_and_counts_months():
    start, end_exclusive, count = month_window("2026-06", "2026-08")
    assert start == date(2026, 6, 1)
    assert end_exclusive == date(2026, 9, 1)
    assert count == 3


def test_month_window_rejects_reverse_and_oversized_ranges():
    with pytest.raises(ValueError, match="开始月份"):
        month_window("2026-08", "2026-07")
    with pytest.raises(ValueError, match=str(MAX_BIRTHDAY_COUPON_MONTHS)):
        month_window("2024-01", "2026-01")


def test_month_end_handles_leap_year():
    assert month_end("2024-02") == date(2024, 2, 29)


def test_center_coupon_profiles_keep_l_and_c_issue_rules_separate():
    assert normalize_coupon_type(" l ") == "L"
    assert normalize_coupon_type("c") == "C"
    assert center_coupon_profile("L")["expected_issue_count_per_member"] == 1
    assert center_coupon_profile("C")["expected_issue_count_per_member"] == 2
    with pytest.raises(ValueError, match="L 或 C"):
        normalize_coupon_type("A")


def test_birthday_coupon_uses_an_independent_permission_chain():
    from routers import activity_analysis, authz

    permission_code = "activity_analysis.birthday_coupon.view"
    registered = {row[0] for row in authz.CORE_PERMISSION_DEFINITIONS}
    router_source = (REPO_ROOT / "python_app/routers/activity_analysis.py").read_text()
    migration_source = (REPO_ROOT / "python_app/alembic/versions/f5a6b7c8d9e0_add_birthday_coupon_permission.py").read_text()

    assert activity_analysis.BIRTHDAY_COUPON_ANALYSIS_PERMISSION == permission_code
    assert permission_code in registered
    assert "require_permission(db, current_user, BIRTHDAY_COUPON_ANALYSIS_PERMISSION)" in router_source
    assert permission_code in migration_source
    assert "source.permission_code = 'activity_analysis.view'" in migration_source


def test_dashboard_returns_group_rollups_for_department_drilldown():
    router_source = (REPO_ROOT / "python_app/routers/activity_analysis.py").read_text()

    assert 'coupon_type: str = Query("L"' in router_source
    assert "GROUPING SETS" in router_source
    assert '"groups": groups' in router_source


def test_birthday_coupon_drilldowns_keep_coupon_and_member_month_scope():
    router_source = (REPO_ROOT / "python_app/routers/activity_analysis.py").read_text()

    assert '@router.get("/birthday-coupon/usage-details")' in router_source
    assert "JOIN issued_coupons issued ON issued.tcflvipseq = l.tcflvipseq" in router_source
    assert "LEFT JOIN LATERAL" in router_source
    assert "WHERE s.sglbillno = h.billno" in router_source
    assert "COALESCE(NULLIF(sb.group_names, ''), '未归属柜组') AS group_names" in router_source
    assert "NULLIF(TRIM(s.sglmfid), '')" in router_source
    assert "l.tcflzy IN ('O', 'P', 'U', 'V')" in router_source
    assert '@router.get("/birthday-coupon/member-levels")' in router_source
    assert '@router.get("/birthday-coupon/level-members")' in router_source
    assert '@router.get("/birthday-coupon/member-sales")' in router_source
    assert '@router.get("/birthday-coupon/export-details")' in router_source
    assert '"usage_flows": usage_flows' in router_source
    assert "AS group_names" in router_source
    assert "h.rqsj >= CAST(:period_start AS date)" in router_source
    assert "h.rqsj < CAST(:period_end AS date)" in router_source
    assert "UPPER(TRIM(COALESCE(l.tcflvipno, ''))) = :member_no" in router_source


def test_birthday_coupon_export_scopes_sale_headers_before_detail_joins():
    router_source = (REPO_ROOT / "python_app/routers/activity_analysis.py").read_text()
    export_source = router_source.split(
        'async def birthday_coupon_export_details(', 1
    )[1].split(
        'def _birthday_coupon_period_context(', 1
    )[0]

    assert export_source.count("salehead_scope AS MATERIALIZED") == 2
    assert export_source.count("h.rqsj >= CAST(:cohort_start AS date)") >= 2
    assert export_source.count("h.rqsj < CAST(:cohort_end AS date)") >= 2
    assert "JOIN salehead_scope h" in export_source
