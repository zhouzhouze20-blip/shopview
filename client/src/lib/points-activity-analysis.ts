export type PointStatus =
  | "OK"
  | "POINT_DIFF"
  | "MISSING_RATE"
  | "ZERO_RATE"
  | "ALLOCATION_IMBALANCE";

export const DEPARTMENT_SCOPE_ALL_VALUE = "__scope_all_departments__";
export const DEPARTMENT_SCOPE_ALL_LABEL = "权限内全部部门";
export const POINTS_ACTIVITY_START_DATE = "2026-07-09";

export function pointsActivityDefaultEndDate(today: string) {
  return today < POINTS_ACTIVITY_START_DATE ? POINTS_ACTIVITY_START_DATE : today;
}

export function clampPointsActivityEndDate(startDate: string, candidateEndDate: string) {
  return candidateEndDate < startDate ? startDate : candidateEndDate;
}

export function pointStatusLabel(status?: string | null) {
  switch ((status || "").toUpperCase()) {
    case "OK":
      return "正常";
    case "POINT_DIFF":
      return "积分差异";
    case "MISSING_RATE":
      return "缺积分倍率";
    case "ZERO_RATE":
      return "积分率为0";
    case "ALLOCATION_IMBALANCE":
      return "付款分摊不平";
    default:
      return "待复核";
  }
}

export function pointStatusTone(status?: string | null) {
  switch ((status || "").toUpperCase()) {
    case "OK":
      return "success";
    case "POINT_DIFF":
    case "ZERO_RATE":
      return "danger";
    case "MISSING_RATE":
    case "ALLOCATION_IMBALANCE":
      return "warning";
    default:
      return "muted";
  }
}

export type PointAnalysisQueryState = {
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
  error?: unknown;
  data?: {
    departments?: unknown[];
    groups?: unknown[];
    members?: unknown[];
    tickets?: unknown[];
  };
};

export function pointAnalysisQueryMessage(state: PointAnalysisQueryState) {
  if (state.isLoading || state.isFetching) {
    return "正在加载中心年中庆活动数据...";
  }
  if (state.isError) {
    const errorText = state.error instanceof Error ? state.error.message : String(state.error ?? "");
    if (/(?:^|\D)403(?:\D|$)/.test(errorText)) {
      return "无中心年中庆活动查看权限";
    }
    if (/(?:^|\D)504(?:\D|$)|timeout|timed out|超时/i.test(errorText)) {
      return "中心年中庆活动数据查询超时，请缩短日期范围后重试";
    }
    return "中心年中庆活动数据加载失败，请稍后重试或检查后端服务";
  }
  if (
    state.data &&
    [state.data.departments, state.data.groups, state.data.members, state.data.tickets].every(
      (items) => Array.isArray(items) && items.length === 0,
    )
  ) {
    return "当前日期和权限范围内暂无数据";
  }
  return null;
}

export function memberLevelLabel(level?: string | number | null) {
  switch (String(level ?? "").trim()) {
    case "01":
      return "银星";
    case "02":
      return "金星";
    case "03":
      return "黑金";
    case "04":
      return "黑钻";
    default:
      return "未标识";
  }
}

export function memberLevelSearchKeyword(keyword: string) {
  switch (keyword.trim()) {
    case "银星":
      return "01";
    case "金星":
      return "02";
    case "黑金":
      return "03";
    case "黑钻":
      return "04";
    default:
      return keyword;
  }
}

export function salesSharePercent(value: unknown, total: unknown) {
  const numerator = Number(value || 0);
  const denominator = Number(total || 0);
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) return "0.0%";
  return `${((numerator / denominator) * 100).toFixed(1)}%`;
}

export function pointTicketTimeLabel(value?: string | null) {
  const text = String(value || "").trim();
  if (!text) return "-";
  const normalized = text.replace("T", " ");
  return normalized.length >= 19 ? normalized.slice(0, 19) : normalized;
}
