/** 浏览器本地日历「今天」的 ISO 日期 YYYY-MM-DD */
export function localDateFromToday(): string {
  const now = new Date();
  const t = now.getTime() - now.getTimezoneOffset() * 60000;
  return new Date(t).toISOString().slice(0, 10);
}

/**
 * 财务月划分（与百货财务口径一致）：
 * - 第1期：1.1～1.28
 * - 第2期：1.29～2.28
 * - 第3期：闰年为 2.29～3.28；非闰年为 3.1～3.28
 * - 第4～11期：上月29日～当月28日（如 3.29～4.28 … 10.29～11.28）
 * - 第12期：11.29～12.31
 */

export type FinancialMonthWindow = {
  year: number;
  /** 1～12 */
  index: number;
  start: string;
  end: string;
};

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

/** 指定公历年、财务月序号（1～12）对应的起止日期（闭区间，ISO YYYY-MM-DD） */
export function getFinancialMonthWindow(year: number, index: number): FinancialMonthWindow {
  if (index < 1 || index > 12) {
    throw new Error(`financial month index out of range: ${index}`);
  }
  const y = year;
  const leap = isLeapYear(year);

  if (index === 1) {
    return { year, index, start: `${y}-01-01`, end: `${y}-01-28` };
  }
  if (index === 2) {
    return { year, index, start: `${y}-01-29`, end: `${y}-02-28` };
  }
  if (index === 3) {
    if (leap) {
      return { year, index, start: `${y}-02-29`, end: `${y}-03-28` };
    }
    return { year, index, start: `${y}-03-01`, end: `${y}-03-28` };
  }
  if (index === 12) {
    return { year, index, start: `${y}-11-29`, end: `${y}-12-31` };
  }

  // index 4～11：上月29日～当月28日（index 4 => 3月29～4月28）
  const endMonth = index; // FM4 -> April(4) 28 ... FM11 -> November(11) 28
  const startMonth = index - 1; // FM4 -> March(3) 29
  return {
    year,
    index,
    start: `${y}-${pad2(startMonth)}-29`,
    end: `${y}-${pad2(endMonth)}-28`,
  };
}

/** ISO 日期字符串比较用（YYYY-MM-DD） */
export function minIsoDate(a: string, b: string): string {
  return a <= b ? a : b;
}

/** start 到 end 包含两端的天数偏移：同一天为 0，次日为 1 … */
export function daysOffsetFromStart(startIso: string, endIso: string): number {
  const [y1, m1, d1] = startIso.split("-").map(Number);
  const [y2, m2, d2] = endIso.split("-").map(Number);
  const t0 = Date.UTC(y1, m1 - 1, d1);
  const t1 = Date.UTC(y2, m2 - 1, d2);
  return Math.round((t1 - t0) / 86400000);
}

export function addDaysFromIso(startIso: string, offsetDays: number): string {
  const [y, m, d] = startIso.split("-").map(Number);
  const dt = new Date(y, m - 1, d + offsetDays);
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}`;
}

/** 某日落在哪一财务月（按当地日历年的窗口查找） */
export function findFinancialMonthContaining(isoDate: string): FinancialMonthWindow {
  const year = Number(isoDate.slice(0, 4));
  for (let i = 1; i <= 12; i++) {
    const w = getFinancialMonthWindow(year, i);
    if (isoDate >= w.start && isoDate <= w.end) {
      return w;
    }
  }
  throw new Error(`日期不在财务月覆盖范围内: ${isoDate}`);
}

export type HomeSalesFinancialMeta = {
  /** 当前财务月完整窗口 */
  window: FinancialMonthWindow;
  /** 本期统计区间起点（财务月起） */
  periodStart: string;
  /** 本期统计区间终点（截至今日，不超过财务月末） */
  periodEnd: string;
  /** 上年同期区间（与本期从财务月起经过的自然日数对齐，上年终点不超过上年该财务月末） */
  priorPeriodStart: string;
  priorPeriodEnd: string;
};

/** 根据「今天」生成本期与上年同期的销售查询区间（用于主页驾驶舱） */
export function buildHomeSalesFinancialMeta(todayIso: string): HomeSalesFinancialMeta {
  const window = findFinancialMonthContaining(todayIso);
  const periodStart = window.start;
  const periodEnd = minIsoDate(todayIso, window.end);

  const priorYearWindow = getFinancialMonthWindow(window.year - 1, window.index);
  const offset = daysOffsetFromStart(periodStart, periodEnd);
  let priorPeriodEnd = addDaysFromIso(priorYearWindow.start, offset);
  priorPeriodEnd = minIsoDate(priorPeriodEnd, priorYearWindow.end);

  return {
    window,
    periodStart,
    periodEnd,
    priorPeriodStart: priorYearWindow.start,
    priorPeriodEnd,
  };
}
