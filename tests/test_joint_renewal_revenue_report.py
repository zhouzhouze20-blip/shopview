from datetime import date

from services.joint_renewal_revenue_report import (
    PAIR_SQL,
    SALES_SQL,
    calculate_joint_renewal_item,
    summarize_joint_renewal_items,
)


def _raw(**overrides):
    row = {
        "new_contract_no": "NEW001",
        "old_contract_no": "OLD001",
        "store_code": "603",
        "store_name": "常州新世纪商城",
        "department_code": "60301",
        "department_name": "新世纪一部",
        "supplier_code": "SUP001",
        "supplier_name": "测试供应商",
        "group_code": "6030101001",
        "group_name": "测试柜组",
        "brand_name": "测试品牌",
        "old_start_date": date(2025, 1, 1),
        "old_end_date": date(2025, 12, 31),
        "new_start_date": date(2026, 1, 1),
        "new_end_date": date(2026, 12, 31),
        "gap_days": 0,
        "old_rate_1": 0.10,
        "new_rate_1": 0.12,
        "old_rate_2": 0,
        "old_rate_3": 0,
        "old_rate_4": 0,
        "old_rate_5": 0,
        "new_rate_2": 0,
        "new_rate_3": 0,
        "new_rate_4": 0,
        "new_rate_5": 0,
        "sales_row_count": 365,
        "sales_first_date": date(2025, 1, 1),
        "sales_last_date": date(2025, 12, 31),
        "sales_qty": 100,
        "priced_sales_amount": 1000,
        "sales_revenue": 1000,
        "actual_gross_profit": 80,
        "historical_base_profit": None,
        "historical_sales_rate_profit": None,
        "activity_rate_impact": None,
        "activity_sales_row_count": 0,
        "stored_card_amount": None,
        "voucher_amount": None,
        "member_discount_amount": None,
        "promotion_discount_amount": None,
        "recorded_payment_fee_amount": None,
    }
    row.update(overrides)
    return row


def test_joint_renewal_uses_actual_profit_as_baseline_and_only_adds_rate_delta():
    item = calculate_joint_renewal_item(
        _raw(),
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 7, 18),
    )

    assert item["base_rate_impact"] == 20
    assert item["simulated_new_profit"] == 100
    assert item["classification"] == "增长"
    assert item["activity_rate_impact"] is None
    assert item["stored_card_amount"] is None
    assert item["activity_payment_breakdown_available"] is False
    assert item["review_required"] is False


def test_joint_renewal_marks_missing_sales_and_multirate_contract_for_review():
    item = calculate_joint_renewal_item(
        _raw(sales_row_count=0, priced_sales_amount=0, actual_gross_profit=0, new_rate_2=0.05),
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 7, 18),
    )

    assert item["classification"] == "待复核"
    assert "上一合同期间无匹配销售" in item["review_reasons"]
    assert "存在扣率2-5，第一稿仅测算扣率1" in item["review_reasons"]


def test_joint_renewal_summary_counts_contracts_separately_from_group_pairs():
    first = calculate_joint_renewal_item(
        _raw(group_code="6030101001"),
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 7, 18),
    )
    second = calculate_joint_renewal_item(
        _raw(group_code="6030101002", new_rate_1=0.08),
        source_min_date=date(2025, 1, 1),
        source_max_date=date(2026, 7, 18),
    )

    summary = summarize_joint_renewal_items([first, second])

    assert summary["renewal_contract_count"] == 1
    assert summary["pair_count"] == 2
    assert summary["growth_count"] == 1
    assert summary["decline_count"] == 1


def test_joint_renewal_queries_keep_operation_and_source_boundaries_explicit():
    normalized_pairs = " ".join(PAIR_SQL.lower().split())
    normalized_sales = " ".join(SALES_SQL.lower().split())

    assert "cm.cmwmid" in normalized_pairs and "= '4'" in normalized_pairs
    assert "old_cm.cmwmid" in normalized_pairs
    assert "unit_revenue_sales_detail" in normalized_sales
    assert "salegoodslist" not in normalized_sales
    assert "source_group_code = pair.group_code" in normalized_sales
