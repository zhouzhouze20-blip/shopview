from __future__ import annotations

from typing import Any

from .metrics import num


def money(value: float) -> str:
    return f"{value:,.0f}"


def pct(value: float | None) -> str:
    if value is None:
        return "无法计算"
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.2f}%"


def pp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f} 个百分点"


def group_label(row: dict[str, Any]) -> str:
    return str(row.get("group_name") or row.get("group_code") or "未命名柜组")


def anomaly(
    *,
    row: dict[str, Any],
    rule_id: str,
    severity: str,
    title: str,
    message: str,
    metrics: dict[str, Any],
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "group_code": row.get("group_code") or "",
        "group_name": row.get("group_name"),
        "department_code": row.get("department_code"),
        "department_name": row.get("department_name"),
        "title": title,
        "message": message,
        "metrics": metrics,
        "thresholds": thresholds,
    }


def evaluate_group_rules(row: dict[str, Any], config: dict[str, float]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    name = group_label(row)
    sales = num(row.get("effective_sales"))
    prior_sales = num(row.get("same_period_effective_sales"))
    sales_yoy = row.get("sales_yoy_rate")
    margin = num(row.get("ticket_margin"))
    margin_delta_pp = num(row.get("margin_delta_pp"))
    ticket_yoy = row.get("ticket_yoy_rate")
    sales_share = num(row.get("sales_share"))

    if prior_sales >= config["min_prior_sales_for_yoy"] and sales_yoy is not None and sales_yoy <= config["large_decline_rate"]:
        out.append(
            anomaly(
                row=row,
                rule_id="R001",
                severity="high",
                title="销售明显下滑",
                message=f"{name} 本期销售 {money(sales)} 元，较同期 {money(prior_sales)} 元下降 {pct(sales_yoy)}，减少 {money(num(row.get('decline_impact')))} 元。",
                metrics=_core_metrics(row),
                thresholds={
                    "large_decline_rate": config["large_decline_rate"],
                    "min_prior_sales_for_yoy": config["min_prior_sales_for_yoy"],
                },
            )
        )

    if (
        prior_sales >= config["min_prior_sales_for_yoy"]
        and sales >= config["min_sales_for_yoy"]
        and sales_yoy is not None
        and sales_yoy >= config["large_growth_rate"]
    ):
        out.append(
            anomaly(
                row=row,
                rule_id="R002",
                severity="medium",
                title="销售异常增长",
                message=f"{name} 本期销售 {money(sales)} 元，较同期 {money(prior_sales)} 元增长 {pct(sales_yoy)}，需确认活动、基数或口径变化。",
                metrics=_core_metrics(row),
                thresholds={
                    "large_growth_rate": config["large_growth_rate"],
                    "min_sales_for_yoy": config["min_sales_for_yoy"],
                    "min_prior_sales_for_yoy": config["min_prior_sales_for_yoy"],
                },
            )
        )

    if prior_sales >= config["min_prior_sales_for_yoy"] and sales <= 0:
        out.append(
            anomaly(
                row=row,
                rule_id="R003",
                severity="critical",
                title="同期有销售，本期无销售",
                message=f"{name} 同期销售 {money(prior_sales)} 元，本期无销售，需优先核查是否停柜、撤场、销售未同步或柜组映射变化。",
                metrics=_core_metrics(row),
                thresholds={"min_prior_sales_for_yoy": config["min_prior_sales_for_yoy"]},
            )
        )

    if sales >= config["min_sales_for_yoy"] and prior_sales <= 0:
        out.append(
            anomaly(
                row=row,
                rule_id="R004",
                severity="info",
                title="本期有销售，同期无销售",
                message=f"{name} 本期销售 {money(sales)} 元，同期无销售，可能是新柜组、新品牌或柜组编码变化。",
                metrics=_core_metrics(row),
                thresholds={"min_sales_for_yoy": config["min_sales_for_yoy"]},
            )
        )

    if sales >= config["min_sales_for_yoy"] and margin < config["low_margin_rate"]:
        out.append(
            anomaly(
                row=row,
                rule_id="R005",
                severity="high",
                title="毛利率过低",
                message=f"{name} 本期毛利率 {pct(margin)}，低于 {pct(config['low_margin_rate'])} 阈值，需核查折扣、成本或毛利口径。",
                metrics=_core_metrics(row),
                thresholds={
                    "low_margin_rate": config["low_margin_rate"],
                    "min_sales_for_yoy": config["min_sales_for_yoy"],
                },
            )
        )

    if (
        sales >= config["min_sales_for_yoy"]
        and prior_sales >= config["min_prior_sales_for_yoy"]
        and margin_delta_pp <= config["margin_drop_pp"]
    ):
        out.append(
            anomaly(
                row=row,
                rule_id="R006",
                severity="medium",
                title="毛利率明显下降",
                message=f"{name} 毛利率较同期变化 {pp(margin_delta_pp)}，超过下降阈值 {pp(config['margin_drop_pp'])}。",
                metrics=_core_metrics(row),
                thresholds={
                    "margin_drop_pp": config["margin_drop_pp"],
                    "min_sales_for_yoy": config["min_sales_for_yoy"],
                    "min_prior_sales_for_yoy": config["min_prior_sales_for_yoy"],
                },
            )
        )

    if sales_yoy is not None and sales_yoy > 0 and margin_delta_pp <= config["margin_drop_pp"] and sales >= config["min_sales_for_yoy"]:
        out.append(
            anomaly(
                row=row,
                rule_id="R007",
                severity="medium",
                title="销售增长但毛利率下降",
                message=f"{name} 销售同比增长 {pct(sales_yoy)}，但毛利率下降 {pp(abs(margin_delta_pp))}，需关注促销拉动后的利润质量。",
                metrics=_core_metrics(row),
                thresholds={
                    "margin_drop_pp": config["margin_drop_pp"],
                    "min_sales_for_yoy": config["min_sales_for_yoy"],
                },
            )
        )

    if sales_share >= config["high_sales_share"] and margin < config["high_sales_low_margin_rate"]:
        out.append(
            anomaly(
                row=row,
                rule_id="R008",
                severity="high",
                title="高销售低毛利",
                message=f"{name} 销售占比 {pct(sales_share)}，但毛利率仅 {pct(margin)}，低于高贡献柜组毛利阈值 {pct(config['high_sales_low_margin_rate'])}。",
                metrics=_core_metrics(row),
                thresholds={
                    "high_sales_share": config["high_sales_share"],
                    "high_sales_low_margin_rate": config["high_sales_low_margin_rate"],
                },
            )
        )

    if (
        num(row.get("same_period_ticket_count")) > 0
        and ticket_yoy is not None
        and ticket_yoy <= config["ticket_decline_rate"]
        and prior_sales >= config["min_prior_sales_for_yoy"]
    ):
        out.append(
            anomaly(
                row=row,
                rule_id="R009",
                severity="medium",
                title="小票数明显下降",
                message=f"{name} 小票数同比下降 {pct(ticket_yoy)}，需关注客流、成交笔数或开单状态变化。",
                metrics=_core_metrics(row),
                thresholds={
                    "ticket_decline_rate": config["ticket_decline_rate"],
                    "min_prior_sales_for_yoy": config["min_prior_sales_for_yoy"],
                },
            )
        )

    return out


def _core_metrics(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "effective_sales",
        "same_period_effective_sales",
        "sales_delta",
        "sales_yoy_rate",
        "net_profit",
        "same_period_net_profit",
        "ticket_margin",
        "same_period_margin",
        "margin_delta_pp",
        "ticket_count",
        "same_period_ticket_count",
        "ticket_yoy_rate",
        "sales_share",
        "decline_impact",
        "growth_contribution",
    )
    return {key: row.get(key) for key in keys}

