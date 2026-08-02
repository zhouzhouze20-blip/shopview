export type SalesBrowseJourneyLog = {
  id: number;
  user_id?: number | null;
  username?: string | null;
  real_name?: string | null;
  action_code: string;
  resource_code: string;
  detail?: Record<string, unknown> | null;
  created_at: string;
};

export type SalesBrowseJourneyStep = {
  logId: number;
  time: string;
  kind: "store" | "department" | "group" | "ticket" | "return" | "list";
  label: string;
  value?: string;
};

export type SalesBrowseJourney = {
  key: string;
  userName: string;
  startedAt: string;
  endedAt: string;
  steps: SalesBrowseJourneyStep[];
};

const SESSION_GAP_MS = 30 * 60 * 1000;

function conditionsOf(log: SalesBrowseJourneyLog): Record<string, unknown> {
  const conditions = log.detail?.query_conditions;
  return conditions && typeof conditions === "object" && !Array.isArray(conditions)
    ? conditions as Record<string, unknown>
    : {};
}

function clean(value: unknown): string {
  return value === null || value === undefined ? "" : String(value).trim();
}

function placeValue(conditions: Record<string, unknown>, nameKey: string, codeKey: string): string {
  return clean(conditions[nameKey]) || clean(conditions[codeKey]);
}

function stepFromLog(log: SalesBrowseJourneyLog): SalesBrowseJourneyStep | null {
  if (log.resource_code !== "mobile-sales-dashboard" || log.action_code !== "query") return null;
  const conditions = conditionsOf(log);
  if (clean(conditions.query_type) !== "sales") return null;

  const time = log.created_at;
  const level = clean(conditions.query_level);
  const navigationAction = clean(conditions.navigation_action);

  if (navigationAction === "back") {
    const targetLevel = clean(conditions.to_level) || level;
    if (targetLevel === "departments") {
      return {
        logId: log.id,
        time,
        kind: "return",
        label: "返回部门列表",
        value: placeValue(conditions, "store_name", "store_id") || undefined,
      };
    }
    if (targetLevel === "groups") {
      return {
        logId: log.id,
        time,
        kind: "return",
        label: "返回柜组列表",
        value: placeValue(conditions, "department_name", "department_code") || undefined,
      };
    }
    if (targetLevel === "department-products") {
      return {
        logId: log.id,
        time,
        kind: "return",
        label: "返回商品列表",
        value: placeValue(conditions, "department_name", "department_code") || undefined,
      };
    }
    if (targetLevel === "stores") {
      return { logId: log.id, time, kind: "return", label: "返回门店列表" };
    }
  }

  if (level === "departments") {
    const value = placeValue(conditions, "store_name", "store_id");
    return value ? { logId: log.id, time, kind: "store", label: "门店", value } : null;
  }
  if (level === "groups") {
    const value = placeValue(conditions, "department_name", "department_code");
    return value ? { logId: log.id, time, kind: "department", label: "部门", value } : null;
  }
  if (level === "tickets" || level === "goods") {
    const value = placeValue(conditions, "group_name", "group_code");
    return value ? { logId: log.id, time, kind: "group", label: "柜组", value } : null;
  }
  if (level === "detail") {
    const value = clean(conditions.ticket_no) || clean(conditions.bill_no);
    return value ? { logId: log.id, time, kind: "ticket", label: "小票", value } : null;
  }
  if (level === "stores") {
    return { logId: log.id, time, kind: "list", label: "查看门店列表" };
  }
  return null;
}

function userKey(log: SalesBrowseJourneyLog): string {
  return log.user_id != null ? `id:${log.user_id}` : `name:${log.real_name || log.username || "unknown"}`;
}

export function buildSalesBrowseJourneys(logs: SalesBrowseJourneyLog[]): SalesBrowseJourney[] {
  const ordered = [...logs]
    .filter((log) => stepFromLog(log) !== null)
    .sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime());

  const sessions = new Map<string, Array<{ logs: SalesBrowseJourneyLog[]; lastAt: number }>>();
  for (const log of ordered) {
    const key = userKey(log);
    const userSessions = sessions.get(key) ?? [];
    const at = new Date(log.created_at).getTime();
    const current = userSessions[userSessions.length - 1];
    if (!current || !Number.isFinite(at) || at - current.lastAt > SESSION_GAP_MS) {
      userSessions.push({ logs: [log], lastAt: at });
    } else {
      current.logs.push(log);
      current.lastAt = at;
    }
    sessions.set(key, userSessions);
  }

  return Array.from(sessions.entries())
    .flatMap(([key, userSessions]) => userSessions.map((session, index) => {
      const first = session.logs[0];
      const last = session.logs[session.logs.length - 1];
      return {
        key: `${key}:${index}:${first.id}`,
        userName: first.real_name || first.username || "未知用户",
        startedAt: first.created_at,
        endedAt: last.created_at,
        steps: session.logs.map(stepFromLog).filter((step): step is SalesBrowseJourneyStep => step !== null),
      };
    }))
    .filter((journey) => journey.steps.some((step) => step.kind !== "list"))
    .sort((left, right) => new Date(right.endedAt).getTime() - new Date(left.endedAt).getTime());
}
