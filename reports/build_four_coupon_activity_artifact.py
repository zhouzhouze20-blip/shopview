"""Build the bounded Data Analytics report artifact for the four-coupon campaign."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reports.four_coupon_activity_analysis import (
    COUPON_KPI_SQL,
    CROSS_SALES_SQL,
    END_DATE,
    MEMBER_LEVEL_SQL,
    START_DATE,
    STORE_ID,
    load_frames,
    validate_frames,
)


OUTPUT = Path(__file__).with_name("七夕四券活动分析_artifact.json")


PORTFOLIO_SQL = r"""
WITH issue AS (
  SELECT COUNT(*) issue_count,COUNT(DISTINCT UPPER(TRIM(tcflvipno))) issued_members
  FROM tktcardfqlog
  WHERE TRIM(tcflmkt)='601' AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M')
    AND tcflzy='M' AND tcflstartdate::date='2026-08-14' AND tcflenddate::date='2026-08-19'
    AND tcfldate::date<='2026-08-19'
), flow AS MATERIALIZED (
  SELECT l.tcflzy,UPPER(TRIM(l.tcflvipno)) member_no,h.billno,ABS(COALESCE(l.tcflmoney,0)) amount
  FROM tktcardfqlog l JOIN salehead h
    ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid
   AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric
   AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)='601' AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M')
    AND l.tcflzy IN ('O','P') AND l.tcflstartdate::date='2026-08-14'
    AND l.tcflenddate::date='2026-08-19'
    AND l.tcfldate::date BETWEEN '2026-08-14' AND '2026-08-19'
), bills AS (SELECT DISTINCT billno FROM flow),
coupon AS (
  SELECT SUM(CASE WHEN tcflzy='O' THEN amount ELSE -amount END) net_coupon_amount,
         SUM(amount) FILTER(WHERE tcflzy='O') gross_coupon_amount,
         SUM(amount) FILTER(WHERE tcflzy='P') returned_coupon_amount,
         COUNT(DISTINCT member_no) FILTER(WHERE tcflzy='O') used_members,
         COUNT(DISTINCT billno) FILTER(WHERE tcflzy='O') use_tickets,
         COUNT(DISTINCT billno) FILTER(WHERE tcflzy='P') return_tickets
  FROM flow
), sales AS (
  SELECT SUM(COALESCE(s.sglxssr,0)) net_linked_sales,SUM(COALESCE(s.sgln2,0)) net_linked_gross_profit
  FROM bills b JOIN salegoodslist s ON s.sglbillno=b.billno
)
SELECT issue.*,coupon.*,sales.* FROM issue,coupon,sales
"""


QUALITY_SOURCE_SQL = r"""
WITH issue AS (
  SELECT * FROM tktcardfqlog
  WHERE TRIM(tcflmkt)='601' AND UPPER(TRIM(tcfljetype)) IN ('B','E','H','M') AND tcflzy='M'
    AND tcflstartdate::date='2026-08-14' AND tcflenddate::date='2026-08-19'
    AND tcfldate::date<='2026-08-19'
), flow AS (
  SELECT l.*,h.billno,h.hykh buyer_member
  FROM tktcardfqlog l JOIN salehead h
    ON h.mkt=TRIM(l.tcflmkt) AND h.syjh=l.tcflsyjid
   AND l.tcflinvno~'^[0-9]+$' AND h.fphm=l.tcflinvno::numeric
   AND h.rqsj::date=l.tcfldate::date
  WHERE TRIM(l.tcflmkt)='601' AND UPPER(TRIM(l.tcfljetype)) IN ('B','E','H','M')
    AND l.tcflzy IN ('O','P') AND l.tcflstartdate::date='2026-08-14'
    AND l.tcflenddate::date='2026-08-19'
    AND l.tcfldate::date BETWEEN '2026-08-14' AND '2026-08-19'
), use_bill AS (
  SELECT billno,COUNT(DISTINCT UPPER(TRIM(tcfljetype))) coupon_type_count
  FROM flow WHERE tcflzy='O' GROUP BY 1
)
SELECT COUNT(*) issue_count,
       COUNT(*) FILTER(WHERE tcfldate::date<'2026-08-14') prelaunch_issue_count,
       (SELECT COUNT(*) FROM use_bill WHERE coupon_type_count>1) multi_coupon_type_tickets,
       (SELECT COUNT(DISTINCT billno) FROM flow WHERE tcflzy='O' AND UPPER(TRIM(COALESCE(tcflvipno,'')))<>UPPER(TRIM(COALESCE(buyer_member,'')))) holder_buyer_mismatch_tickets
FROM issue
"""


def literal_sql(sql: str) -> str:
    return (
        sql.replace(":store_id", f"'{STORE_ID}'")
        .replace(":start_date", f"'{START_DATE}'")
        .replace(":end_date", f"'{END_DATE}'")
    )


def rows(frame: pd.DataFrame) -> list[dict]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def build() -> dict:
    frames = load_frames()
    validate_frames(frames)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    kpi = frames["coupon_kpis"].copy()
    kpi["coupon_label"] = kpi["coupon_type"] + " · " + kpi["coupon_name"]
    kpi["member_redemption_rate"] = kpi["member_redemption_rate_pct"] / 100.0
    kpi["net_sales_share"] = kpi["net_linked_sales"] / kpi["net_linked_sales"].sum()
    kpi["return_rate"] = kpi["returned_units"] / kpi["gross_used_units"]

    member = frames["member_levels"].copy()
    member["member_level"] = member["customer_level"].str.replace("卡会员", "", regex=False)
    member["member_redemption_rate"] = member["member_redemption_rate_pct"] / 100.0
    member["net_sales_share"] = member["net_linked_sales"] / member["net_linked_sales"].sum()

    brands = frames["cross_sales"].query("dimension_type == '品牌' and rank_in_coupon <= 5").copy()
    brands["coupon_label"] = brands["coupon_type"].map(
        dict(zip(kpi["coupon_type"], kpi["coupon_label"], strict=True))
    )
    brands["sales_share"] = brands["sales_share_pct"] / 100.0

    quality = frames["quality"].iloc[0]
    portfolio = pd.DataFrame(
        [
            {
                "issued_units": int(kpi["issue_count"].sum()),
                "issued_members": int(member["issued_members"].sum()),
                "used_members": int(member["used_members"].sum()),
                "member_redemption_rate": float(member["used_members"].sum() / member["issued_members"].sum()),
                "gross_used_units": int(kpi["gross_used_units"].sum()),
                "returned_units": int(kpi["returned_units"].sum()),
                "net_used_units": int(kpi["net_used_units"].sum()),
                "net_coupon_amount": float(kpi["net_coupon_amount"].sum()),
                "net_linked_sales": float(kpi["net_linked_sales"].sum()),
                "net_linked_gross_profit": float(kpi["net_linked_gross_profit"].sum()),
                "coupon_to_sales_rate": float(kpi["net_coupon_amount"].sum() / kpi["net_linked_sales"].sum()),
                "use_tickets": int(quality["use_tickets"]),
                "return_tickets": int(quality["return_tickets"]),
            }
        ]
    )

    common_filters = [
        "门店=601（常州购物中心）",
        "券种 IN (B,E,H,M)",
        "券有效期=2026-08-14至2026-08-19",
        "发券动作=M；核销/退券动作=O/P",
    ]
    sources = [
        {
            "id": "portfolio_sql",
            "label": "四券组合总额核对",
            "query": {
                "engine": "PostgreSQL",
                "language": "SQL",
                "sql": PORTFOLIO_SQL,
                "description": "按去重小票核对四券组合的发券、会员、净券金额、连带销售和毛利。",
                "executed_at": generated_at,
                "filters": common_filters,
                "tables_used": ["tktcardfqlog", "salehead", "salegoodslist"],
                "metric_definitions": [
                    "净券金额=核销金额(O)-退券金额(P)",
                    "净连带销售=四券相关去重小票的 salegoodslist.sglxssr 合计，已包含退货负数",
                    "会员使用率=发生核销(O)的唯一持券会员数/唯一获券会员数",
                ],
            },
        },
        {
            "id": "coupon_kpi_sql",
            "label": "分券种活动指标",
            "query": {
                "engine": "PostgreSQL",
                "language": "SQL",
                "sql": literal_sql(COUPON_KPI_SQL),
                "description": "计算 B/E/H/M 四券的发券、核销、退券、会员与分摊后的连带销售指标。",
                "executed_at": generated_at,
                "filters": common_filters,
                "tables_used": ["tktcardfqlog", "salehead", "salegoodslist", "fj_dw_member_dim"],
                "metric_definitions": [
                    "发券张数仅取最初发券动作 M，包含活动前预发但有效期属于本活动的券",
                    "多券同单销售按各券核销金额占比分摊；退货同口径分摊",
                    "券金额占销售=净券金额/净连带销售",
                ],
            },
        },
        {
            "id": "member_level_sql",
            "label": "持券会员等级分析",
            "query": {
                "engine": "PostgreSQL",
                "language": "SQL",
                "sql": literal_sql(MEMBER_LEVEL_SQL),
                "description": "按持券会员等级统计获券、使用、净连带销售、新会员和活动前90天活跃会员。",
                "executed_at": generated_at,
                "filters": common_filters,
                "tables_used": ["tktcardfqlog", "salehead", "salegoodslist", "fj_dw_member_dim"],
                "metric_definitions": [
                    "会员等级取 fj_dw_member_dim.customer_level",
                    "连带销售归属持券会员；当持券人与结账会员不同，以持券人为会员分析主体",
                ],
            },
        },
        {
            "id": "cross_sales_sql",
            "label": "连带品牌与品类分析",
            "query": {
                "engine": "PostgreSQL",
                "language": "SQL",
                "sql": literal_sql(CROSS_SALES_SQL),
                "description": "按券种统计多券同单分摊后的品牌、品类和部门净连带销售。",
                "executed_at": generated_at,
                "filters": common_filters + ["每券种每个维度保留销售前10名"],
                "tables_used": ["tktcardfqlog", "salehead", "salegoodslist", "codebrand", "goodscat", "manaframe"],
                "metric_definitions": ["净连带销售包含退货负数；多券同单按券金额占比分摊"],
            },
        },
        {
            "id": "quality_sql",
            "label": "活动口径与关联质量检查",
            "query": {
                "engine": "PostgreSQL",
                "language": "SQL",
                "sql": QUALITY_SOURCE_SQL,
                "description": "检查预发券、多券同单及持券人与结账会员不一致的小票。",
                "executed_at": generated_at,
                "filters": common_filters,
                "tables_used": ["tktcardfqlog", "salehead"],
                "metric_definitions": ["持券人-结账会员不一致按小票去重计数"],
            },
        },
    ]

    manifest = {
        "version": 1,
        "surface": "report",
        "title": "七夕四券活动分析",
        "description": "常州购物中心 2026年8月14日至19日 B/E/H/M 四券的核销、连带销售与会员分析。",
        "generatedAt": generated_at,
        "sources": sources,
        "cards": [
            {"id": "net_sales_card", "dataset": "portfolio", "sourceId": "portfolio_sql", "description": "四券关联去重小票销售减退货。", "metrics": [{"label": "净连带销售", "field": "net_linked_sales", "format": "currency"}]},
            {"id": "used_member_card", "dataset": "portfolio", "sourceId": "portfolio_sql", "description": "发生过核销的唯一持券会员。", "metrics": [{"label": "使用会员", "field": "used_members", "format": "number"}, {"label": "会员使用率", "field": "member_redemption_rate", "format": "percent"}]},
            {"id": "net_units_card", "dataset": "portfolio", "sourceId": "portfolio_sql", "description": "核销张数扣除退券张数。", "metrics": [{"label": "净核销券", "field": "net_used_units", "format": "number"}, {"label": "退券", "field": "returned_units", "format": "number"}]},
            {"id": "coupon_cost_card", "dataset": "portfolio", "sourceId": "portfolio_sql", "description": "核销券金额扣除退券金额；当前活动表折算收入与供应商承担均为0。", "metrics": [{"label": "净券金额", "field": "net_coupon_amount", "format": "currency"}, {"label": "占净销售", "field": "coupon_to_sales_rate", "format": "percent"}]},
        ],
        "charts": [
            {"id": "coupon_sales_chart", "title": "各券净连带销售", "subtitle": "E券贡献超过一半净连带销售，H券位居第二。", "type": "bar", "dataset": "coupon_kpis", "sourceId": "coupon_kpi_sql", "encodings": {"x": {"field": "coupon_label", "type": "nominal", "label": "券种"}, "y": {"field": "net_linked_sales", "type": "quantitative", "format": "currency", "label": "净连带销售"}}, "valueFormat": "currency", "layout": "half"},
            {"id": "coupon_redemption_chart", "title": "各券会员使用率", "subtitle": "E券使用率最高；M券仅5.1%，触达或规则需要重构。", "type": "bar", "dataset": "coupon_kpis", "sourceId": "coupon_kpi_sql", "encodings": {"x": {"field": "coupon_label", "type": "nominal", "label": "券种"}, "y": {"field": "member_redemption_rate", "type": "quantitative", "format": "percent", "label": "会员使用率"}}, "valueFormat": "percent", "layout": "half"},
            {"id": "member_level_chart", "title": "会员等级使用率", "subtitle": "会员等级越高，活动使用率与人均连带销售整体越高。", "type": "bar", "dataset": "member_levels", "sourceId": "member_level_sql", "encodings": {"x": {"field": "member_level", "type": "ordinal", "label": "会员等级"}, "y": {"field": "member_redemption_rate", "type": "quantitative", "format": "percent", "label": "会员使用率"}}, "valueFormat": "percent", "layout": "full"},
        ],
        "tables": [
            {"id": "coupon_kpi_table", "title": "四券核心指标明细", "subtitle": "销售按多券同单金额占比分摊，金额均已扣除退货。", "dataset": "coupon_kpis", "sourceId": "coupon_kpi_sql", "layout": "full", "density": "dense", "defaultSort": {"field": "net_linked_sales", "direction": "desc"}, "columns": [
                {"field": "coupon_label", "label": "券种"}, {"field": "issue_count", "label": "发券", "format": "number"}, {"field": "used_members", "label": "使用会员", "format": "number"}, {"field": "member_redemption_rate", "label": "会员使用率", "format": "percent"}, {"field": "net_used_units", "label": "净核销", "format": "number"}, {"field": "net_coupon_amount", "label": "净券金额", "format": "currency"}, {"field": "net_linked_sales", "label": "净连带销售", "format": "currency"}, {"field": "net_linked_gross_profit", "label": "净连带毛利", "format": "currency"}, {"field": "coupon_to_sales_pct", "label": "券/销售(百分点)", "format": "number"}
            ]},
            {"id": "member_level_table", "title": "会员等级表现", "dataset": "member_levels", "sourceId": "member_level_sql", "layout": "full", "density": "dense", "defaultSort": {"field": "member_redemption_rate", "direction": "desc"}, "columns": [
                {"field": "member_level", "label": "会员等级"}, {"field": "issued_members", "label": "获券会员", "format": "number"}, {"field": "used_members", "label": "使用会员", "format": "number"}, {"field": "member_redemption_rate", "label": "使用率", "format": "percent"}, {"field": "net_linked_sales", "label": "净连带销售", "format": "currency"}, {"field": "sales_per_used_member", "label": "使用会员人均销售", "format": "currency"}, {"field": "prior_90d_active_members", "label": "前90天活跃", "format": "number"}
            ]},
            {"id": "top_brand_table", "title": "各券连带销售前五品牌", "subtitle": "同券内按净连带销售排序。", "dataset": "top_brands", "sourceId": "cross_sales_sql", "layout": "full", "density": "dense", "defaultSort": {"field": "net_sales", "direction": "desc"}, "columns": [
                {"field": "coupon_type", "label": "券种"}, {"field": "dimension_name", "label": "品牌"}, {"field": "tickets", "label": "小票", "format": "number"}, {"field": "net_sales", "label": "净连带销售", "format": "currency"}, {"field": "net_gross_profit", "label": "净连带毛利", "format": "currency"}, {"field": "sales_share", "label": "券内销售占比", "format": "percent"}
            ]},
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": "# 七夕四券活动分析"},
            {"id": "executive_summary", "type": "markdown", "body": "## Executive Summary\n\n本档四券共产生 **103.02万元净连带销售**、**15.23万元净连带毛利**，净券金额 **7.16万元**，占净连带销售 **6.95%**。E券是规模主力，贡献52.3%净连带销售且会员使用率49.5%；H券客单最高、贡献40.06万元；B券覆盖较散但使用率仅28.5%；M券只有12名会员使用，现有规则和触达方式不适合作为主活动券。\n\n这份结果描述的是“关联销售”，不能直接解释为活动增量或ROI。"},
            {"id": "headline_metrics", "type": "metric-strip", "cardIds": ["net_sales_card", "used_member_card", "net_units_card", "coupon_cost_card"]},
            {"id": "definitions", "type": "markdown", "body": "## 口径定义\n\n- 活动范围：601门店、B/E/H/M券、有效期2026-08-14至2026-08-19。\n- 来源只取最初发券动作 M；后续核销 O 和退券 P 只计金额。\n- 694张券在活动开始前预发，仍按有效期归入本档活动。\n- 7张小票同时使用多种活动券，分券种销售按券金额占比分摊；组合总额按小票去重。"},
            {"id": "coupon_findings", "type": "markdown", "sourceId": "coupon_kpi_sql", "body": "## 各券表现：E负责规模，H负责高客单，M需要重构\n\n- **E券**：净连带销售53.92万元，会员使用率49.5%，是本档活动的规模引擎。\n- **H券**：净连带销售40.06万元，核销小票平均销售2696元，适合承担高客单穿着品类拉动。\n- **B券**：净连带销售8.89万元、会员使用率28.5%，应提高定向触达而非继续扩大泛发。\n- **M券**：仅12名会员使用、净连带销售1436元，使用率5.1%，建议重做领取入口、规则或受众。"},
            {"id": "coupon_sales_block", "type": "chart", "chartId": "coupon_sales_chart"},
            {"id": "coupon_redemption_block", "type": "chart", "chartId": "coupon_redemption_chart"},
            {"id": "coupon_table_block", "type": "table", "tableId": "coupon_kpi_table"},
            {"id": "member_findings", "type": "markdown", "sourceId": "member_level_sql", "body": "## 会员分层：高等级会员转化更高\n\n黑钻、黑金、金星、银星会员使用率依次为75.0%、67.1%、60.8%、48.9%，使用会员人均连带销售也由银星的1946元提升至黑金的2968元。建议E/H券优先覆盖高等级与活动前90天活跃会员；银星会员继续承担规模，但需要更精细的到期提醒和品类推荐。"},
            {"id": "member_level_chart_block", "type": "chart", "chartId": "member_level_chart"},
            {"id": "member_level_table_block", "type": "table", "tableId": "member_level_table"},
            {"id": "cross_sales_findings", "type": "markdown", "sourceId": "cross_sales_sql", "body": "## 连带销售结构\n\nE券主要被萨洛蒙、鄂尔多斯、爱步及户外/女装消费吸收；H券集中在鄂尔多斯、ASH、IRO Paris等穿着品牌；B券分布更分散。M券的连带销售几乎都在生鲜和超市，说明它与百货主活动的消费场景不同，应独立评估。"},
            {"id": "top_brand_table_block", "type": "table", "tableId": "top_brand_table"},
            {"id": "recommendations", "type": "markdown", "body": "## 建议\n\n1. **保留E券作为主力券**：预发给高等级及前90天活跃会员，并在到期前做一次定向提醒。\n2. **H券继续承担高客单穿着拉动**：围绕女装、女鞋和内衣品牌做组合推荐，同时跟踪退货后的净贡献。\n3. **B券从泛发改为场景化触达**：按女鞋、运动、童装兴趣标签定向发放，下一档以使用率35%作为观察线。\n4. **M券单独重构**：若目标是超市引流，应独立设定客流与复购指标；若目标是百货连带，应调整门槛、适用范围和入口。\n5. **修正活动归属字段**：把B/E/H/M写入真实活动ID，避免依赖有效期识别，也避免整年券或新人券混入。"},
            {"id": "further_questions", "type": "markdown", "body": "## 进一步验证\n\n- 用同店同星期、同等级未领券会员建立对照，测算真实增量销售和增量毛利。\n- 核对B/E券低于标称门槛的27张小票，确认门槛依据是应收金额、折前金额还是组合规则。\n- 持券人与结账会员不同的小票有238张，需确认代付、家庭共卡或会员识别缺失的业务原因。\n- 若要计算ROI，需补充供应商承担、折算收入及运营投放成本。"},
            {"id": "caveats", "type": "markdown", "sourceId": "quality_sql", "body": "## 口径与限制\n\n- 连带销售是核销券关联小票金额，不代表因活动新增的销售。\n- 36.1%的券在活动开始前发放；只按活动日期查发券会少算694张。\n- 当前券日志活动ID为0，报告按有效期识别；系统活动归属修正后应重新核对。\n- 238张使用小票的持券人与结账会员不一致，会员分析以持券人为主。\n- 净连带毛利取 salegoodslist.sgln2；本范围内它与现有净利字段一致，不能作为独立净利润结论。"},
        ],
    }

    snapshot = {
        "version": 1,
        "generatedAt": generated_at,
        "status": "ready",
        "datasets": {
            "portfolio": rows(portfolio),
            "coupon_kpis": rows(kpi),
            "member_levels": rows(member),
            "top_brands": rows(brands),
        },
    }
    return {"surface": "report", "manifest": manifest, "snapshot": snapshot, "sources": sources}


if __name__ == "__main__":
    artifact = build()
    OUTPUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(OUTPUT)
