from datetime import date
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python_app"))

from services.new_century_campaign import (
    MARKET_CODE,
    PERMISSION_CODE,
    mask_member_no,
    mask_mobile,
    previous_year_period,
    safe_change_percent,
    safe_ratio,
    validate_period,
)


def test_dashboard_is_hard_scoped_to_new_century_and_has_independent_permission():
    from routers import authz

    router_source = (REPO_ROOT / "python_app/routers/new_century_campaign.py").read_text()
    migration_source = (
        REPO_ROOT / "python_app/alembic/versions/i8d9e0f1a2b3_add_new_century_campaign_permission.py"
    ).read_text()
    registered = {row[0] for row in authz.CORE_PERMISSION_DEFINITIONS}

    assert MARKET_CODE == "603"
    assert PERMISSION_CODE in registered
    assert "require_permission(db, current_user, PERMISSION_CODE)" in router_source
    assert "_require_selected_activity_store(db, scope, MARKET_CODE)" in router_source
    assert PERMISSION_CODE in migration_source
    assert "source.permission_code = 'activity_analysis.view'" in migration_source


def test_coupon_ods_migration_keeps_crm_rows_in_local_ods_schema():
    source = (REPO_ROOT / "python_app/alembic/versions/h7c8d9e0f1a2_create_new_century_coupon_ods.py").read_text()

    assert "CREATE SCHEMA IF NOT EXISTS ods" in source
    assert "CREATE TABLE ods.crm_coupon_template_603" in source
    assert "CREATE TABLE ods.crm_coupon_record_603" in source
    assert "coupon_code BIGINT PRIMARY KEY" in source
    assert "mem_mobile VARCHAR(64)" in source


def test_period_validation_and_prior_year_defaults_are_stable():
    validate_period(date(2026, 7, 31), date(2026, 8, 9), label="活动期")
    assert previous_year_period(date(2026, 7, 31), date(2026, 8, 9)) == (
        date(2025, 7, 31),
        date(2025, 8, 9),
    )
    with pytest.raises(ValueError, match="开始日期"):
        validate_period(date(2026, 8, 9), date(2026, 7, 31), label="活动期")
    with pytest.raises(ValueError, match="366"):
        validate_period(date(2025, 1, 1), date(2026, 1, 2), label="活动期")


def test_metric_helpers_do_not_invent_comparisons_when_denominator_is_zero():
    assert safe_change_percent(120, 100) == pytest.approx(20)
    assert safe_change_percent(100, 0) is None
    assert safe_ratio(22, 78, percent=True) == pytest.approx(28.205128)
    assert safe_ratio(1, 0) is None


def test_member_join_keys_are_masked_before_api_response():
    assert mask_mobile("138-1234-5678") == "138****5678"
    assert mask_member_no("1234567890") == "12******90"
    assert "13812345678" not in mask_mobile("13812345678")


def test_gift_consumption_uses_member_mapping_and_same_day_pos_sales():
    source = (REPO_ROOT / "python_app/routers/new_century_campaign.py").read_text()

    assert "LOWER(COALESCE(t.coupon_type, '')) = 'gift'" in source
    assert "regexp_replace(COALESCE(m.telephone, '')" in source
    assert "s.business_date = g.used_date AND s.member_no = g.customer_no" in source
    assert 'row["mobile"] = mask_mobile' in source
    assert "used_order_money" not in source
