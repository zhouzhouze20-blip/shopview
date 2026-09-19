export const LIVE_COUPON_TYPES = ["J", "D", "R", "E", "B", "H", "G"] as const;

export type LiveRow = Record<string, string | number | null | string[]>;
export type LiveReport = {
  status: "ready" | "choose_period" | "no_period";
  tracking_start: string; today: string; valid_to?: string; observed_end?: string;
  query_start?: string; query_end?: string;
  generated_at?: string; latest_visible_sale?: string; latest_visible_coupon_date?: string;
  periods: { valid_from: string; valid_to: string }[];
  scope?: { mode: "full_store" | "business_scope"; store_code: string; label: string };
  coupons?: LiveRow[]; daily?: LiveRow[]; departments?: LiveRow[]; groups?: LiveRow[]; tickets?: LiveRow[]; trajectory?: LiveRow[];
  holders?: LiveRow[]; trajectory_available?: boolean;
  member_trajectory?: LiveRow[]; member_period_available?: boolean;
  quality?: { unmatched_flow_count: number; missing_issue_flow_count: number; missing_sales_flow_count: number };
  distinct_used_members?: number; distinct_use_tickets?: number;
};
export type LiveColumn = [string, string];
export type LiveQueryRange = { start: string; end: string };

export function couponLiveQueryUrl(validTo: string, range: LiveQueryRange | null): string {
  const params = new URLSearchParams();
  if (validTo) params.set("valid_to", validTo);
  if (range) {
    params.set("start_date", range.start);
    params.set("end_date", range.end);
  }
  return `/api/activity-analysis/coupon-live${params.size ? `?${params}` : ""}`;
}

export function validateLiveQueryRange(range: LiveQueryRange, min: string, max: string): string {
  if (!range.start || !range.end) return "请选择查询开始和结束日期";
  if (range.start > range.end) return "查询开始日期不能晚于结束日期";
  if (range.start < min || range.end > max) return `查询日期须在 ${min} 至 ${max} 之间`;
  return "";
}

export function shanghaiToday(): string {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const value = (type: string) => parts.find(part => part.type === type)?.value;
  return `${value("year")}-${value("month")}-${value("day")}`;
}
export const couponColumns: LiveColumn[] = [
  ["coupon_type", "券种"], ["issued_count", "本档发券资产数"], ["preissued_count", "其中提前发券"],
  ["issued_amount", "本档发券金额"], ["used_assets", "已使用资产数"], ["used_members", "用券人数"],
  ["use_tickets", "核销小票数"], ["redeemed_amount", "核销券额"], ["refunded_amount", "退券额"],
  ["net_coupon_amount", "净用券额"], ["linked_sales", "净连带销售"], ["linked_returns", "关联退货（负数）"],
  ["linked_gross_profit", "净连带毛利"],
];
export const departmentColumns: LiveColumn[] = [
  ["department", "部门"], ["coupon_type", "券种"], ["redeemed_amount", "分摊核销券额"],
  ["refunded_amount", "分摊退券额"], ["linked_sales", "净连带销售"], ["linked_returns", "关联退货（负数）"],
  ["linked_gross_profit", "净连带毛利"],
];
export const groupColumns: LiveColumn[] = [
  ["group_code", "柜组编码"], ["group_name", "柜组"],
  ...departmentColumns.filter(([key]) => key !== "department" && key !== "coupon_type"),
];
export const ticketColumns: LiveColumn[] = [
  ["sale_time", "销售时间"], ["coupon_type", "券种"], ["ticket_kind", "类型"], ["billno", "小票序号"],
  ["original_billno", "原小票序号"], ["holder_member_no", "持券会员卡"], ["checkout_member_no", "购物会员卡"],
  ["department", "部门"], ["group_name", "柜组"], ["brand_name", "品牌"],
  ["sales", "分摊销售收入"], ["gross_profit", "分摊毛利"],
];
export const trajectoryColumns: LiveColumn[] = [
  ["holder_member_no", "持券会员卡"], ["sale_time", "今日消费时间"], ["event_type", "会员关系"],
  ["coupon_types", "本票使用跟踪券"], ["billno", "小票序号"], ["checkout_member_no", "购物会员卡"],
  ["department", "部门"], ["group_name", "柜组"], ["brand_name", "品牌"],
  ["sales", "本范围销售收入"], ["gross_profit", "本范围毛利"],
];

export function filterTrajectory(rows: LiveRow[], coupon: string, member: string): LiveRow[] {
  return rows.filter(row => (coupon === "all" || (Array.isArray(row.used_coupon_types) && row.used_coupon_types.includes(coupon)))
    && (!member.trim() || String(row.holder_member_no || "").includes(member.trim())));
}

// Filter only the rows already authorized by the server; never expand scope.
export function filterCouponDepartments(rows: LiveRow[], coupon: string | null): LiveRow[] {
  return coupon ? rows.filter(row => row.coupon_type === coupon) : [];
}

export type LiveDepartment = { code: string; name: string };
export function filterCouponGroups(rows: LiveRow[], coupon: string | null, department: LiveDepartment | null): LiveRow[] {
  if (!coupon || !department) return [];
  return rows.filter(row => row.coupon_type === coupon
    && String(row.department_code || "") === department.code
    && String(row.department || "") === department.name);
}

export type HolderDetailMode = "other" | "own" | "related" | "all";
export const holderDetailLabels: Record<HolderDetailMode, string> = {
  other: "其他本人消费", own: "全部本人消费", related: "购物会员不同或未登记", all: "全部期间轨迹",
};
export const holderColumns: LiveColumn[] = [
  ["holder_member_no", "持券会员卡"], ["used_coupon_types", "所选期间用券"],
  ["period_own_sales", "所选期间本人合计销售（元）"], ["period_other_sales", "其中其他消费净额（元）"],
  ["period_own_returns", "本人退货（负数，已计入合计）"], ["period_sale_tickets", "本人销售小票数"],
  ["period_return_tickets", "本人退货小票数"], ["period_related_sales", "购物会员不同或未登记关联净额（元）"],
];
export const holderDetailColumns: LiveColumn[] = [
  ["holder_member_no", "持券会员卡"], ["sale_time", "交易时间"], ["ticket_kind", "销售/退货"],
  ["billno", "小票序号"], ["original_billno", "原小票序号"], ["checkout_member_no", "购物会员卡"],
  ["event_type", "会员关系"], ["consumption_type", "消费分类"], ["ticket_coupon_types", "本票/原单跟踪券"],
  ["department", "部门"], ["group_code", "柜组编码"], ["group_name", "柜组"], ["brand_name", "品牌"],
  ["sales", "本范围销售收入（元）"], ["gross_profit", "本范围毛利（元）"],
];

function isOwnShopping(row: LiveRow): boolean {
  return Boolean(row.holder_member_no) && row.holder_member_no === row.checkout_member_no;
}
function usesSelectedCoupon(row: LiveRow, coupon: string): boolean {
  const types = Array.isArray(row.ticket_coupon_types) ? row.ticket_coupon_types : [];
  return coupon === "all" ? types.length > 0 : types.includes(coupon);
}

// The API grain is one holder + receipt + group + brand + supplier, not one coupon.
// Dedupe only at that grain; a receipt can legitimately contain multiple merchandise groups.
function uniqueHolderLines(rows: LiveRow[]): LiveRow[] {
  const seen = new Set<string>();
  return rows.filter(row => {
    const key = JSON.stringify([row.holder_member_no, row.billno, row.group_code, row.brand_code, row.supplier_code]);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function hasMemberPeriodData(report: LiveReport): boolean {
  return report.member_period_available === true && Array.isArray(report.holders)
    && Array.isArray(report.member_trajectory) && Boolean(report.query_start && report.query_end);
}

export function holderPeriodDetails(report: LiveReport, coupon: string, member: string,
  selectedHolder: string | null = null, mode: HolderDetailMode = "all"): LiveRow[] {
  if (!hasMemberPeriodData(report)) return [];
  const allowed = new Set(filterTrajectory(report.holders || [], coupon, member).map(row => row.holder_member_no));
  return uniqueHolderLines(report.member_trajectory || []).filter(row => allowed.has(row.holder_member_no)
    && (!selectedHolder || row.holder_member_no === selectedHolder)
    && String(row.sale_time || "").slice(0, 10) >= report.query_start!
    && String(row.sale_time || "").slice(0, 10) <= report.query_end!
    && (mode === "all" || (mode === "related" ? !isOwnShopping(row)
      : isOwnShopping(row) && (mode === "own" || !usesSelectedCoupon(row, coupon)))))
    .map(row => ({ ...row, consumption_type: !isOwnShopping(row) ? "购物会员不同或未登记"
      : usesSelectedCoupon(row, coupon) ? "所选券关联本人消费" : "其他本人消费" }));
}

export function summarizeHolderPeriod(report: LiveReport, coupon: string, member: string): LiveRow[] {
  if (!hasMemberPeriodData(report)) return [];
  const details = holderPeriodDetails(report, coupon, member);
  const byMember = new Map<string, LiveRow[]>();
  for (const row of details) {
    const key = String(row.holder_member_no);
    const rows = byMember.get(key) || [];
    rows.push(row);
    byMember.set(key, rows);
  }
  const cents = (rows: LiveRow[]) => rows.reduce((sum, row) => sum + Math.round(Number(row.sales || 0) * 100), 0) / 100;
  const tickets = (rows: LiveRow[], kind: string) => new Set(rows.filter(row => row.ticket_kind === kind).map(row => row.billno)).size;
  return filterTrajectory(report.holders || [], coupon, member).map(holder => {
    const rows = byMember.get(String(holder.holder_member_no)) || [];
    const own = rows.filter(isOwnShopping);
    return { ...holder, holder_member_no: String(holder.holder_member_no), period_own_sales: cents(own),
      period_other_sales: cents(own.filter(row => !usesSelectedCoupon(row, coupon))),
      period_own_returns: cents(own.filter(row => row.ticket_kind === "退货")),
      period_sale_tickets: tickets(own, "销售"), period_return_tickets: tickets(own, "退货"),
      period_related_sales: cents(rows.filter(row => !isOwnShopping(row))),
    };
  }).sort((a, b) => b.period_own_sales - a.period_own_sales || String(a.holder_member_no).localeCompare(String(b.holder_member_no)));
}
