import { addDaysFromIso, findFinancialMonthContaining } from "./financialMonth.ts";

export type MobileSalesDatePreset = {
  label: "本日" | "昨天" | "本财务月" | "本年";
  start: string;
  end: string;
};

/** 本财务月用于实时查看并包含当天；本年仍截至昨天，避免改变原有年度累计口径。 */
export function buildMobileSalesDatePresets(todayIso: string): MobileSalesDatePreset[] {
  const yesterday = addDaysFromIso(todayIso, -1);
  const financialMonth = findFinancialMonthContaining(todayIso);
  const reportingYear = yesterday.slice(0, 4);

  return [
    { label: "本日", start: todayIso, end: todayIso },
    { label: "昨天", start: yesterday, end: yesterday },
    { label: "本财务月", start: financialMonth.start, end: todayIso },
    { label: "本年", start: `${reportingYear}-01-01`, end: yesterday },
  ];
}
