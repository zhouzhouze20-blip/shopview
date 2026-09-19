export type AuditUsageTrendGranularity = "month" | "year";

export type AuditUsageDimension = "trend" | "person" | "module";

export function buildAuditUsageTrendUrl(
  granularity: AuditUsageTrendGranularity,
  period: string,
  dimension: AuditUsageDimension = "trend",
): string {
  const query = new URLSearchParams({ granularity, period });
  if (dimension !== "trend") query.set("dimension", dimension);
  return `/api/system/audit-statistics/trend?${query.toString()}`;
}
