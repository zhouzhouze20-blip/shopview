import { addDaysFromIso, findFinancialMonthContaining } from "./financialMonth.ts";

export type MobileSalesDatePreset = {
  label: "本日" | "昨天" | "本财务月" | "本年";
  start: string;
  end: string;
};

/** 本日用于实时查看；累计快捷区间仍截至昨天，避免把未完整入库的当天数据混入累计值。 */
export function buildMobileSalesDatePresets(todayIso: string): MobileSalesDatePreset[] {
  const yesterday = addDaysFromIso(todayIso, -1);
  const financialMonth = findFinancialMonthContaining(yesterday);
  const reportingYear = yesterday.slice(0, 4);

  return [
    { label: "本日", start: todayIso, end: todayIso },
    { label: "昨天", start: yesterday, end: yesterday },
    { label: "本财务月", start: financialMonth.start, end: yesterday },
    { label: "本年", start: `${reportingYear}-01-01`, end: yesterday },
  ];
}
