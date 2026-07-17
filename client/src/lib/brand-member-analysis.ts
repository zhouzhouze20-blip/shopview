export interface BrandMemberGroupOption {
  group_code: string;
  group_name: string;
  department_code: string | null;
  department_name: string | null;
  target_selectable: boolean;
}

export interface BrandMemberSegment {
  code: "brand_returning" | "same_department_inflow" | "cross_department_inflow" | "external_new";
  label: string;
  buyer_count: number;
  sales_revenue: number;
  ticket_count: number;
  buyer_share: number | null;
  sales_share: number | null;
}

export interface BrandMemberSummary {
  sales_revenue: number;
  positive_revenue: number;
  refund_revenue: number;
  ticket_count: number;
  member_buyer_count: number;
  member_sales_revenue: number;
  member_ticket_count: number;
  nonmember_sales_revenue: number;
  refund_only_member_sales_revenue: number;
  spend_per_buyer: number;
  purchase_frequency: number;
  department_rank: number | null;
  department_group_count: number;
  old_customer_repurchase_rate: number;
}

export interface BrandMemberFunnel {
  historical_target_member_count: number;
  store_visit_count: number;
  department_visit_count: number;
  target_repurchase_count: number;
}

export interface BrandMemberInflowSource {
  segment_code: string;
  group_code: string;
  group_name: string;
  department_name: string | null;
  buyer_count: number;
  historical_sales: number;
}

export interface BrandMemberLevelConsumption {
  level_code: "01" | "02" | "03" | "04" | "UNIDENTIFIED";
  level_label: string;
  buyer_count: number;
  sales_revenue: number;
  ticket_count: number;
  buyer_share: number | null;
  sales_share: number | null;
  spend_per_buyer: number;
  purchase_frequency: number;
  average_ticket_value: number;
}

export interface BrandMemberPeriod {
  period: { start_date: string; end_date: string };
  summary: BrandMemberSummary;
  segments: BrandMemberSegment[];
  member_level_consumption: BrandMemberLevelConsumption[];
  old_customer_funnel: BrandMemberFunnel;
  inflow_sources: BrandMemberInflowSource[];
}

export interface BrandMemberCompetitor {
  group_code: string;
  group_name: string;
  department_name: string | null;
  current: Pick<BrandMemberSummary, "sales_revenue" | "ticket_count" | "member_buyer_count" | "member_sales_revenue" | "spend_per_buyer" | "purchase_frequency">;
  prior: Pick<BrandMemberSummary, "sales_revenue" | "ticket_count" | "member_buyer_count" | "member_sales_revenue" | "spend_per_buyer" | "purchase_frequency">;
}

export interface MetricComparison {
  current: number;
  prior: number;
  change: number;
  change_rate: number | null;
}

export interface BrandMemberReport {
  scope: {
    store_code: string;
    target_group_code: string;
    competitor_group_codes: string[];
  };
  target: {
    group_code: string;
    group_name: string;
    department_code: string;
    department_name: string;
    current: BrandMemberPeriod;
    prior: BrandMemberPeriod;
  };
  comparison: Record<string, MetricComparison>;
  competitors: BrandMemberCompetitor[];
  definitions: Record<string, string>;
}

export interface BrandMemberFilters {
  storeCode: string;
  targetGroupCode: string;
  competitorGroupCodes: string[];
  currentStart: string;
  currentEnd: string;
  priorStart: string;
  priorEnd: string;
}

export function brandMemberAiFallbackMessage(status: string) {
  switch (status) {
    case "guardrail_rejected":
      return "AI结论未通过数据校验，当前展示规则结论。";
    case "not_configured":
      return "AI服务尚未配置，当前展示规则结论。";
    case "empty":
      return "AI未返回有效结论，当前展示规则结论。";
    case "truncated":
      return "AI返回内容不完整，当前展示规则结论。";
    default:
      return "AI服务暂不可用，当前展示规则结论。";
  }
}

export function filterBrandMemberGroups(groups: BrandMemberGroupOption[], query: string) {
  const keywords = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (!keywords.length) return groups;

  return groups.filter((group) => {
    const searchableText = [
      group.group_name,
      group.group_code,
      group.department_name || "",
      group.department_code || "",
    ].join(" ").toLocaleLowerCase();
    return keywords.every((keyword) => searchableText.includes(keyword));
  });
}

const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export function defaultBrandMemberDates(now = new Date()): Pick<BrandMemberFilters, "currentStart" | "currentEnd" | "priorStart" | "priorEnd"> {
  const currentStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const currentEnd = new Date(now.getFullYear(), now.getMonth(), 0);
  const priorStart = new Date(currentStart.getFullYear() - 1, currentStart.getMonth(), currentStart.getDate());
  const priorEnd = new Date(currentEnd.getFullYear() - 1, currentEnd.getMonth(), currentEnd.getDate());
  return {
    currentStart: isoDate(currentStart),
    currentEnd: isoDate(currentEnd),
    priorStart: isoDate(priorStart),
    priorEnd: isoDate(priorEnd),
  };
}

export function priorYearPeriod(start: string, end: string) {
  const shift = (value: string) => {
    const [year, month, day] = value.split("-").map(Number);
    const candidate = new Date(year - 1, month - 1, day);
    if (candidate.getMonth() !== month - 1) return isoDate(new Date(year - 1, month, 0));
    return isoDate(candidate);
  };
  return { priorStart: shift(start), priorEnd: shift(end) };
}

export function previousPeriod(start: string, end: string) {
  const parse = (value: string) => {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  };
  const startDate = parse(start);
  const endDate = parse(end);
  const durationDays = Math.round((endDate.getTime() - startDate.getTime()) / 86_400_000) + 1;
  const priorEnd = new Date(startDate);
  priorEnd.setDate(priorEnd.getDate() - 1);
  const priorStart = new Date(priorEnd);
  priorStart.setDate(priorStart.getDate() - durationDays + 1);
  return { priorStart: isoDate(priorStart), priorEnd: isoDate(priorEnd) };
}

export function brandMemberRequest(filters: BrandMemberFilters) {
  return {
    store_code: filters.storeCode,
    target_group_code: filters.targetGroupCode,
    competitor_group_codes: filters.competitorGroupCodes,
    current_start: filters.currentStart,
    current_end: filters.currentEnd,
    prior_start: filters.priorStart,
    prior_end: filters.priorEnd,
  };
}

export function buildAiSnapshot(report: BrandMemberReport) {
  return {
    target: report.target,
    comparison: report.comparison,
    competitors: report.competitors,
    definitions: report.definitions,
  };
}

export function formatBrandMoney(value: number) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

export function formatBrandNumber(value: number, maximumFractionDigits = 0) {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits }).format(Number(value || 0));
}

export function formatBrandPercent(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

export function formatBrandShare(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}
