import {
  findFinancialMonthContaining,
  getFinancialMonthWindow,
  minIsoDate,
} from "./financialMonth.ts";

export type MobileRevenueDatePreset = {
  label: "本财务月" | "上个财务月" | "本年";
  start: string;
  end: string;
};

export function buildMobileRevenueDatePresets(todayIso: string): MobileRevenueDatePreset[] {
  const currentFinancialMonth = findFinancialMonthContaining(todayIso);
  const previousFinancialMonth =
    currentFinancialMonth.index === 1
      ? getFinancialMonthWindow(currentFinancialMonth.year - 1, 12)
      : getFinancialMonthWindow(currentFinancialMonth.year, currentFinancialMonth.index - 1);

  return [
    {
      label: "本财务月",
      start: currentFinancialMonth.start,
      end: minIsoDate(todayIso, currentFinancialMonth.end),
    },
    {
      label: "上个财务月",
      start: previousFinancialMonth.start,
      end: previousFinancialMonth.end,
    },
    {
      label: "本年",
      start: `${todayIso.slice(0, 4)}-01-01`,
      end: todayIso,
    },
  ];
}
