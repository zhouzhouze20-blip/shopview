from __future__ import annotations


def point_rule_source_tables() -> tuple[str, ...]:
    return (
        "order_point",
        "salegoodslist",
        "sellpaygoods",
        "paymode",
        "tktqtype",
        "tktqtypemkt",
        "card_paymoderule",
        "rulejfrate",
    )


def point_status_case_sql(
    actual_expr: str = "actual_point",
    expected_expr: str = "expected_point",
    rate_expr: str = "jfrate",
    allocation_diff_expr: str = "allocation_diff_amount",
) -> str:
    return f"""
      CASE
        WHEN {rate_expr} IS NULL THEN 'MISSING_RATE'
        WHEN {rate_expr} = 0 THEN 'ZERO_RATE'
        WHEN ABS(COALESCE({allocation_diff_expr}, 0)) > 0.01 THEN 'ALLOCATION_IMBALANCE'
        WHEN ABS(COALESCE({actual_expr}, 0) - COALESCE({expected_expr}, 0)) > 0.01 THEN 'POINT_DIFF'
        ELSE 'OK'
      END
    """


def point_status_label(status: str | None) -> str:
    labels = {
        "OK": "正常",
        "POINT_DIFF": "积分差异",
        "MISSING_RATE": "缺积分倍率",
        "ZERO_RATE": "积分率为0",
        "ALLOCATION_IMBALANCE": "付款分摊不平",
    }
    return labels.get((status or "").strip().upper(), "待复核")
