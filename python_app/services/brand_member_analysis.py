from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session


SEGMENT_DEFINITIONS = (
    ("brand_returning", "品牌老客", 1),
    ("same_department_inflow", "同部门流入", 2),
    ("cross_department_inflow", "跨部门流入", 3),
    ("external_new", "外部招新", 4),
)

MEMBER_LEVEL_DEFINITIONS = (
    ("01", "银星会员", 1),
    ("02", "金星会员", 2),
    ("03", "黑金会员", 3),
    ("04", "黑钻会员", 4),
    ("UNIDENTIFIED", "未标识会员", 5),
)

PURCHASE_FREQUENCY_DEFINITIONS = (
    ("single_purchase", "一次客", 1),
    ("repeat_purchase", "多次客", 2),
)

BRAND_MEMBER_QUERY_TIMEOUT_SECONDS = 120

AI_FORBIDDEN_TERMS = (
    "同比",
    "环比",
    "销售码洋",
    "客单价",
    "品类到访",
    "待激活会员",
)
AI_TERM_REPLACEMENTS = {
    "较同比": "较同期",
    "较环比": "较同期",
    "同比": "较同期",
    "环比": "较同期",
    "销售码洋": "销售收入",
    "客单价": "会员人均消费",
    "品类到访": "到目标部门人数",
    "待激活会员": "历史品牌会员",
}
AI_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?")

AI_SUMMARY_FIELDS = (
    "sales_revenue",
    "positive_revenue",
    "refund_revenue",
    "ticket_count",
    "member_buyer_count",
    "member_sales_revenue",
    "member_ticket_count",
    "nonmember_sales_revenue",
    "refund_only_member_sales_revenue",
    "spend_per_buyer",
    "purchase_frequency",
    "member_sales_quantity",
    "items_per_ticket",
    "average_item_price",
    "department_rank",
    "department_group_count",
    "old_customer_repurchase_rate",
)

AI_DISPLAY_QUANTIZERS = (Decimal("1"), Decimal("0.1"), Decimal("0.01"))
AI_REQUIRED_SECTIONS = ("核心判断", "客群变化", "经营机会", "沟通建议")


def _pick(source: Any, fields: Iterable[str]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {field: source[field] for field in fields if field in source}


def _mapping_rows(source: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(source, list):
        return []
    return [row for row in source[:limit] if isinstance(row, dict)]


def _safe_period_for_ai(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {
        "period": _pick(source.get("period"), ("start_date", "end_date")),
        "summary": _pick(source.get("summary"), AI_SUMMARY_FIELDS),
        "segments": [
            _pick(row, ("code", "label", "buyer_count", "sales_revenue", "ticket_count", "buyer_share", "sales_share"))
            for row in _mapping_rows(source.get("segments"), 8)
        ],
        "member_level_consumption": [
            _pick(
                row,
                (
                    "level_code",
                    "level_label",
                    "buyer_count",
                    "sales_revenue",
                    "ticket_count",
                    "buyer_share",
                    "sales_share",
                    "spend_per_buyer",
                    "purchase_frequency",
                ),
            )
            for row in _mapping_rows(source.get("member_level_consumption"), 5)
        ],
        "purchase_frequency_analysis": [
            _pick(
                row,
                (
                    "code",
                    "label",
                    "buyer_count",
                    "buyer_share",
                    "sales_revenue",
                    "sales_share",
                    "ticket_count",
                    "sales_quantity",
                    "spend_per_buyer",
                    "purchase_frequency",
                    "average_ticket_value",
                    "items_per_ticket",
                    "average_item_price",
                ),
            )
            for row in _mapping_rows(source.get("purchase_frequency_analysis"), 2)
        ],
        "old_customer_funnel": _pick(
            source.get("old_customer_funnel"),
            ("historical_target_member_count", "store_visit_count", "department_visit_count", "target_repurchase_count"),
        ),
        "inflow_sources": [
            _pick(row, ("segment_code", "group_code", "group_name", "department_name", "buyer_count", "historical_sales"))
            for row in _mapping_rows(source.get("inflow_sources"), 10)
        ],
    }


def sanitize_ai_snapshot(snapshot: Any) -> dict[str, Any]:
    """Allow only aggregate report fields before data leaves ShopView for an AI provider."""
    if not isinstance(snapshot, dict):
        return {}
    target_source = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    safe_target = {
        **_pick(target_source, ("group_code", "group_name", "department_code", "department_name")),
        "current": _safe_period_for_ai(target_source.get("current")),
        "prior": _safe_period_for_ai(target_source.get("prior")),
    }
    safe_comparison: dict[str, Any] = {}
    comparison_source = snapshot.get("comparison")
    if isinstance(comparison_source, dict):
        for metric in AI_SUMMARY_FIELDS:
            if metric in comparison_source:
                safe_comparison[metric] = _pick(
                    comparison_source[metric],
                    ("current", "prior", "change", "change_rate"),
                )
    safe_competitors = []
    for row in _mapping_rows(snapshot.get("competitors"), 5):
        safe_competitors.append(
            {
                **_pick(row, ("group_code", "group_name", "department_name")),
                "current": _pick(row.get("current"), AI_SUMMARY_FIELDS),
                "prior": _pick(row.get("prior"), AI_SUMMARY_FIELDS),
            }
        )
    definitions_source = snapshot.get("definitions")
    safe_definitions = _pick(
        definitions_source,
        ("sales_revenue", "member_count", "history_cutoff", "internal_inflow"),
    )
    return {
        "target": safe_target,
        "comparison": safe_comparison,
        "competitors": safe_competitors,
        "definitions": safe_definitions,
    }


def _decimal_token(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value).replace(",", "").rstrip("%"))
    except (InvalidOperation, ValueError):
        return None


def _collect_allowed_numbers(value: Any, allowed: set[Decimal]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _collect_allowed_numbers(item, allowed)
        return
    if isinstance(value, list):
        for item in value:
            _collect_allowed_numbers(item, allowed)
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float, Decimal)):
        number = _decimal_token(value)
        if number is None:
            return
        allowed.add(number)
        for quantizer in AI_DISPLAY_QUANTIZERS:
            allowed.add(number.quantize(quantizer, rounding=ROUND_HALF_UP))
        if abs(number) <= 1:
            percentage = number * 100
            allowed.add(percentage)
            for quantizer in AI_DISPLAY_QUANTIZERS:
                allowed.add(percentage.quantize(quantizer, rounding=ROUND_HALF_UP))
        return
    if isinstance(value, str):
        for token in AI_NUMBER_PATTERN.findall(value):
            number = _decimal_token(token)
            if number is not None:
                allowed.add(number)


def validate_ai_conclusion(report: str | None, snapshot: dict[str, Any]) -> tuple[bool, str | None]:
    if not report or not report.strip():
        return False, "AI未返回结论"
    for term in AI_FORBIDDEN_TERMS:
        if term in report:
            return False, f"AI结论使用了禁用口径词：{term}"
    if "**" in report or "```" in report:
        return False, "AI结论未使用要求的纯文本格式"

    allowed: set[Decimal] = set()
    _collect_allowed_numbers(snapshot, allowed)
    for token in AI_NUMBER_PATTERN.findall(report):
        number = _decimal_token(token)
        if number is not None and number not in allowed:
            return False, f"AI结论出现输入中不存在的数字：{token}"
    missing_sections = [section for section in AI_REQUIRED_SECTIONS if section not in report]
    if missing_sections:
        return False, f"AI结论结构不完整，缺少：{'、'.join(missing_sections)}"
    return True, None


def normalize_ai_conclusion_terms(report: str | None) -> str | None:
    if report is None:
        return None
    normalized = report
    for forbidden, required in AI_TERM_REPLACEMENTS.items():
        normalized = normalized.replace(forbidden, required)
    return normalized


def _json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _rows(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = db.execute(text(sql), params).mappings().all()
    return [{key: _json_value(value) for key, value in row.items()} for row in result]


def _row(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    result = db.execute(text(sql), params).mappings().first()
    if result is None:
        return None
    return {key: _json_value(value) for key, value in result.items()}


def _clean_code(value: str) -> str:
    return value.strip().upper()


def _rate(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def build_comparison(current: dict[str, Any], prior: dict[str, Any]) -> dict[str, Any]:
    metrics = (
        "sales_revenue",
        "ticket_count",
        "member_buyer_count",
        "member_sales_revenue",
        "spend_per_buyer",
        "purchase_frequency",
        "items_per_ticket",
        "average_item_price",
        "old_customer_repurchase_rate",
    )
    comparison: dict[str, Any] = {}
    for metric in metrics:
        current_value = float(current.get(metric) or 0)
        prior_value = float(prior.get(metric) or 0)
        comparison[metric] = {
            "current": current_value,
            "prior": prior_value,
            "change": current_value - prior_value,
            "change_rate": _rate(current_value - prior_value, abs(prior_value)),
        }
    return comparison


def build_rule_conclusion(snapshot: dict[str, Any]) -> str:
    target = snapshot.get("target") or {}
    comparison = snapshot.get("comparison") or {}
    current = target.get("current") or {}
    current_summary = current.get("summary") or {}
    current_segments = {row.get("code"): row for row in current.get("segments") or []}

    lines: list[str] = []
    sales_change = (comparison.get("sales_revenue") or {}).get("change_rate")
    buyer_change = (comparison.get("member_buyer_count") or {}).get("change_rate")
    if sales_change is None:
        lines.append("同期销售基数为零，建议以本期绝对销售和客群结构作为沟通重点。")
    else:
        direction = "增长" if sales_change >= 0 else "下降"
        lines.append(f"本期销售收入较同期{direction}{abs(float(sales_change)):.1%}。")

    if buyer_change is not None:
        direction = "增加" if buyer_change >= 0 else "减少"
        lines.append(f"购买会员数较同期{direction}{abs(float(buyer_change)):.1%}，可结合人均消费判断变化来自客流还是消费深度。")

    old_row = current_segments.get("brand_returning") or {}
    external_row = current_segments.get("external_new") or {}
    if float(external_row.get("buyer_count") or 0) > float(old_row.get("buyer_count") or 0):
        lines.append("本期外部招新人数高于品牌老客回购人数，品牌拉新表现更突出，下一步应关注新客二次消费。")
    else:
        lines.append("本期品牌老客仍是主要购买人群，可重点关注到店但未回购品牌的历史会员。")

    rank = current_summary.get("department_rank")
    rank_total = current_summary.get("department_group_count")
    if rank and rank_total:
        lines.append(f"目标柜组本期在所属部门销售排名第{int(rank)}位，共{int(rank_total)}个有销售柜组。")
    return "\n".join(lines[:4])


def list_group_options(db: Session, store_code: str) -> list[dict[str, Any]]:
    return _rows(
        db,
        """
        SELECT
          UPPER(TRIM(BOTH FROM mf.mfcode)) AS group_code,
          COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), TRIM(BOTH FROM mf.mfcode)) AS group_name,
          NULLIF(TRIM(BOTH FROM dept.mfcode), '') AS department_code,
          NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS department_name,
          st.store_id::varchar AS scope_store_id
        FROM manaframe mf
        LEFT JOIN manaframe dept
          ON UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
             = UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
        LEFT JOIN stores st
          ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = :store_code
        WHERE TRIM(BOTH FROM mf.mfcode) LIKE :store_prefix
          AND LENGTH(TRIM(BOTH FROM mf.mfcode)) = 10
        ORDER BY department_name NULLS LAST, group_name, group_code
        """,
        {
            "store_code": store_code.strip(),
            "store_prefix": f"{store_code.strip()}%",
        },
    )


def load_group_meta(db: Session, store_code: str, group_code: str) -> dict[str, Any] | None:
    return _row(
        db,
        """
        SELECT
          UPPER(TRIM(BOTH FROM mf.mfcode)) AS group_code,
          COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), TRIM(BOTH FROM mf.mfcode)) AS group_name,
          NULLIF(TRIM(BOTH FROM dept.mfcode), '') AS department_code,
          NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS department_name,
          st.store_id::varchar AS scope_store_id
        FROM manaframe mf
        LEFT JOIN manaframe dept
          ON UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
             = UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
        LEFT JOIN stores st
          ON TRIM(BOTH FROM COALESCE(st.store_code, '')) = :store_code
        WHERE UPPER(TRIM(BOTH FROM COALESCE(mf.mfcode, ''))) = :group_code
          AND SUBSTRING(TRIM(BOTH FROM COALESCE(mf.mfcode, '')) FROM 1 FOR 3) = :store_code
        LIMIT 1
        """,
        {"store_code": store_code.strip(), "group_code": _clean_code(group_code)},
    )


def _period_classification_ctes() -> str:
    return """
    target_lines AS MATERIALIZED (
      SELECT
        s.sglbillno AS billno,
        COALESCE(s.sglxssr, 0)::numeric AS sales_revenue,
        NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no
      FROM salegoodslist s
      LEFT JOIN salehead h
        ON h.billno = s.sglbillno
       AND h.mkt::text = s.sglmarket::text
      WHERE s.sglmarket::text = :store_code
        AND s.sglmfid = :target_group_code
        AND s.sglhsrq BETWEEN :start_date AND :end_date
    ),
    period_member_receipts AS MATERIALIZED (
      SELECT
        member_no,
        billno,
        SUM(sales_revenue) AS sales_revenue
      FROM target_lines
      WHERE member_no IS NOT NULL
      GROUP BY member_no, billno
    ),
    period_member_rows AS MATERIALIZED (
      SELECT
        member_no,
        SUM(sales_revenue) AS sales_revenue,
        COUNT(*) FILTER (WHERE sales_revenue > 0) AS ticket_count,
        BOOL_OR(sales_revenue > 0) AS has_positive_purchase
      FROM period_member_receipts
      GROUP BY member_no
    ),
    purchase_members AS MATERIALIZED (
      SELECT member_no, sales_revenue, ticket_count
      FROM period_member_rows
      WHERE has_positive_purchase IS TRUE
    ),
    member_history_heads AS MATERIALIZED (
      SELECT
        h.billno,
        h.store_code,
        pm.member_no
      FROM purchase_members pm
      CROSS JOIN LATERAL (
        SELECT h.billno, h.mkt AS store_code
        FROM salehead h
        WHERE h.mkt = :store_code
          AND NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') = pm.member_no
          AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
        OFFSET 0
      ) h
    ),
    history AS MATERIALIZED (
      SELECT
        heads.member_no,
        BOOL_OR(
          s.sglmfid = :target_group_code
          AND COALESCE(s.sglxssr, 0) > 0
        ) AS had_target_purchase,
        BOOL_OR(
          UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, ''))) = :target_department_code
          AND COALESCE(s.sglxssr, 0) > 0
        ) AS had_same_department_purchase,
        BOOL_OR(COALESCE(s.sglxssr, 0) > 0) AS had_store_purchase
      FROM member_history_heads heads
      CROSS JOIN LATERAL (
        SELECT s.sglmfid, s.sglxssr
        FROM salegoodslist s
        WHERE s.sglbillno = heads.billno
          AND s.sglmarket = heads.store_code
          AND s.sglhsrq < :start_date
        OFFSET 0
      ) s
      LEFT JOIN manaframe mf
        ON mf.mfcode = s.sglmfid
      GROUP BY heads.member_no
    ),
    classified AS MATERIALIZED (
      SELECT
        pm.member_no,
        pm.sales_revenue,
        pm.ticket_count,
        CASE
          WHEN COALESCE(history.had_target_purchase, FALSE) THEN 'brand_returning'
          WHEN COALESCE(history.had_same_department_purchase, FALSE) THEN 'same_department_inflow'
          WHEN COALESCE(history.had_store_purchase, FALSE) THEN 'cross_department_inflow'
          ELSE 'external_new'
        END AS segment_code
      FROM purchase_members pm
      LEFT JOIN history ON history.member_no = pm.member_no
    )
    """


def _load_member_level_consumption(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    level_values = ", ".join(
        f"('{code}', '{label}', {sort_order})"
        for code, label, sort_order in MEMBER_LEVEL_DEFINITIONS
    )
    rows = _rows(
        db,
        f"""
        WITH member_level_rows AS MATERIALIZED (
          SELECT
            CASE
              WHEN TRIM(BOTH FROM COALESCE(h.custtype, '')) IN ('01', '02', '03', '04')
              THEN TRIM(BOTH FROM h.custtype)
              ELSE 'UNIDENTIFIED'
            END AS level_code,
            NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no,
            s.sglbillno AS billno,
            COALESCE(s.sglxssr, 0)::numeric AS sales_revenue
          FROM salegoodslist s
          JOIN salehead h
            ON h.billno = s.sglbillno
           AND h.mkt::text = s.sglmarket::text
          WHERE s.sglmarket::text = :store_code
            AND s.sglmfid = :target_group_code
            AND s.sglhsrq BETWEEN :start_date AND :end_date
            AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
        ),
        member_level_receipts AS MATERIALIZED (
          SELECT
            level_code,
            member_no,
            billno,
            SUM(sales_revenue) AS sales_revenue
          FROM member_level_rows
          GROUP BY level_code, member_no, billno
        ),
        member_level_members AS MATERIALIZED (
          SELECT
            level_code,
            member_no,
            SUM(sales_revenue) AS sales_revenue,
            COUNT(*) FILTER (WHERE sales_revenue > 0) AS ticket_count,
            BOOL_OR(sales_revenue > 0) AS has_positive_purchase
          FROM member_level_receipts
          GROUP BY level_code, member_no
        ),
        level_totals AS (
          SELECT
            level_code,
            COUNT(*) AS buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue,
            COALESCE(SUM(ticket_count), 0) AS ticket_count
          FROM member_level_members
          WHERE has_positive_purchase IS TRUE
          GROUP BY level_code
        ),
        level_defs(level_code, level_label, sort_order) AS (VALUES {level_values}),
        all_totals AS (
          SELECT
            COALESCE(SUM(buyer_count), 0) AS buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue
          FROM level_totals
        )
        SELECT
          defs.level_code,
          defs.level_label,
          COALESCE(totals.buyer_count, 0) AS buyer_count,
          COALESCE(totals.sales_revenue, 0) AS sales_revenue,
          COALESCE(totals.ticket_count, 0) AS ticket_count,
          CASE
            WHEN all_totals.buyer_count = 0 THEN NULL
            ELSE COALESCE(totals.buyer_count, 0)::numeric / all_totals.buyer_count
          END AS buyer_share,
          CASE
            WHEN all_totals.sales_revenue = 0 THEN NULL
            ELSE COALESCE(totals.sales_revenue, 0) / all_totals.sales_revenue
          END AS sales_share,
          CASE
            WHEN COALESCE(totals.buyer_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_revenue, 0) / totals.buyer_count
          END AS spend_per_buyer,
          CASE
            WHEN COALESCE(totals.buyer_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.ticket_count, 0)::numeric / totals.buyer_count
          END AS purchase_frequency,
          CASE
            WHEN COALESCE(totals.ticket_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_revenue, 0) / totals.ticket_count
          END AS average_ticket_value
        FROM level_defs defs
        CROSS JOIN all_totals
        LEFT JOIN level_totals totals ON totals.level_code = defs.level_code
        ORDER BY defs.sort_order
        """,
        params,
    )
    for row in rows:
        row["buyer_count"] = int(float(row.get("buyer_count") or 0))
        row["ticket_count"] = int(float(row.get("ticket_count") or 0))
    return rows


def _load_purchase_frequency_analysis(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    frequency_values = ", ".join(
        f"('{code}', '{label}', {sort_order})"
        for code, label, sort_order in PURCHASE_FREQUENCY_DEFINITIONS
    )
    rows = _rows(
        db,
        f"""
        WITH member_lines AS MATERIALIZED (
          SELECT
            NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no,
            s.sglbillno AS billno,
            COALESCE(s.sglxssr, 0)::numeric AS sales_revenue,
            COALESCE(s.sglsl, 0)::numeric AS sales_quantity
          FROM salegoodslist s
          JOIN salehead h
            ON h.billno = s.sglbillno
           AND h.mkt::text = s.sglmarket::text
          WHERE s.sglmarket::text = :store_code
            AND s.sglmfid = :target_group_code
            AND s.sglhsrq BETWEEN :start_date AND :end_date
            AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
        ),
        member_receipts AS MATERIALIZED (
          SELECT
            member_no,
            billno,
            SUM(sales_revenue) AS sales_revenue,
            SUM(sales_quantity) AS sales_quantity
          FROM member_lines
          GROUP BY member_no, billno
        ),
        period_members AS MATERIALIZED (
          SELECT
            member_no,
            SUM(sales_revenue) AS sales_revenue,
            SUM(sales_quantity) AS sales_quantity,
            COUNT(*) FILTER (WHERE sales_revenue > 0) AS ticket_count,
            BOOL_OR(sales_revenue > 0) AS has_positive_purchase
          FROM member_receipts
          GROUP BY member_no
        ),
        purchase_members AS MATERIALIZED (
          SELECT
            member_no,
            sales_revenue,
            sales_quantity,
            ticket_count,
            CASE WHEN ticket_count = 1 THEN 'single_purchase' ELSE 'repeat_purchase' END AS frequency_code
          FROM period_members
          WHERE has_positive_purchase IS TRUE
        ),
        frequency_totals AS (
          SELECT
            frequency_code AS code,
            COUNT(*) AS buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue,
            COALESCE(SUM(sales_quantity), 0) AS sales_quantity,
            COALESCE(SUM(ticket_count), 0) AS ticket_count
          FROM purchase_members
          GROUP BY frequency_code
        ),
        all_totals AS (
          SELECT
            COALESCE(SUM(buyer_count), 0) AS buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue
          FROM frequency_totals
        ),
        frequency_defs(code, label, sort_order) AS (VALUES {frequency_values})
        SELECT
          defs.code,
          defs.label,
          COALESCE(totals.buyer_count, 0) AS buyer_count,
          COALESCE(totals.sales_revenue, 0) AS sales_revenue,
          COALESCE(totals.sales_quantity, 0) AS sales_quantity,
          COALESCE(totals.ticket_count, 0) AS ticket_count,
          CASE
            WHEN all_totals.buyer_count = 0 THEN NULL
            ELSE COALESCE(totals.buyer_count, 0)::numeric / all_totals.buyer_count
          END AS buyer_share,
          CASE
            WHEN all_totals.sales_revenue = 0 THEN NULL
            ELSE COALESCE(totals.sales_revenue, 0) / all_totals.sales_revenue
          END AS sales_share,
          CASE
            WHEN COALESCE(totals.buyer_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_revenue, 0) / totals.buyer_count
          END AS spend_per_buyer,
          CASE
            WHEN COALESCE(totals.buyer_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.ticket_count, 0)::numeric / totals.buyer_count
          END AS purchase_frequency,
          CASE
            WHEN COALESCE(totals.ticket_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_revenue, 0) / totals.ticket_count
          END AS average_ticket_value,
          CASE
            WHEN COALESCE(totals.ticket_count, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_quantity, 0) / totals.ticket_count
          END AS items_per_ticket,
          CASE
            WHEN COALESCE(totals.sales_quantity, 0) = 0 THEN 0
            ELSE COALESCE(totals.sales_revenue, 0) / totals.sales_quantity
          END AS average_item_price
        FROM frequency_defs defs
        CROSS JOIN all_totals
        LEFT JOIN frequency_totals totals ON totals.code = defs.code
        ORDER BY defs.sort_order
        """,
        params,
    )
    for row in rows:
        row["buyer_count"] = int(float(row.get("buyer_count") or 0))
        row["ticket_count"] = int(float(row.get("ticket_count") or 0))
    return rows


def _load_period(
    db: Session,
    *,
    store_code: str,
    target_group_code: str,
    target_department_code: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    segment_values = ", ".join(
        f"('{code}', '{label}', {sort_order})" for code, label, sort_order in SEGMENT_DEFINITIONS
    )
    params = {
        "store_code": store_code.strip(),
        "target_group_code": _clean_code(target_group_code),
        "target_department_code": _clean_code(target_department_code),
        "start_date": start_date,
        "end_date": end_date,
    }
    rows = _rows(
        db,
        f"""
        WITH
        {_period_classification_ctes()},
        summary AS (
          SELECT
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue,
            COALESCE(SUM(sales_revenue) FILTER (WHERE sales_revenue > 0), 0) AS positive_revenue,
            COALESCE(SUM(sales_revenue) FILTER (WHERE sales_revenue < 0), 0) AS refund_revenue,
            COUNT(DISTINCT billno) AS ticket_count,
            COALESCE(SUM(sales_revenue) FILTER (WHERE member_no IS NULL), 0) AS nonmember_sales_revenue
          FROM target_lines
        ),
        member_summary AS (
          SELECT
            COUNT(*) AS member_buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS member_sales_revenue,
            COALESCE(SUM(ticket_count), 0) AS member_ticket_count
          FROM purchase_members
        ),
        refund_only AS (
          SELECT COALESCE(SUM(sales_revenue), 0) AS refund_only_member_sales_revenue
          FROM period_member_rows
          WHERE has_positive_purchase IS FALSE
        ),
        segment_defs(code, label, sort_order) AS (VALUES {segment_values}),
        segment_totals AS (
          SELECT
            segment_code AS code,
            COUNT(*) AS buyer_count,
            COALESCE(SUM(sales_revenue), 0) AS sales_revenue,
            COALESCE(SUM(ticket_count), 0) AS ticket_count
          FROM classified
          GROUP BY segment_code
        )
        SELECT
          summary.sales_revenue,
          summary.positive_revenue,
          summary.refund_revenue,
          summary.ticket_count,
          summary.nonmember_sales_revenue,
          member_summary.member_buyer_count,
          member_summary.member_sales_revenue,
          member_summary.member_ticket_count,
          refund_only.refund_only_member_sales_revenue,
          CASE
            WHEN member_summary.member_buyer_count = 0 THEN 0
            ELSE member_summary.member_sales_revenue / member_summary.member_buyer_count
          END AS spend_per_buyer,
          CASE
            WHEN member_summary.member_buyer_count = 0 THEN 0
            ELSE member_summary.member_ticket_count::numeric / member_summary.member_buyer_count
          END AS purchase_frequency,
          defs.code AS segment_code,
          defs.label AS segment_label,
          defs.sort_order,
          COALESCE(totals.buyer_count, 0) AS segment_buyer_count,
          COALESCE(totals.sales_revenue, 0) AS segment_sales_revenue,
          COALESCE(totals.ticket_count, 0) AS segment_ticket_count
        FROM summary
        CROSS JOIN member_summary
        CROSS JOIN refund_only
        CROSS JOIN segment_defs defs
        LEFT JOIN segment_totals totals ON totals.code = defs.code
        ORDER BY defs.sort_order
        """,
        params,
    )

    summary: dict[str, Any] = {
        "sales_revenue": 0,
        "positive_revenue": 0,
        "refund_revenue": 0,
        "ticket_count": 0,
        "member_buyer_count": 0,
        "member_sales_revenue": 0,
        "member_ticket_count": 0,
        "nonmember_sales_revenue": 0,
        "refund_only_member_sales_revenue": 0,
        "spend_per_buyer": 0,
        "purchase_frequency": 0,
        "member_sales_quantity": 0,
        "items_per_ticket": 0,
        "average_item_price": 0,
    }
    segments: list[dict[str, Any]] = []
    if rows:
        first = rows[0]
        for key in tuple(summary):
            summary[key] = first.get(key) or 0
        buyer_total = float(summary["member_buyer_count"] or 0)
        member_sales_total = float(summary["member_sales_revenue"] or 0)
        for row in rows:
            buyer_count = float(row.get("segment_buyer_count") or 0)
            sales_revenue = float(row.get("segment_sales_revenue") or 0)
            segments.append(
                {
                    "code": row.get("segment_code"),
                    "label": row.get("segment_label"),
                    "buyer_count": int(buyer_count),
                    "sales_revenue": sales_revenue,
                    "ticket_count": int(float(row.get("segment_ticket_count") or 0)),
                    "buyer_share": _rate(buyer_count, buyer_total),
                    "sales_share": _rate(sales_revenue, member_sales_total),
                }
            )

    rank = _load_department_rank(db, params)
    summary.update(rank)
    funnel = _load_old_customer_funnel(db, params)
    summary["old_customer_repurchase_rate"] = _rate(
        float(funnel.get("target_repurchase_count") or 0),
        float(funnel.get("historical_target_member_count") or 0),
    ) or 0
    purchase_frequency_analysis = _load_purchase_frequency_analysis(db, params)
    member_sales_quantity = sum(
        float(row.get("sales_quantity") or 0) for row in purchase_frequency_analysis
    )
    summary["member_sales_quantity"] = member_sales_quantity
    summary["items_per_ticket"] = _rate(
        member_sales_quantity,
        float(summary.get("member_ticket_count") or 0),
    ) or 0
    summary["average_item_price"] = _rate(
        float(summary.get("member_sales_revenue") or 0),
        member_sales_quantity,
    ) or 0
    return {
        "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "summary": summary,
        "segments": segments,
        "member_level_consumption": _load_member_level_consumption(db, params),
        "purchase_frequency_analysis": purchase_frequency_analysis,
        "old_customer_funnel": funnel,
        "inflow_sources": _load_inflow_sources(db, params),
    }


def _load_department_rank(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    row = _row(
        db,
        """
        WITH department_groups AS MATERIALIZED (
          SELECT TRIM(BOTH FROM mfcode) AS group_code
          FROM manaframe
          WHERE TRIM(BOTH FROM mfpcode) = :target_department_code
        ),
        group_sales AS (
          SELECT
            s.sglmfid AS group_code,
            SUM(COALESCE(s.sglxssr, 0)) AS sales_revenue
          FROM department_groups groups
          JOIN salegoodslist s
            ON s.sglmfid = groups.group_code
          WHERE s.sglmarket = :store_code
            AND s.sglhsrq BETWEEN :start_date AND :end_date
          GROUP BY s.sglmfid
        ),
        ranked AS (
          SELECT
            group_code,
            DENSE_RANK() OVER (ORDER BY sales_revenue DESC) AS department_rank,
            COUNT(*) OVER () AS department_group_count
          FROM group_sales
        )
        SELECT department_rank, department_group_count
        FROM ranked
        WHERE group_code = :target_group_code
        """,
        params,
    )
    return row or {"department_rank": None, "department_group_count": 0}


def _load_old_customer_funnel(db: Session, params: dict[str, Any]) -> dict[str, Any]:
    funnel_params = {
        **params,
        "store_prefix": f"{str(params['store_code']).strip()}%",
    }
    row = _row(
        db,
        """
        WITH old_members AS MATERIALIZED (
          SELECT DISTINCT NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no
          FROM salehead h
          JOIN salegoodslist s
            ON s.sglbillno = h.billno
           AND s.sglmarket = h.mkt
          WHERE s.sglmarket = :store_code
            AND s.sglmfid = :target_group_code
            AND s.sglhsrq < :start_date
            AND COALESCE(s.sglxssr, 0) > 0
            AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
        ),
        store_groups AS MATERIALIZED (
          SELECT UPPER(TRIM(BOTH FROM mf.mfcode)) AS group_code
          FROM manaframe mf
          WHERE TRIM(BOTH FROM mf.mfcode) LIKE :store_prefix
            AND LENGTH(TRIM(BOTH FROM mf.mfcode)) = 10
        ),
        period_lines AS MATERIALIZED (
          SELECT
            NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no,
            UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, ''))) AS department_code,
            UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))) AS group_code
          FROM store_groups groups
          JOIN salegoodslist s
            ON s.sglmarket = :store_code
           AND s.sglmfid = groups.group_code
           AND s.sglhsrq BETWEEN :start_date AND :end_date
           AND COALESCE(s.sglxssr, 0) > 0
          CROSS JOIN LATERAL (
            SELECT h.hykh
            FROM salehead h
            WHERE h.billno = s.sglbillno
              AND h.mkt = s.sglmarket
            OFFSET 0
          ) h
          LEFT JOIN manaframe mf
            ON mf.mfcode = s.sglmfid
        ),
        period_activity AS MATERIALIZED (
          SELECT
            old.member_no,
            TRUE AS visited_store,
            BOOL_OR(lines.department_code = :target_department_code) AS visited_department,
            BOOL_OR(lines.group_code = :target_group_code) AS repurchased_target
          FROM old_members old
          JOIN period_lines lines
            ON lines.member_no = old.member_no
          GROUP BY old.member_no
        )
        SELECT
          COUNT(*) AS historical_target_member_count,
          COUNT(*) FILTER (WHERE COALESCE(activity.visited_store, FALSE)) AS store_visit_count,
          COUNT(*) FILTER (WHERE COALESCE(activity.visited_department, FALSE)) AS department_visit_count,
          COUNT(*) FILTER (WHERE COALESCE(activity.repurchased_target, FALSE)) AS target_repurchase_count
        FROM old_members old
        LEFT JOIN period_activity activity ON activity.member_no = old.member_no
        """,
        funnel_params,
    )
    return row or {
        "historical_target_member_count": 0,
        "store_visit_count": 0,
        "department_visit_count": 0,
        "target_repurchase_count": 0,
    }


def _load_inflow_sources(db: Session, params: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(
        db,
        f"""
        WITH
        {_period_classification_ctes()},
        internal_members AS MATERIALIZED (
          SELECT member_no, segment_code
          FROM classified
          WHERE segment_code IN ('same_department_inflow', 'cross_department_inflow')
        ),
        internal_member_heads AS MATERIALIZED (
          SELECT
            h.billno,
            h.store_code,
            members.member_no,
            members.segment_code
          FROM internal_members members
          CROSS JOIN LATERAL (
            SELECT h.billno, h.mkt AS store_code
            FROM salehead h
            WHERE h.mkt = :store_code
              AND NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') = members.member_no
              AND NULLIF(TRIM(BOTH FROM COALESCE(h.hykh, '')), '') IS NOT NULL
            OFFSET 0
          ) h
        ),
        source_sales AS MATERIALIZED (
          SELECT
            heads.member_no,
            heads.segment_code,
            UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))) AS source_group_code,
            COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), TRIM(BOTH FROM s.sglmfid)) AS source_group_name,
            NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS source_department_name,
            SUM(COALESCE(s.sglxssr, 0)) AS historical_sales,
            BOOL_OR(COALESCE(s.sglxssr, 0) > 0) AS had_positive_purchase
          FROM internal_member_heads heads
          CROSS JOIN LATERAL (
            SELECT s.sglmfid, s.sglxssr
            FROM salegoodslist s
            WHERE s.sglbillno = heads.billno
              AND s.sglmarket = heads.store_code
              AND s.sglhsrq < :start_date
            OFFSET 0
          ) s
          LEFT JOIN manaframe mf
            ON mf.mfcode = s.sglmfid
          LEFT JOIN manaframe dept
            ON UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
               = UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
          WHERE UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))) <> :target_group_code
          GROUP BY heads.member_no, heads.segment_code, source_group_code, source_group_name, source_department_name
        ),
        ranked AS (
          SELECT
            source_sales.*,
            ROW_NUMBER() OVER (
              PARTITION BY member_no
              ORDER BY historical_sales DESC, source_group_code
            ) AS source_rank
          FROM source_sales
          WHERE had_positive_purchase IS TRUE
        )
        SELECT
          segment_code,
          source_group_code AS group_code,
          source_group_name AS group_name,
          source_department_name AS department_name,
          COUNT(*) AS buyer_count,
          SUM(historical_sales) AS historical_sales
        FROM ranked
        WHERE source_rank = 1
        GROUP BY segment_code, source_group_code, source_group_name, source_department_name
        ORDER BY buyer_count DESC, historical_sales DESC
        LIMIT 10
        """,
        params,
    )


def _competitor_metrics(
    db: Session,
    *,
    store_code: str,
    competitor_codes: Iterable[str],
    current_start: date,
    current_end: date,
    prior_start: date,
    prior_end: date,
) -> list[dict[str, Any]]:
    codes = tuple(dict.fromkeys(_clean_code(code) for code in competitor_codes if code.strip()))
    if not codes:
        return []
    placeholders = []
    params: dict[str, Any] = {
        "store_code": store_code.strip(),
        "current_start": current_start,
        "current_end": current_end,
        "prior_start": prior_start,
        "prior_end": prior_end,
    }
    for index, code in enumerate(codes):
        key = f"competitor_{index}"
        placeholders.append(f":{key}")
        params[key] = code
    rows = _rows(
        db,
        f"""
        WITH periods(period_key, start_date, end_date) AS (
          VALUES
            ('current', CAST(:current_start AS date), CAST(:current_end AS date)),
            ('prior', CAST(:prior_start AS date), CAST(:prior_end AS date))
        ),
        lines AS MATERIALIZED (
          SELECT
            periods.period_key,
            UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))) AS group_code,
            s.sglbillno AS billno,
            COALESCE(s.sglxssr, 0) AS sales_revenue,
            NULLIF(UPPER(TRIM(BOTH FROM COALESCE(h.hykh, ''))), '') AS member_no
          FROM periods
          JOIN salegoodslist s ON s.sglhsrq BETWEEN periods.start_date AND periods.end_date
          LEFT JOIN salehead h
            ON h.billno = s.sglbillno
           AND TRIM(BOTH FROM COALESCE(h.mkt::text, '')) = TRIM(BOTH FROM COALESCE(s.sglmarket::text, ''))
          WHERE TRIM(BOTH FROM COALESCE(s.sglmarket::text, '')) = :store_code
            AND UPPER(TRIM(BOTH FROM COALESCE(s.sglmfid, ''))) IN ({', '.join(placeholders)})
        ),
        member_groups AS MATERIALIZED (
          SELECT
            period_key,
            group_code,
            member_no,
            SUM(sales_revenue) AS member_sales_revenue,
            COUNT(DISTINCT billno) AS member_ticket_count,
            BOOL_OR(sales_revenue > 0) AS has_positive_purchase
          FROM lines
          WHERE member_no IS NOT NULL
          GROUP BY period_key, group_code, member_no
        ),
        group_summary AS (
          SELECT
            lines.period_key,
            lines.group_code,
            SUM(lines.sales_revenue) AS sales_revenue,
            COUNT(DISTINCT lines.billno) AS ticket_count
          FROM lines
          GROUP BY lines.period_key, lines.group_code
        ),
        member_summary AS (
          SELECT
            period_key,
            group_code,
            COUNT(*) AS member_buyer_count,
            SUM(member_sales_revenue) AS member_sales_revenue,
            SUM(member_ticket_count) AS member_ticket_count
          FROM member_groups
          WHERE has_positive_purchase IS TRUE
          GROUP BY period_key, group_code
        )
        SELECT
          groups.group_code,
          COALESCE(NULLIF(TRIM(BOTH FROM mf.mfcname), ''), groups.group_code) AS group_name,
          NULLIF(TRIM(BOTH FROM dept.mfcname), '') AS department_name,
          periods.period_key,
          COALESCE(group_summary.sales_revenue, 0) AS sales_revenue,
          COALESCE(group_summary.ticket_count, 0) AS ticket_count,
          COALESCE(member_summary.member_buyer_count, 0) AS member_buyer_count,
          COALESCE(member_summary.member_sales_revenue, 0) AS member_sales_revenue,
          CASE
            WHEN COALESCE(member_summary.member_buyer_count, 0) = 0 THEN 0
            ELSE member_summary.member_sales_revenue / member_summary.member_buyer_count
          END AS spend_per_buyer,
          CASE
            WHEN COALESCE(member_summary.member_buyer_count, 0) = 0 THEN 0
            ELSE member_summary.member_ticket_count::numeric / member_summary.member_buyer_count
          END AS purchase_frequency
        FROM (VALUES {', '.join(f'({placeholder})' for placeholder in placeholders)}) groups(group_code)
        CROSS JOIN periods
        LEFT JOIN group_summary
          ON group_summary.group_code = groups.group_code
         AND group_summary.period_key = periods.period_key
        LEFT JOIN member_summary
          ON member_summary.group_code = groups.group_code
         AND member_summary.period_key = periods.period_key
        LEFT JOIN manaframe mf
          ON UPPER(TRIM(BOTH FROM COALESCE(mf.mfcode, ''))) = groups.group_code
        LEFT JOIN manaframe dept
          ON UPPER(TRIM(BOTH FROM COALESCE(dept.mfcode, '')))
             = UPPER(TRIM(BOTH FROM COALESCE(mf.mfpcode, '')))
        ORDER BY group_name, periods.period_key
        """,
        params,
    )
    competitors: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("group_code") or "")
        item = competitors.setdefault(
            code,
            {
                "group_code": code,
                "group_name": row.get("group_name") or code,
                "department_name": row.get("department_name"),
                "current": {},
                "prior": {},
            },
        )
        period_key = str(row.get("period_key") or "")
        item[period_key] = {
            key: row.get(key) or 0
            for key in (
                "sales_revenue",
                "ticket_count",
                "member_buyer_count",
                "member_sales_revenue",
                "spend_per_buyer",
                "purchase_frequency",
            )
        }
    return [competitors[code] for code in codes]


def load_brand_member_analysis(
    db: Session,
    *,
    store_code: str,
    target_group_code: str,
    competitor_group_codes: Iterable[str],
    current_start: date,
    current_end: date,
    prior_start: date,
    prior_end: date,
) -> dict[str, Any]:
    target = load_group_meta(db, store_code, target_group_code)
    if target is None:
        raise ValueError("目标柜组不存在，或不属于所选门店")
    department_code = str(target.get("department_code") or "").strip()
    if not department_code:
        raise ValueError("目标柜组缺少部门归属，暂时无法计算内部流入和部门排名")

    db.execute(
        text(f"SET LOCAL statement_timeout = '{BRAND_MEMBER_QUERY_TIMEOUT_SECONDS}s'"),
        {},
    )

    current = _load_period(
        db,
        store_code=store_code,
        target_group_code=target_group_code,
        target_department_code=department_code,
        start_date=current_start,
        end_date=current_end,
    )
    prior = _load_period(
        db,
        store_code=store_code,
        target_group_code=target_group_code,
        target_department_code=department_code,
        start_date=prior_start,
        end_date=prior_end,
    )
    competitors = _competitor_metrics(
        db,
        store_code=store_code,
        competitor_codes=competitor_group_codes,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
    )
    public_target = {key: value for key, value in target.items() if key != "scope_store_id"}
    return {
        "scope": {
            "store_code": store_code.strip(),
            "target_group_code": _clean_code(target_group_code),
            "competitor_group_codes": [
                _clean_code(code) for code in competitor_group_codes if code.strip()
            ],
        },
        "target": {**public_target, "current": current, "prior": prior},
        "comparison": build_comparison(current["summary"], prior["summary"]),
        "competitors": competitors,
        "definitions": {
            "sales_revenue": "salegoodslist.sglxssr 正负数净额",
            "member_count": "期间目标柜组至少发生一笔正向销售的非空会员卡号数",
            "history_cutoff": "分别追溯至本期或同期开始日期之前的全部历史",
            "internal_inflow": "内部流入包含同部门流入和跨部门流入",
            "member_level": "会员等级取交易小票 salehead.custtype：01银星、02金星、03黑金、04黑钻，其他非空会员归为未标识会员；按等级内会员去重，期间等级变化的会员可能出现在多个等级",
            "member_level_average_ticket_value": "会员等级客单按该等级会员销售收入净额除以正向购买小票数计算，退货小票不计客次",
            "purchase_frequency_segments": "一次客为期间内1张正向购买小票，多次客为期间内2张及以上正向购买小票；退货小票不计客次",
            "items_per_ticket": "客件数按会员净销售件数 salegoodslist.sglsl 除以正向购买小票数计算，退货数量按负数冲减",
            "average_item_price": "件单价按会员销售收入净额除以会员净销售件数计算",
        },
    }
