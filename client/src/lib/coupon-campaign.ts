import XLSX from "xlsx-js-style";

export type CampaignRow = Record<string, string | number | boolean | null>;
export type Campaign = {
  id: number; name: string; store_code: string; start_date: string; end_date: string;
  coupon_types: string[]; erp_activity_id: string; notes: string;
  rule_snapshot?: { fetched_at: string; rows: CampaignRow[]; source: string; basis: string; ods_batch_id?: string; source_synced_at?: string; ods_published_at?: string } | null;
};
export type CampaignFilters = {
  store_code: string; name: string; start_date: string; end_date: string;
};
export function filterCampaigns(campaigns: Campaign[], filters: CampaignFilters) {
  const name = filters.name.trim().toLocaleLowerCase("zh-CN");
  return campaigns.filter(campaign =>
    (!filters.store_code || campaign.store_code === filters.store_code)
    && (!name || campaign.name.toLocaleLowerCase("zh-CN").includes(name))
    && (!filters.start_date || campaign.start_date >= filters.start_date)
    && (!filters.end_date || campaign.end_date <= filters.end_date)
  );
}
export type CampaignSalesLift = {
  status: "estimated" | "unavailable"; reason?: string; method: string;
  baseline_weeks: number; day_count?: number; rule_batch_id?: string;
  treatment_group_count?: number; mapped_treatment_group_count?: number;
  department_count?: number; control_group_count?: number;
  actual_sales?: number; same_weekday_baseline_sales?: number; raw_change_rate?: number;
  control_actual_sales?: number; control_baseline_sales?: number; control_change_rate?: number;
  control_factor?: number; expected_sales?: number; estimated_increment?: number;
  estimated_growth_rate?: number; caveats?: string[];
  activity_start_date?: string; activity_end_date?: string;
  baseline_periods?: { week_no: number; start_date: string; end_date: string }[];
};
export type CampaignReport = {
  scope: Campaign; summary: CampaignRow; coupons: CampaignRow[]; members: CampaignRow[];
  member_levels: CampaignRow[]; brands: CampaignRow[]; tickets: CampaignRow[];
  quality: Record<string, number>; definitions: string[]; generated_at: string;
  sales_lift: CampaignSalesLift;
  ownership?: {
    status: string; status_label: string; version: number; fingerprint: string;
    storage_ready: boolean; can_confirm: boolean; candidate_assets: number; report_assets: number;
    confirmed_assets: number; unconfirmed_added: number; confirmed_missing: number;
    missing_erp_period: number; conflicting_erp_period: number; basis: string; change_basis: string;
    confirmed_at?: string; confirmed_by?: number; note: string;
  };
  member_source?: { status: string; source: string; history_basis: string; matched: number; unresolved: number; reason?: string };
  assets?: CampaignRow[]; coupon_flows?: CampaignRow[]; brand_details?: CampaignRow[];
  post_activity_returns?: {
    observed_through: string; return_tickets: number; return_sales: number; reference_net_sales: number;
    basis: string; caveat: string; details: CampaignRow[];
  };
};
export type CampaignColumn = [string, string];
export const couponColumns: CampaignColumn[] = [
  ["coupon_type", "券种"], ["source_name", "最初发券来源"], ["issued_count", "发券资产数"],
  ["preissued_count", "提前发券数"], ["issued_members", "领券人数"], ["used_members", "核销人数"],
  ["issued_amount", "发券金额"], ["redeemed_amount", "核销券金额（冲正后）"],
  ["returned_coupon_amount", "退券金额（冲正后）"], ["net_coupon_amount", "净券金额"],
  ["use_tickets", "核销销售小票数"], ["return_tickets", "关联退货小票数"],
  ["gross_linked_sales", "关联销售收入"], ["linked_return_sales", "关联退货收入（负数）"],
  ["net_linked_sales", "净连带销售"], ["net_linked_gross_profit", "净连带毛利"],
  ["average_ticket_sales", "平均单票（净连带/核销票数）"], ["mismatch_coupon_amount", "会员不一致用券金额"],
];
export const memberColumns: CampaignColumn[] = [
  ["member_no", "持券会员号"], ["member_level", "当前会员等级"], ["member_match_status", "会员主档匹配状态"],
  ["activity_member_level", "活动时等级"], ["is_new_member", "档期内注册（非首购）"], ["member_loaded_at", "会员ODS采集时间"],
  ...couponColumns.filter(([k]) => !["coupon_type", "source_name", "issued_members", "used_members"].includes(k)),
  ["own_store_net_sales", "本人本店本期净销售"],
];
export const ticketColumns: CampaignColumn[] = [
  ["billno", "小票序号"], ["original_billno", "原销售小票序号"], ["sale_date", "交易时间"],
  ["ticket_kind", "交易类型"], ["coupon_type", "券种"], ["member_no", "持券会员号"],
  ["checkout_member_no", "小票登记会员号"], ["member_match", "会员对照"],
  ["association_basis", "关联依据"],
  ["coupon_amount", "本票净核销券金额"], ["allocation", "销售分摊比例"],
  ["linked_sales", "分摊销售收入"], ["linked_gross_profit", "分摊毛利"],
];
export const ruleColumns: CampaignColumn[] = [
  ["coupon_type", "券种"], ["rule_type", "收券方式"], ["rule_mode", "设置模式"],
  ["threshold_amount", "条件金额"], ["accept_amount", "收券金额"], ["max_amount", "最大收券金额字段"],
  ["start_date", "规则开始"], ["end_date", "规则结束"], ["rule_count", "规则行数"], ["document_count", "规则单据数"],
];
export const levelColumns: CampaignColumn[] = [
  ["member_level", "当前会员等级"], ["members", "持券人数"], ["used_members", "净核销金额大于零人数"],
  ["net_linked_sales", "净连带销售"], ["own_store_net_sales", "本人本店本期净销售"],
];
export const brandColumns: CampaignColumn[] = [
  ["coupon_type", "券种"], ["brand_code", "品牌编码"],
  ["net_linked_sales", "净连带销售"], ["net_linked_gross_profit", "净连带毛利"],
];
export const assetColumns: CampaignColumn[] = [
  ["coupon_type", "券种"], ["asset_id", "券资产序号"], ["issue_id", "初始发券日志序号"], ["member_no", "持券会员号"],
  ["valid_from", "有效期开始"], ["valid_to", "有效期结束"], ["erp_period", "源日志ERP档期"],
  ["source_name", "发券来源"], ["amount", "发券金额"], ["in_report", "纳入本报告"],
];
export const flowColumns: CampaignColumn[] = [
  ["coupon_type", "券种"], ["asset_id", "券资产序号"], ["flow_id", "日志序号"], ["action", "操作码"],
  ["flow_date", "发生日期"], ["amount", "券金额绝对值"], ["billno", "关联小票序号"], ["match_count", "小票匹配数"],
];
export const brandDetailColumns: CampaignColumn[] = [
  ["billno", "小票序号"], ["original_billno", "原销售小票序号"], ["coupon_type", "券种"],
  ["brand_code", "品牌编码"], ["supplier_code", "供应商编码"], ["ticket_kind", "交易类型"],
  ["allocation", "整票销售分摊比例"], ["linked_sales", "分摊销售收入"], ["linked_gross_profit", "分摊毛利"],
];
export const postReturnColumns: CampaignColumn[] = [
  ["billno", "退货小票序号"], ["original_billno", "原销售小票序号"], ["sale_date", "退货日期"],
  ["brand_code", "品牌编码"], ["supplier_code", "供应商编码"], ["sales", "退货销售收入"], ["gross_profit", "退货毛利"],
];
export const qualityLabels: Record<string, string> = {
  member_profile_unresolved: "当前会员主档或等级未唯一匹配",
  ownership_unconfirmed: "归属未经确认或发生变化（1=是）",
  ownership_added_assets: "归属未确认的新增候选资产",
  ownership_missing_assets: "已确认但本次无法追溯的资产",
  ownership_conflicting_erp_period: "源日志指向其他ERP档期的资产",
  unmatched_use_flows: "核销/冲正日志未唯一匹配小票",
  unmatched_return_flows: "退券/冲正日志未唯一匹配小票",
  unsupported_action_flows: "存在延期、转移、作废等待人工核对操作",
  missing_sales_tickets: "已匹配核销小票缺少销售明细",
  return_without_original: "退券小票未追溯到本档原核销销售",
  unassigned_return_coupon_flows: "退券小票未纳入关联退货销售",
  missing_initial_issue_flows: "本档有效期日志缺少可确认的初始发券",
  returns_linked_by_coupon_log: "缺原小票，通过本档退券日志关联的退货票数",
};

export function buildCampaignWorkbook(report: CampaignReport) {
  const workbook = XLSX.utils.book_new();
  function sheet(name: string, rows: CampaignRow[], columns: CampaignColumn[]) {
    // Member/card identifiers stay strings. No formula interpretation of source text.
    const ws = XLSX.utils.aoa_to_sheet([columns.map(c => c[1]), ...rows.map(r => columns.map(([key]) => r[key] ?? ""))]);
    ws["!cols"] = columns.map(([key]) => ({ wch: key.includes("member") || key.includes("date") ? 24 : 20 }));
    ws["!autofilter"] = { ref: ws["!ref"] || "A1" };
    columns.forEach((_, i) => {
      const cell = ws[XLSX.utils.encode_cell({ r: 0, c: i })];
      cell.s = { font: { bold: true, color: { rgb: "FFFFFF" } }, fill: { fgColor: { rgb: "0F172A" } }, alignment: { wrapText: true } };
    });
    XLSX.utils.book_append_sheet(workbook, ws, name);
  }
  sheet("报告口径", [
    { key: "活动", value: report.scope.name }, { key: "门店", value: report.scope.store_code },
    { key: "档期", value: `${report.scope.start_date} 至 ${report.scope.end_date}` },
    { key: "券种", value: report.scope.coupon_types.join("、") },
    { key: "生成时间", value: report.generated_at },
    { key: "ERP规则快照", value: report.scope.rule_snapshot?.fetched_at || "未读取" },
    { key: "ERP规则ODS采集时间", value: report.scope.rule_snapshot?.source_synced_at || "未记录" },
    { key: "ERP规则ODS校验批次", value: report.scope.rule_snapshot?.ods_batch_id || "未记录" },
    ...(report.ownership ? [
      { key: "归属状态", value: report.ownership.status_label }, { key: "归属版本", value: report.ownership.version },
      { key: "归属确认时间", value: report.ownership.confirmed_at || "未确认" },
      { key: "归属确认人ID", value: report.ownership.confirmed_by ?? "未确认" },
      { key: "归属确认依据", value: report.ownership.note },
      { key: "归属口径", value: report.ownership.basis },
    ] : []),
    ...(report.member_source ? [{ key: "当前会员来源", value: report.member_source.source }, { key: "历史等级口径", value: report.member_source.history_basis }] : []),
    ...(report.post_activity_returns ? [
      { key: "活动后退货观察截止", value: report.post_activity_returns.observed_through },
      { key: "活动后退货金额（不改写活动期）", value: report.post_activity_returns.return_sales },
      { key: "活动后退货限制", value: report.post_activity_returns.caveat },
    ] : []),
    ...report.definitions.map(value => ({ key: "口径", value })),
    ...Object.entries(report.quality).map(([key, value]) => ({ key: qualityLabels[key] || key, value })),
  ], [["key", "项目"], ["value", "说明/数量"]]);
  sheet("四券汇总", report.coupons, couponColumns);
  sheet("会员分层", report.member_levels, levelColumns);
  sheet("会员明细", report.members, memberColumns);
  sheet("关联小票", report.tickets, ticketColumns);
  sheet("会员不一致", report.tickets.filter(r => r.member_match !== "一致"), ticketColumns);
  sheet("连带品牌", report.brands, brandColumns);
  sheet("ERP规则摘要", report.scope.rule_snapshot?.rows || [], ruleColumns);
  const lift = report.sales_lift;
  sheet("销售增长试算", lift?.status === "estimated" ? [
    { key: "状态", value: "参考估算" }, { key: "方法", value: lift.method },
    { key: "活动期日期", value: lift.activity_start_date && lift.activity_end_date ? `${lift.activity_start_date} 至 ${lift.activity_end_date}` : "未记录" },
    ...(lift.baseline_periods || []).map(period => ({ key: `历史同星期前${period.week_no}周`, value: `${period.start_date} 至 ${period.end_date}` })),
    { key: "活动天数", value: lift.day_count ?? "" }, { key: "历史同星期周数", value: lift.baseline_weeks },
    { key: "参与柜组数", value: lift.treatment_group_count ?? "" }, { key: "参与部门数", value: lift.department_count ?? "" },
    { key: "同部门对照柜组数", value: lift.control_group_count ?? "" },
    { key: "参与范围活动期净销售", value: lift.actual_sales ?? "" },
    { key: "参与范围历史同星期基准", value: lift.same_weekday_baseline_sales ?? "" },
    { key: "未经校准变化率(%)", value: lift.raw_change_rate ?? "" },
    { key: "对照范围历史基准", value: lift.control_baseline_sales ?? "" },
    { key: "对照范围活动期净销售", value: lift.control_actual_sales ?? "" },
    { key: "对照范围变化率(%)", value: lift.control_change_rate ?? "" },
    { key: "校准后预计销售", value: lift.expected_sales ?? "" },
    { key: "估算净增量", value: lift.estimated_increment ?? "" },
    { key: "估算增长率(%)", value: lift.estimated_growth_rate ?? "" },
    ...(lift.caveats || []).map(value => ({ key: "限制", value })),
  ] : [{ key: "状态", value: "暂不可计算" }, { key: "原因", value: lift?.reason || "未返回试算结果" }], [["key", "项目"], ["value", "数值/说明"]]);
  if (report.assets) sheet("券资产归属", report.assets, assetColumns);
  if (report.coupon_flows) sheet("活动期券流水", report.coupon_flows, flowColumns);
  if (report.brand_details) sheet("品牌供应商明细", report.brand_details, brandDetailColumns);
  if (report.post_activity_returns) sheet("活动后退货", report.post_activity_returns.details, postReturnColumns);
  return workbook;
}

export function exportCampaignWorkbook(report: CampaignReport) {
  const safeName = report.scope.name.replace(/[\\/:*?"<>|]/g, "_");
  XLSX.writeFile(buildCampaignWorkbook(report), `${safeName}_${report.scope.store_code}_活动分析.xlsx`);
}
