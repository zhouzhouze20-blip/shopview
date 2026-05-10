from __future__ import annotations

from typing import Any

from .ai_report import generate_ai_report
from .config import DEFAULT_GROUP_ANALYSIS_CONFIG, SEVERITY_RANK
from .metrics import build_summary, enrich_group_rows, num
from .rules import evaluate_group_rules


def analyze_group_sales(
    rows: list[dict[str, Any]],
    *,
    scope: dict[str, Any],
    include_ai: bool = True,
    config: dict[str, float] | None = None,
) -> dict[str, Any]:
    cfg = {**DEFAULT_GROUP_ANALYSIS_CONFIG, **(config or {})}
    enriched = enrich_group_rows(rows)
    summary = build_summary(enriched)
    rankings = build_rankings(enriched, top_n=int(cfg["top_n"]))
    anomalies = build_anomalies(enriched, cfg)
    actions = build_actions(anomalies, summary)

    result = {
        "scope": scope,
        "summary": summary,
        "rankings": rankings,
        "anomalies": anomalies,
        "actions": actions,
        "config": cfg,
        "ai": {
            "enabled": include_ai,
            "status": "skipped",
            "report": None,
        },
    }

    if include_ai:
        result["ai"] = generate_ai_report(
            {
                "scope": scope,
                "summary": summary,
                "rankings": _compact_rankings(rankings),
                "anomalies": [_compact_anomaly(item) for item in anomalies[:10]],
                "actions": actions,
            }
        )

    return result


def build_rankings(rows: list[dict[str, Any]], *, top_n: int) -> dict[str, list[dict[str, Any]]]:
    return {
        "top_sales": _rank(rows, "effective_sales", top_n, reverse=True, positive_only=True),
        "top_growth": _rank(rows, "growth_contribution", top_n, reverse=True, positive_only=True),
        "top_decline": _rank(rows, "decline_impact", top_n, reverse=True, positive_only=True),
        "top_profit": _rank(rows, "net_profit", top_n, reverse=True, positive_only=True),
        "low_margin": _rank([r for r in rows if num(r.get("effective_sales")) > 0], "ticket_margin", top_n, reverse=False),
        "ticket_decline": _rank(rows, "ticket_delta", top_n, reverse=False, negative_only=True),
    }


def build_anomalies(rows: list[dict[str, Any]], config: dict[str, float]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for row in rows:
        anomalies.extend(evaluate_group_rules(row, config))
    anomalies.sort(
        key=lambda item: (
            SEVERITY_RANK.get(str(item.get("severity")), 99),
            -num(item.get("metrics", {}).get("decline_impact")),
            -num(item.get("metrics", {}).get("effective_sales")),
        )
    )
    return anomalies


def build_actions(anomalies: list[dict[str, Any]], summary: dict[str, Any]) -> list[dict[str, Any]]:
    rule_ids = {str(item.get("rule_id")) for item in anomalies}
    actions: list[dict[str, Any]] = []
    if {"R001", "R003"} & rule_ids:
        actions.append(
            {
                "priority": "high",
                "title": "优先复盘销售下滑或归零柜组",
                "description": "按销售影响金额排序，核查活动、客流、库存、柜组映射、撤场停柜和销售同步状态。",
                "related_rule_ids": sorted({"R001", "R003"} & rule_ids),
            }
        )
    if {"R005", "R006", "R007", "R008"} & rule_ids:
        actions.append(
            {
                "priority": "high",
                "title": "核查毛利质量异常柜组",
                "description": "重点检查折扣、促销、成本、联营扣率和毛利字段口径，区分经营让利和数据异常。",
                "related_rule_ids": sorted({"R005", "R006", "R007", "R008"} & rule_ids),
            }
        )
    if "R009" in rule_ids:
        actions.append(
            {
                "priority": "medium",
                "title": "跟进小票数明显下降柜组",
                "description": "结合客流、开单、收银、活动和人员排班确认成交笔数下降原因。",
                "related_rule_ids": ["R009"],
            }
        )
    if "R002" in rule_ids:
        actions.append(
            {
                "priority": "medium",
                "title": "确认异常增长柜组的增长来源",
                "description": "区分真实活动拉动、新柜组或去年低基数，并检查柜组编码与同期口径是否一致。",
                "related_rule_ids": ["R002"],
            }
        )
    if not actions:
        actions.append(
            {
                "priority": "info",
                "title": "暂无明显异常",
                "description": "当前阈值下未识别到重点异常，可继续关注头部柜组贡献和毛利率变化。",
                "related_rule_ids": [],
            }
        )
    return actions


def _rank(
    rows: list[dict[str, Any]],
    key: str,
    top_n: int,
    *,
    reverse: bool,
    positive_only: bool = False,
    negative_only: bool = False,
) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        value = num(row.get(key))
        if positive_only and value <= 0:
            continue
        if negative_only and value >= 0:
            continue
        candidates.append(row)
    ranked = sorted(candidates, key=lambda row: num(row.get(key)), reverse=reverse)[:top_n]
    return [_ranking_item(row, key) for row in ranked]


def _ranking_item(row: dict[str, Any], rank_key: str) -> dict[str, Any]:
    return {
        "group_code": row.get("group_code") or "",
        "group_name": row.get("group_name"),
        "department_code": row.get("department_code"),
        "department_name": row.get("department_name"),
        "rank_key": rank_key,
        "rank_value": row.get(rank_key),
        "effective_sales": row.get("effective_sales"),
        "same_period_effective_sales": row.get("same_period_effective_sales"),
        "sales_yoy_rate": row.get("sales_yoy_rate"),
        "net_profit": row.get("net_profit"),
        "ticket_margin": row.get("ticket_margin"),
        "ticket_count": row.get("ticket_count"),
        "same_period_ticket_count": row.get("same_period_ticket_count"),
    }


def _compact_rankings(rankings: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {key: rows[:3] for key, rows in rankings.items()}


def _compact_anomaly(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": item.get("rule_id"),
        "severity": item.get("severity"),
        "group_code": item.get("group_code"),
        "group_name": item.get("group_name"),
        "title": item.get("title"),
        "message": item.get("message"),
    }
