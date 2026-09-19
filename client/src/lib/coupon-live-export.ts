import XLSX from "xlsx-js-style";
import {
  type LiveReport, type LiveRow, type LiveColumn, type LiveDepartment, type HolderDetailMode,
  LIVE_COUPON_TYPES, couponColumns, departmentColumns, groupColumns, ticketColumns, trajectoryColumns,
  holderColumns, holderDetailColumns, holderDetailLabels, filterTrajectory, filterCouponDepartments,
  filterCouponGroups, summarizeHolderPeriod, holderPeriodDetails, hasMemberPeriodData,
} from "./coupon-live";

export type LiveTab = "overview" | "tickets" | "trajectory" | "members";
export type LiveExportView = {
  tab: LiveTab; coupon: string; member: string; ticketCoupon: string;
  departmentCoupon: string | null; department: LiveDepartment | null;
  holder: string | null; detailMode: HolderDetailMode;
};
export type LiveExportSheet = { name: string; rows: LiveRow[]; columns: LiveColumn[] };
export const liveTabLabels: Record<LiveTab, string> = {
  overview: "发放与使用", tickets: "销售退货明细", trajectory: "持券人今日轨迹", members: "会员期间汇总",
};

export function includesMemberSheets(tab: LiveTab, departmentCoupon: string | null): boolean {
  return tab === "members" || tab === "trajectory" || (tab === "overview" && !departmentCoupon);
}

function memberExportSheets(report: LiveReport, view: LiveExportView): LiveExportSheet[] {
  if (!hasMemberPeriodData(report)) {
    if (view.tab === "members") throw new Error("所选期间会员数据尚未就绪，请刷新并确认后端已更新");
    return [];
  }
  // A stale selection from another tab must never silently narrow the annex.
  const holder = view.tab === "members" ? view.holder : null;
  return [
    { name: "会员期间汇总", columns: holderColumns, rows: summarizeHolderPeriod(report, view.coupon, view.member)
      .filter(row => !holder || row.holder_member_no === holder) },
    { name: "会员期间明细", columns: holderDetailColumns,
      rows: holderPeriodDetails(report, view.coupon, view.member, holder, holder ? view.detailMode : "all") },
  ];
}

export function liveExportSheets(report: LiveReport, view: LiveExportView): LiveExportSheet[] {
  if (report.status !== "ready") throw new Error("数据尚未就绪，不能导出");
  if (view.tab === "tickets") return [{ name: "销售退货明细", columns: ticketColumns,
    rows: (report.tickets || []).filter(row => view.ticketCoupon === "all" || row.coupon_type === view.ticketCoupon) }];
  if (view.tab === "trajectory") return [{ name: "持券人今日轨迹", columns: trajectoryColumns,
    rows: filterTrajectory(report.trajectory || [], view.coupon, view.member) }, ...memberExportSheets(report, view)];
  if (view.tab === "members") return memberExportSheets(report, view);
  if (view.departmentCoupon) return view.department ? [{ name: "柜组使用情况", columns: groupColumns,
    rows: filterCouponGroups(report.groups || [], view.departmentCoupon, view.department) }]
    : [{ name: "部门使用情况", columns: departmentColumns,
      rows: filterCouponDepartments(report.departments || [], view.departmentCoupon) }];
  return [
    { name: "卡券汇总", columns: couponColumns, rows: report.coupons || [] },
    { name: "每日使用", columns: [["day", "业务日期"], ...couponColumns.filter(([key]) => ["redeemed_amount", "refunded_amount", "net_coupon_amount", "linked_sales", "linked_returns", "linked_gross_profit"].includes(key))], rows: report.daily || [] },
    { name: "部门使用情况", columns: departmentColumns, rows: report.departments || [] },
    { name: "柜组使用情况", columns: [["department", "部门"], ["coupon_type", "券种"], ...groupColumns], rows: report.groups || [] },
    ...memberExportSheets(report, view),
  ];
}

export function buildLiveWorkbook(report: LiveReport, view: LiveExportView) {
  // Export only the same authorized, filtered population rendered by this view,
  // never the Records component's 50-row page slice and never a second wider API.
  const sheets = liveExportSheets(report, view);
  const wb = XLSX.utils.book_new();
  const moneyKey = (key: string) => /sales|profit|amount|returns/.test(key);
  function append({ name, rows, columns }: LiveExportSheet) {
    const values = rows.map(row => columns.map(([key]) => {
      const value = row[key];
      if (value == null) return "";
      if (Array.isArray(value)) return value.join("、");
      if (/member_no|billno|_code$/.test(key)) return String(value);
      return value;
    }));
    const ws = XLSX.utils.aoa_to_sheet([columns.map(([, label]) => label), ...values]);
    ws["!cols"] = columns.map(([key]) => ({ wch: /member_no|billno|time/.test(key) ? 25 : key === "value" ? 95 : 24 }));
    ws["!rows"] = [{ hpt: 36 }];
    ws["!autofilter"] = { ref: ws["!ref"] || "A1" };
    columns.forEach(([key], c) => {
      ws[XLSX.utils.encode_cell({ r: 0, c })].s = {
        font: { bold: true, color: { rgb: "FFFFFF" } }, fill: { fgColor: { rgb: "0F172A" } },
        alignment: { vertical: "center", wrapText: true },
      };
      rows.forEach((_, index) => {
        const cell = ws[XLSX.utils.encode_cell({ r: index + 1, c })];
        if (cell?.t === "n") cell.z = moneyKey(key) ? '#,##0.00;[Red]-#,##0.00;0.00' : '#,##0';
        if (cell) cell.s = { alignment: { vertical: "center", wrapText: key === "value" } };
      });
    });
    XLSX.utils.book_append_sheet(wb, ws, name);
  }
  sheets.forEach(append);
  const selectedCoupon = view.tab === "overview" ? view.departmentCoupon || "all" : view.tab === "tickets" ? view.ticketCoupon : view.coupon;
  const memberView = includesMemberSheets(view.tab, view.departmentCoupon);
  const memberSheetsPresent = sheets.some(sheet => sheet.name === "会员期间汇总");
  append({ name: "导出口径", columns: [["key", "项目"], ["value", "说明"]], rows: [
    { key: "页面", value: "秋v卡券跟进" }, { key: "导出视图", value: liveTabLabels[view.tab] },
    { key: "门店", value: "购物中心（601）" }, { key: "数据权限", value: report.scope?.label || "当前授权范围" },
    { key: "券有效期", value: `${report.tracking_start} 至 ${report.valid_to}` },
    { key: "用券人群/核销查询期", value: `${report.query_start} 至 ${report.query_end}` },
    { key: "会员消费统计期", value: `${report.query_start} 至 ${report.query_end}（含首尾日期）` },
    { key: "实时轨迹日期", value: report.today }, { key: "数据读取时间", value: report.generated_at || "未记录" },
    { key: "最新可见销售时间", value: report.latest_visible_sale || "暂无" },
    { key: "券种筛选", value: selectedCoupon === "all" ? LIVE_COUPON_TYPES.join("、") : selectedCoupon },
    { key: "会员附表", value: !memberView ? "当前明细下钻导出不附会员表，请在总览或会员期间汇总导出。"
      : memberSheetsPresent ? "已包含会员期间汇总及会员期间明细。"
      : "所选期间会员数据尚未返回，未附会员表，不代表消费为零。" },
    { key: "会员附表券种筛选", value: memberView ? view.coupon === "all" ? LIVE_COUPON_TYPES.join("、") : view.coupon : "不适用" },
    { key: "会员查找", value: memberView ? view.member.trim() || "全部" : "不适用" },
    { key: "下钻会员", value: view.tab === "members" ? view.holder || "全部" : "不适用" },
    { key: "会员明细范围", value: view.tab === "members" && view.holder ? holderDetailLabels[view.detailMode] : "全部匹配记录" },
    { key: "部门下钻", value: view.tab === "overview" && view.department ? `${view.department.name}（${view.department.code}）` : "无" },
    { key: "导出范围", value: "当前视图及筛选下全部匹配记录，不限页面50行；仅包含后端已授权数据。" },
    { key: "会员合计", value: "所选起止日期内，购物会员卡等于持券会员卡的小票可见商品行，销售加同期间实际退货负数；不含购物会员不同或未登记的关联小票，不取系统今天替代所选日期。局部账号仅为授权范围合计。" },
    { key: "其他消费", value: "本人所选期间消费中未关联所选跟踪券的小票；选全部时为未关联任一跟踪券。退货按原小票跟踪券分类。无匹配日志不代表未使用其他种类券。" },
    { key: "关联净额", value: "购物会员不同或未登记，仅为待核查线索，不认定代付，也不计入本人合计。多人关联同票的轨迹不能直接相加。" },
    { key: "发券与连带", value: "发放是截至查询结束日本档累计，含提前发券；连带销售按有效核销券额分摊并扣实际退货，不等于增量销售。" },
    { key: "同步说明", value: "读取已同步ODS；读取时间或最新业务时间不代表ERP同步完成时间。" },
    { key: "未唯一匹配小票流水", value: report.quality?.unmatched_flow_count ?? "未返回" },
    { key: "缺少初始发券流水", value: report.quality?.missing_issue_flow_count ?? "未返回" },
    { key: "小票缺少商品明细流水", value: report.quality?.missing_sales_flow_count ?? "未返回" },
  ] });
  return wb;
}

export function liveExportFilename(report: LiveReport, view: LiveExportView): string {
  const period = `${report.query_start}_${report.query_end}`;
  const suffix = view.tab === "trajectory" ? `${period}_今日${report.today}` : period;
  return `秋v卡券跟进_${liveTabLabels[view.tab]}_${suffix}.xlsx`;
}

export function exportLiveWorkbook(report: LiveReport, view: LiveExportView) {
  const workbook = buildLiveWorkbook(report, view);
  XLSX.writeFile(workbook, liveExportFilename(report, view));
}
