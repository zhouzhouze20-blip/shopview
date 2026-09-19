from pathlib import Path
import inspect
import asyncio
from types import SimpleNamespace
from datetime import date

import pytest

from python_app.routers import activity_analysis
from python_app.services.activity_analysis import coupon_followup


def test_coupon_followup_statuses_and_masking():
    assert coupon_followup.normalize_followup_status("all") is None
    assert coupon_followup.normalize_followup_status("redeemed") == "REDEEMED"
    assert coupon_followup.followup_status_label("VISITED_NOT_REDEEMED") == "已到店未用券"
    assert coupon_followup.mask_member_no("1012343265") == "10****3265"
    assert coupon_followup.mask_member_name("张三") == "张*"
    with pytest.raises(ValueError, match="跟进状态不正确"):
        coupon_followup.normalize_followup_status("unknown")


def test_coupon_followup_uses_index_friendly_member_batches_and_existing_manager_mapping():
    source = inspect.getsource(coupon_followup.query_coupon_followups)
    assert "period_start.replace(year=period_start.year - 1)" in source
    assert "bindparam(\"member_nos\", expanding=True)" in source
    assert "NULLIF(TRIM(COALESCE(h.hykh, '')), '') IS NOT NULL" in source
    assert "category_manager_brand_assignments" in source
    assert "history_sales_amount" in source


def test_mobile_followup_requires_dedicated_permission_and_manager_scope():
    source = inspect.getsource(activity_analysis.mobile_birthday_coupon_followups)
    assert "MOBILE_COUPON_FOLLOWUP_PERMISSION" in source
    assert "subject.user_id" in source
    assert "manager_user_id=manager_user_id" in source


def test_mobile_followup_permission_creates_and_assigns_a_dedicated_manager_role():
    migration = Path(
        "python_app/alembic/versions/g6b7c8d9e0f1_add_mobile_coupon_followup.py"
    ).read_text(encoding="utf-8")
    assert "'mobile.coupon_followup.view'" in migration
    assert "'category_coupon_followup_manager'" in migration
    assert "FROM category_manager_brand_assignments assignment" in migration
    assert "TRIM(store_row.store_code) = '601'" in migration


@pytest.mark.parametrize("assigned,admin,expected_manager,expected_levels", [
    (True, False, None, ("黑钻卡会员",)),
    (True, True, None, ("黑钻卡会员",)),
    (False, False, 667, coupon_followup.FOLLOWUP_MEMBER_LEVELS),
    (False, True, None, coupon_followup.FOLLOWUP_MEMBER_LEVELS),
])
def test_mobile_black_diamond_role_scopes_effective_user(monkeypatch, assigned, admin, expected_manager, expected_levels):
    subject = SimpleNamespace(user_id=667)
    calls = []
    monkeypatch.setattr(activity_analysis, "require_permission", lambda *args: calls.append(args[-1]))
    monkeypatch.setattr(activity_analysis, "get_authz_subject", lambda *args: subject)
    def role_codes(db, user_id):
        assert user_id == subject.user_id
        return {activity_analysis.CENTER_BLACK_DIAMOND_FOLLOWUP_ROLE} if assigned else set()
    monkeypatch.setattr(activity_analysis, "get_role_codes", role_codes)
    monkeypatch.setattr(activity_analysis, "is_admin", lambda db, user: admin)
    monkeypatch.setattr(activity_analysis, "query_coupon_followups", lambda db, **kwargs: kwargs)
    result = asyncio.run(activity_analysis.mobile_birthday_coupon_followups(
        period_month="2026-09", status_code=None, keyword=None, limit=1000, offset=0,
        db=object(), current_user=SimpleNamespace(user_id=549),
    ))
    assert calls == [activity_analysis.MOBILE_COUPON_FOLLOWUP_PERMISSION]
    assert result["manager_user_id"] == expected_manager
    assert result["member_levels"] == expected_levels
    assert result["market_code"] == "601"
    assert result["period_start"] == date(2026, 9, 1)
    assert result["period_end"] == date(2026, 10, 1)


def test_black_diamond_cohort_keeps_unassigned_members_and_excludes_black_gold():
    class Result:
        def __init__(self, rows): self.rows = rows
        def mappings(self): return self
        def all(self): return self.rows
    class DB:
        def execute(self, query, params):
            sql = str(query)
            if "FROM tktcardfqlog l" in sql:
                return Result([{"member_no": n, "coupon_asset_id": n, "issue_amount": 100} for n in ["D", "G"]])
            if "FROM fj_dw_member_dim" in sql:
                return Result([
                    {"member_no": "D", "customer_name": "测试钻", "customer_level": "黑钻卡会员"},
                    {"member_no": "G", "customer_name": "测试金", "customer_level": "黑金卡会员"},
                ])
            if "FROM salehead" in sql:
                assert params["member_nos"] == ["D"]
            return Result([])
    result = coupon_followup.query_coupon_followups(
        DB(), period_start=date(2026, 9, 1), period_end=date(2026, 10, 1),
        market_code="601", issue_action="M", member_levels=("黑钻卡会员",),
    )
    assert result["total"] == result["summary"]["target_member_count"] == 1
    assert result["items"][0]["member_no"] == "D"
    assert result["items"][0]["followup_status"] == "UNASSIGNED_BRAND"
