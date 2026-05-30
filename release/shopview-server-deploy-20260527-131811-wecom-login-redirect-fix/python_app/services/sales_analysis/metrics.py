from __future__ import annotations

from typing import Any


def num(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rate(delta: float, base: float) -> float | None:
    if base <= 0:
        return None
    return delta / base


def enrich_group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_sales = sum(num(row.get("effective_sales")) for row in rows)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        effective_sales = num(row.get("effective_sales"))
        prior_sales = num(row.get("same_period_effective_sales"))
        net_profit = num(row.get("net_profit"))
        prior_net_profit = num(row.get("same_period_net_profit"))
        ticket_count = num(row.get("ticket_count"))
        prior_ticket_count = num(row.get("same_period_ticket_count"))
        ticket_margin = num(row.get("ticket_margin"))
        same_period_margin = num(row.get("same_period_margin"))

        sales_delta = effective_sales - prior_sales
        profit_delta = net_profit - prior_net_profit
        ticket_delta = ticket_count - prior_ticket_count

        item = dict(row)
        item.update(
            {
                "effective_sales": effective_sales,
                "same_period_effective_sales": prior_sales,
                "net_profit": net_profit,
                "same_period_net_profit": prior_net_profit,
                "ticket_count": ticket_count,
                "same_period_ticket_count": prior_ticket_count,
                "ticket_margin": ticket_margin,
                "same_period_margin": same_period_margin,
                "sales_delta": sales_delta,
                "sales_yoy_rate": rate(sales_delta, prior_sales),
                "profit_delta": profit_delta,
                "margin_delta_pp": (ticket_margin - same_period_margin) * 100,
                "ticket_delta": ticket_delta,
                "ticket_yoy_rate": rate(ticket_delta, prior_ticket_count),
                "sales_share": (effective_sales / total_sales) if total_sales > 0 else 0.0,
                "decline_impact": max(0.0, prior_sales - effective_sales),
                "growth_contribution": max(0.0, effective_sales - prior_sales),
            }
        )
        enriched.append(item)
    return enriched


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sales = sum(num(row.get("effective_sales")) for row in rows)
    prior_sales = sum(num(row.get("same_period_effective_sales")) for row in rows)
    net_profit = sum(num(row.get("net_profit")) for row in rows)
    prior_net_profit = sum(num(row.get("same_period_net_profit")) for row in rows)
    ticket_count = sum(num(row.get("ticket_count")) for row in rows)
    prior_ticket_count = sum(num(row.get("same_period_ticket_count")) for row in rows)
    sales_delta = sales - prior_sales
    profit_delta = net_profit - prior_net_profit

    return {
        "group_count": len(rows),
        "active_group_count": sum(1 for row in rows if num(row.get("effective_sales")) > 0),
        "prior_active_group_count": sum(1 for row in rows if num(row.get("same_period_effective_sales")) > 0),
        "sales": sales,
        "prior_sales": prior_sales,
        "sales_delta": sales_delta,
        "sales_yoy_rate": rate(sales_delta, prior_sales),
        "net_profit": net_profit,
        "prior_net_profit": prior_net_profit,
        "profit_delta": profit_delta,
        "profit_yoy_rate": rate(profit_delta, prior_net_profit),
        "margin": (net_profit / sales) if sales > 0 else 0.0,
        "prior_margin": (prior_net_profit / prior_sales) if prior_sales > 0 else 0.0,
        "ticket_count": ticket_count,
        "prior_ticket_count": prior_ticket_count,
        "ticket_delta": ticket_count - prior_ticket_count,
        "ticket_yoy_rate": rate(ticket_count - prior_ticket_count, prior_ticket_count),
    }

