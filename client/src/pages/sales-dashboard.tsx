import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Building2, Check, ChevronRight, Download, FileText, Loader2, RefreshCw, Search, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet, apiPost } from "@/lib/api";
import {
  buildProductTicketParams,
  getReceiptProductDisplay,
  getDepartmentDrilldownTab,
  getGroupDrilldownTab,
  isCosmeticsRetailPriceScope,
  isSupermarketDepartment,
} from "@/lib/sales-dashboard-drilldown";
import {
  exportDepartmentsToExcel,
  exportDepartmentGoodsToExcel,
  exportDepartmentSuppliersToExcel,
  exportGroupsToExcel,
  exportStoresToExcel,
  exportTicketsToExcel,
  formatTicketSaleDateTime,
} from "@/lib/export-sales-excel";
import { useToast } from "@/hooks/use-toast";
import { useModuleAccessLog, type ModuleQueryConditions } from "@/hooks/use-module-access-log";
import { cn } from "@/lib/utils";
import {
  getSalesDashboardData,
  isSalesDashboardTimeoutError,
  salesDashboardRangeDays,
  validateSalesDashboardDateRanges,
} from "@/lib/sales-dashboard-request";

type StoreSummary = {
  store_id: string;
  store_name: string;
  department_count: number;
  group_count: number;
  ticket_count: number;
  quantity: number;
  gross_sales: number;
  effective_sales: number;
  net_profit: number;
  net_margin: number;
  ticket_margin: number;
  /** 上年同期（日期区间平移一年） */
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_ticket_count?: number;
  same_period_margin?: number;
};

type DepartmentSummary = {
  department_code: string;
  department_name: string;
  group_count: number;
  ticket_count: number;
  quantity: number;
  gross_sales: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_ticket_count?: number;
  same_period_margin?: number;
};

type GroupSummary = {
  group_code: string;
  group_name?: string | null;
  department_code?: string | null;
  department_name?: string | null;
  ticket_count: number;
  line_count: number;
  quantity: number;
  priced_sales_amount: number;
  gross_sales: number;
  effective_sales: number;
  net_profit: number;
  /** sum(sgln2)/sum(sglxssr)，与 net_margin 同值 */
  net_margin: number;
  ticket_margin: number;
  same_period_ticket_count?: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
  same_period_margin?: number;
};

type DepartmentGoodsSummary = {
  group_code?: string | null;
  group_name?: string | null;
  goods_code: string;
  barcode?: string | null;
  goods_name?: string | null;
  category_code?: string | null;
  category_name?: string | null;
  brand_code?: string | null;
  brand_name?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  operation_method?: string | null;
  ticket_count: number;
  sales_qty: number;
  sales_amount: number;
  sales_revenue: number;
  sales_cost: number;
  sales_cost_adjustment: number;
  supplier_discount: number;
  gross_profit: number;
  gross_margin_rate: number;
};

type DepartmentSupplierSummary = {
  supplier_code: string;
  supplier_name?: string | null;
  group_count: number;
  goods_count: number;
  ticket_count: number;
  sales_qty: number;
  sales_amount: number;
  sales_revenue: number;
  sales_cost: number;
  sales_cost_adjustment: number;
  supplier_discount: number;
  gross_profit: number;
  gross_margin_rate: number;
};

type TicketSummary = {
  billno: string | number;
  sale_date?: string | null;
  sale_datetime?: string | null;
  cash_register_no?: string | null;
  invoice_no?: string | number | null;
  line_count: number;
  /** 商品件数：salegoodslist 汇总 sglsl */
  quantity: number;
  /** 零售价：salegoodslist 汇总 sglsjje */
  priced_sales_amount: number;
  /** 销售收入：salegoodslist 汇总 sglxssr */
  effective_sales: number;
  /** 毛利：salegoodslist 汇总 sgln2 */
  net_profit: number;
  /** 毛利率：sum(sgln2)/sum(sglxssr) */
  ticket_margin: number;
  /** 授权折扣：salegoodslist 行 sum(sglgrantzk) */
  authorized_discount?: number;
  /** 面值卡 MZK：sum(sglfcard) */
  mzk?: number;
  /** 礼券 LQ：salepay 中 paycode=0500 的付款金额，djlb=4 时为负数 */
  lq?: number;
  /** 小票积分合计：order_point.point，仅用于接口兼容 */
  point?: number;
  /** 消费加积分：order_point.point_type = 消费加积分 */
  consumption_point?: number;
  /** 生日月会员加积分：order_point.point_type = 生日月... */
  birthday_month_member_point?: number;
  /** 列表列「销售类型」：salehead.djlx/djlb，1 销售，4 退货 */
  transaction_type?: string | null;
};

type TicketSummaryTotals = {
  ticket_count: number;
  priced_sales_amount: number;
  effective_sales: number;
  net_profit: number;
};

type TicketDetail = {
  source: string;
  head: Record<string, unknown> | null;
  goods: Array<Record<string, unknown>>;
  payments: Array<Record<string, unknown>>;
};

type SalesAnalysisAnomaly = {
  rule_id: string;
  severity: "critical" | "high" | "medium" | "info" | string;
  group_code: string;
  group_name?: string | null;
  title: string;
  message: string;
  metrics?: Record<string, number | string | null | undefined>;
};

type SalesAnalysisAction = {
  priority: "high" | "medium" | "info" | string;
  title: string;
  description: string;
  related_rule_ids?: string[];
};

type SalesAnalysisResult = {
  scope: Record<string, unknown>;
  summary: {
    group_count: number;
    active_group_count: number;
    sales: number;
    prior_sales: number;
    sales_delta: number;
    sales_yoy_rate: number | null;
    net_profit: number;
    prior_net_profit: number;
    margin: number;
    prior_margin: number;
    ticket_count: number;
    prior_ticket_count: number;
  };
  anomalies: SalesAnalysisAnomaly[];
  actions: SalesAnalysisAction[];
  ai: {
    enabled: boolean;
    status: string;
    provider?: string;
    model?: string;
    report?: string | null;
    error?: string;
  };
};

const money = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));

/** ERP 小票头金额：保留两位小数，不带货币符号（与 ERP 列表样式接近） */
const moneyErp = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value || 0));

const number = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

/** 毛利率等：比率（0–1）转为百分比数字，固定两位小数 */
const percentRatio = (ratio?: number | null) =>
  new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    Number(ratio ?? 0) * 100,
  );

/** 销售收入同比（本期相对上年同期销售收入），返回百分比数值；上年同期≤0 无法计算 */
function salesRevenueYoYPercent(current: number | null | undefined, prior: number | null | undefined): number | null {
  const p = Number(prior ?? 0);
  const c = Number(current ?? 0);
  if (!(p > 0)) return null;
  return ((c - p) / p) * 100;
}

function formatSalesYoYPercent(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

function salesYoYPercentColorClass(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "text-slate-500";
  if (pct > 0) return "text-red-600";
  if (pct < 0) return "text-emerald-600";
  return "text-slate-600";
}

function rateColorClass(rate: number | null | undefined): string {
  if (rate == null || !Number.isFinite(rate)) return "text-slate-500";
  if (rate > 0) return "text-red-600";
  if (rate < 0) return "text-emerald-600";
  return "text-slate-600";
}

function severityBadgeClass(severity: string): string {
  if (severity === "critical" || severity === "high") return "border-red-200 bg-red-50 text-red-700";
  if (severity === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-blue-200 bg-blue-50 text-blue-700";
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    critical: "严重",
    high: "高",
    medium: "中",
    info: "提示",
  };
  return labels[severity] ?? severity;
}

function SalesYoYTableCell(props: {
  effectiveSales: number;
  samePeriodSales: number;
  footer?: boolean;
}) {
  const pct = salesRevenueYoYPercent(props.effectiveSales, props.samePeriodSales);
  return (
    <TableCell
      className={cn(
        "py-2 text-right font-medium tabular-nums",
        props.footer && "font-semibold",
        salesYoYPercentColorClass(pct),
      )}
    >
      {formatSalesYoYPercent(pct)}
    </TableCell>
  );
}

function TableStatusRow(props: { colSpan: number; loading: boolean; emptyText: string }) {
  return (
    <TableRow>
      <TableCell colSpan={props.colSpan} className="h-32 text-center">
        {props.loading ? (
          <div className="inline-flex items-center gap-2 text-sm font-medium text-blue-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            数据加载中…
          </div>
        ) : (
          <div className="text-sm text-slate-500">{props.emptyText}</div>
        )}
      </TableCell>
    </TableRow>
  );
}

function salesDataStatusText(error: unknown, emptyText: string): string {
  if (!error) return emptyText;
  return isSalesDashboardTimeoutError(error)
    ? "数据请求超时，本次查询未返回结果。可缩短日期范围后重试。"
    : "数据加载失败，本次查询未返回结果。请稍后重试。";
}

function salesTableStatusText(error: unknown, emptyText: string): string {
  if (!error) return emptyText;
  return isSalesDashboardTimeoutError(error) ? "查询超时，未返回数据。" : "数据加载失败，请稍后重试。";
}

function SummaryMetricCard(props: { title: string; value: string; loading: boolean; unavailable?: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">{props.title}</CardTitle></CardHeader>
      <CardContent className="py-3">
        {props.loading ? (
          <div className="inline-flex h-8 items-center gap-2 text-sm font-medium text-blue-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中…
          </div>
        ) : props.unavailable ? (
          <div>
            <div className="text-2xl font-semibold text-slate-400">—</div>
            <div className="mt-1 text-xs font-medium text-amber-700">查询未完成</div>
          </div>
        ) : (
          <div className="text-2xl font-semibold">{props.value}</div>
        )}
      </CardContent>
    </Card>
  );
}

function formatDateTime(value: unknown): string {
  if (value == null || value === "") return "-";
  if (typeof value === "string") {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? value : d.toLocaleString("zh-CN", { hour12: false });
  }
  return String(value);
}

function saleStatusLabel(code: unknown): string {
  const c = `${code ?? ""}`.trim().toUpperCase();
  if (!c) return "-";
  const map: Record<string, string> = {
    Y: "已审核",
    C: "已记账",
    N: "未处理",
    "1": "已审核",
    "0": "未审核",
  };
  return map[c] ?? String(code);
}

function ReceiptTicketHeaderBlock(props: {
  source: string;
  head: Record<string, unknown> | null | undefined;
  fallbackFirstRow: Record<string, unknown> | undefined;
}) {
  const { source, head, fallbackFirstRow } = props;
  const h = head ?? {};
  const fb = fallbackFirstRow ?? {};

  const billno = h.billno ?? fb.billno;
  const syjh = h.syjh ?? "-";
  const fphm = h.fphm ?? fb.invoice_no ?? "-";
  const syyh = h.syyh ?? fb.cashier ?? "-";
  const bc = h.bc ?? "-";
  const hykh = h.hykh ?? "-";
  const ysje = Number(h.ysje ?? 0);
  const sjfk = Number(h.sjfk ?? 0);
  const zl = Number(h.zl ?? 0);
  const sysy = Number(h.sswr_sysy ?? 0) + Number(h.fk_sysy ?? 0);
  const yhzke = Number(h.yhzke ?? 0);
  const hyzke = Number(h.hyzke ?? 0);
  const status = saleStatusLabel(h.status);
  const djlb = h.djlb != null && `${h.djlb}` !== "" ? String(h.djlb) : "-";
  const sendrqsj = formatDateTime(h.sendrqsj);
  const rqsj = formatDateTime(h.rqsj ?? fb.sale_datetime ?? fb.sale_date);
  const cust2 = h.str2 != null && `${h.str2}` !== "" ? String(h.str2) : "-";
  const cust3 = h.str3 != null && `${h.str3}` !== "" ? String(h.str3) : "-";
  const mkt = h.mkt != null && `${h.mkt}` !== "" ? String(h.mkt) : "-";

  const Row = ({ label, value }: { label: string; value: string }) => (
    <div className="flex min-h-[22px] items-baseline gap-2 border-b border-slate-200/80 py-0.5 last:border-b-0">
      <span className="shrink-0 text-slate-600">{label}</span>
      <span className="min-w-0 flex-1 text-right font-medium text-slate-900 tabular-nums">{value}</span>
    </div>
  );

  return (
    <div className="rounded border border-slate-300 bg-[#f0f4f8] text-[13px] shadow-sm">
      <div className="border-b border-slate-300 bg-slate-200/80 px-3 py-1.5 text-xs font-medium text-slate-700">
        数据来源：{source}
        {mkt !== "-" ? `　门店：${mkt}` : ""}
      </div>
      <div className="grid grid-cols-1 gap-0 p-2 md:grid-cols-3 md:gap-2">
        <div className="space-y-0 rounded border border-slate-200 bg-white px-2 py-1">
          <Row label="电脑小票号" value={billno != null ? String(billno) : "-"} />
          <Row label="收银机号" value={String(syjh)} />
          <Row label="小票号" value={String(fphm)} />
          <Row label="收款员" value={String(syyh)} />
          <Row label="班次" value={String(bc)} />
          <Row label="会员卡号" value={String(hykh)} />
        </div>
        <div className="space-y-0 rounded border border-slate-200 bg-white px-2 py-1">
          <Row label="实付金额" value={moneyErp(head ? sjfk : Number(fb.effective_sales ?? 0))} />
          <Row label="应收金额" value={moneyErp(head ? ysje : Number(fb.effective_sales ?? 0))} />
          <Row label="找零" value={moneyErp(head ? zl : 0)} />
          <Row label="收银损益" value={moneyErp(head ? sysy : 0)} />
          <Row label="促销折扣" value={moneyErp(head ? yhzke : 0)} />
          <Row label="会员折扣" value={moneyErp(head ? hyzke : 0)} />
        </div>
        <div className="space-y-0 rounded border border-slate-200 bg-white px-2 py-1">
          <Row label="状态" value={head ? status : "-"} />
          <Row label="小票类别" value={head ? djlb : "-"} />
          <Row label="发送时间" value={head ? sendrqsj : "-"} />
          <Row label="交易时间" value={rqsj} />
          <Row label="顾客信息2" value={head ? cust2 : "-"} />
          <Row label="顾客信息3" value={head ? cust3 : "-"} />
        </div>
      </div>
    </div>
  );
}

/** 与后端一致：区间整体减一年，闰年 2/29 对应上年 2/28 */
function priorYearRange(start: string, end: string): { start_date: string; end_date: string } | null {
  if (!start?.trim() || !end?.trim()) return null;
  try {
    const parseLocal = (s: string) => {
      const [y, m, d] = s.split("-").map((x) => Number(x));
      if (!y || !m || !d) return null;
      return new Date(y, m - 1, d);
    };
    const a = parseLocal(start);
    const b = parseLocal(end);
    if (!a || !b || Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return null;
    const ya = new Date(a);
    ya.setFullYear(ya.getFullYear() - 1);
    const yb = new Date(b);
    yb.setFullYear(yb.getFullYear() - 1);
    const pad = (n: number) => String(n).padStart(2, "0");
    const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    return { start_date: fmt(ya), end_date: fmt(yb) };
  } catch {
    return null;
  }
}

const buildQuery = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (typeof value === "boolean") {
      if (value) search.set(key, "true");
      return;
    }
    const s = `${value}`.trim();
    if (s !== "") search.set(key, s);
  });
  const value = search.toString();
  return value ? `?${value}` : "";
};

const TICKET_PAGE_SIZE = 100;
const TICKET_EXPORT_BATCH_SIZE = 5_000;

/** 部门汇总中的「未归属部门」无编码，不能靠 department_code 筛选，需走专用查询参数 */
function isUnassignedDepartmentRow(d: DepartmentSummary): boolean {
  const code = String(d.department_code ?? "").trim();
  const name = String(d.department_name ?? "").trim();
  return code === "" && (name === "未归属部门" || name === "");
}

const todayDateString = () => {
  const now = new Date();
  const timezoneOffset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - timezoneOffset).toISOString().slice(0, 10);
};

export default function SalesDashboardPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("stores");
  const today = todayDateString();
  const initialPrior = priorYearRange(today, today);
  /** 本期区间 → API start_date / end_date */
  const [currentStartDate, setCurrentStartDate] = useState(today);
  const [currentEndDate, setCurrentEndDate] = useState(today);
  /** 同期对比区间 → API prior_start_date / prior_end_date；改本期区间时按上年同日 range 自动同步 */
  const [priorStartDate, setPriorStartDate] = useState(initialPrior?.start_date ?? today);
  const [priorEndDate, setPriorEndDate] = useState(initialPrior?.end_date ?? today);
  /** 日期输入先保存在草稿中，点击“查询”后才触发大表请求，避免连续修改四个日期时重复扫描。 */
  const [draftCurrentStartDate, setDraftCurrentStartDate] = useState(today);
  const [draftCurrentEndDate, setDraftCurrentEndDate] = useState(today);
  const [draftPriorStartDate, setDraftPriorStartDate] = useState(initialPrior?.start_date ?? today);
  const [draftPriorEndDate, setDraftPriorEndDate] = useState(initialPrior?.end_date ?? today);
  const [keyword, setKeyword] = useState("");
  const [departmentProductKeyword, setDepartmentProductKeyword] = useState("");
  const [departmentProductView, setDepartmentProductView] = useState<"goods" | "suppliers" | "groups">("goods");
  const [departmentProductSupplierCode, setDepartmentProductSupplierCode] = useState<string | null>(null);
  const [excludeRental, setExcludeRental] = useState(false);
  const [excludeBackofficeDepartments, setExcludeBackofficeDepartments] = useState(false);
  const [selectedStore, setSelectedStore] = useState<StoreSummary | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentSummary | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<GroupSummary | null>(null);
  const [selectedDepartmentProduct, setSelectedDepartmentProduct] = useState<DepartmentGoodsSummary | null>(null);
  const [selectedBillno, setSelectedBillno] = useState<string | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<SalesAnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [ticketsExporting, setTicketsExporting] = useState(false);
  const [ticketPage, setTicketPage] = useState(1);
  /** 小票列表用本期日期或上年同期日期（与「同期小票数」下钻一致） */
  const [ticketsViewMode, setTicketsViewMode] = useState<"current" | "prior">("current");
  const showPricedSalesAmount = isCosmeticsRetailPriceScope(selectedStore, selectedDepartment);

  const commonParams = useMemo(
    () => ({
      start_date: currentStartDate,
      end_date: currentEndDate,
      prior_start_date: priorStartDate,
      prior_end_date: priorEndDate,
      exclude_rental: excludeRental,
      exclude_backoffice_departments: excludeBackofficeDepartments,
    }),
    [
      currentStartDate,
      currentEndDate,
      priorStartDate,
      priorEndDate,
      excludeRental,
      excludeBackofficeDepartments,
    ],
  );

  const { recordQuery } = useModuleAccessLog({
    moduleId: "sales-dashboard",
    moduleName: "电脑端销售看板",
    clientType: "desktop",
    // 主框架已经记录模块进入，避免电脑端重复写入两条进入日志。
    logEnter: false,
    initialQueryConditions: {
      query_type: "sales",
      ...commonParams,
      query_level: "stores",
    },
  });

  const recordSalesQuery = (queryLevel: string, overrides: ModuleQueryConditions = {}) => {
    recordQuery({
      query_type: "sales",
      ...commonParams,
      query_level: queryLevel,
      store_id: selectedStore?.store_id,
      store_name: selectedStore?.store_name,
      department_code: selectedDepartment?.department_code,
      department_name: selectedDepartment?.department_name,
      group_code: selectedGroup?.group_code,
      group_name: selectedGroup?.group_name,
      ...overrides,
    });
  };

  const ticketsQueryParams = useMemo(() => {
    if (ticketsViewMode === "prior") {
      return { start_date: priorStartDate, end_date: priorEndDate };
    }
    return { start_date: currentStartDate, end_date: currentEndDate };
  }, [ticketsViewMode, currentStartDate, currentEndDate, priorStartDate, priorEndDate]);

  const syncPriorRangeFromCurrent = (start: string, end: string) => {
    const r = priorYearRange(start, end);
    if (r) {
      setDraftPriorStartDate(r.start_date);
      setDraftPriorEndDate(r.end_date);
    }
  };

  const draftRangeDays = salesDashboardRangeDays(draftCurrentStartDate, draftCurrentEndDate);

  const storesQuery = useQuery<StoreSummary[]>({
    queryKey: ["/api/sales/summary/stores", commonParams],
    queryFn: () => getSalesDashboardData(`/api/sales/summary/stores${buildQuery(commonParams)}`, apiGet),
    enabled: activeTab === "stores",
  });

  const departmentsQuery = useQuery<DepartmentSummary[]>({
    queryKey: ["/api/sales/summary/departments", commonParams, selectedStore?.store_id],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/departments${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "departments",
  });

  const groupsUnassigned = Boolean(selectedDepartment && isUnassignedDepartmentRow(selectedDepartment));

  const groupsQuery = useQuery<GroupSummary[]>({
    queryKey: [
      "/api/sales/summary/groups",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      selectedDepartment?.department_name,
      groupsUnassigned,
      keyword,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/groups${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: groupsUnassigned ? undefined : selectedDepartment?.department_code,
          unassigned_department: groupsUnassigned ? true : undefined,
          keyword,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "groups" || (activeTab === "department-products" && departmentProductView === "groups"),
  });

  const departmentGoodsQuery = useQuery<DepartmentGoodsSummary[]>({
    queryKey: [
      "/api/sales/summary/department-goods",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      groupsUnassigned,
      selectedGroup?.group_code,
      departmentProductKeyword,
      departmentProductSupplierCode,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/department-goods${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: groupsUnassigned ? undefined : selectedDepartment?.department_code,
          unassigned_department: groupsUnassigned ? true : undefined,
          group_code: selectedGroup?.group_code,
          supplier_code: departmentProductSupplierCode || undefined,
          keyword: departmentProductKeyword,
          limit: 500,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "department-products" && departmentProductView === "goods" && Boolean(selectedDepartment),
  });

  const departmentSuppliersQuery = useQuery<DepartmentSupplierSummary[]>({
    queryKey: [
      "/api/sales/summary/department-suppliers",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      groupsUnassigned,
      departmentProductKeyword,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/department-suppliers${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: groupsUnassigned ? undefined : selectedDepartment?.department_code,
          unassigned_department: groupsUnassigned ? true : undefined,
          keyword: departmentProductKeyword,
          limit: 300,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "department-products" && departmentProductView === "suppliers" && Boolean(selectedDepartment),
  });

  const selectedProductTicketParams = useMemo(
    () => buildProductTicketParams(selectedDepartmentProduct),
    [selectedDepartmentProduct],
  );

  const ticketsQuery = useQuery<TicketSummary[]>({
    queryKey: [
      "/api/sales/groups/tickets",
      selectedGroup?.group_code,
      ticketsQueryParams,
      ticketsViewMode,
      selectedProductTicketParams,
      excludeRental,
      excludeBackofficeDepartments,
      ticketPage,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/groups/${encodeURIComponent(selectedGroup?.group_code ?? "")}/tickets${buildQuery({
          ...ticketsQueryParams,
          ...selectedProductTicketParams,
          exclude_rental: excludeRental,
          exclude_backoffice_departments: excludeBackofficeDepartments,
          limit: TICKET_PAGE_SIZE,
          offset: (ticketPage - 1) * TICKET_PAGE_SIZE,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "tickets" && Boolean(selectedGroup?.group_code),
  });

  const ticketsSummaryQuery = useQuery<TicketSummaryTotals>({
    queryKey: [
      "/api/sales/groups/tickets/summary",
      selectedGroup?.group_code,
      ticketsQueryParams,
      ticketsViewMode,
      selectedProductTicketParams,
      excludeRental,
      excludeBackofficeDepartments,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/groups/${encodeURIComponent(selectedGroup?.group_code ?? "")}/tickets/summary${buildQuery({
          ...ticketsQueryParams,
          ...selectedProductTicketParams,
          exclude_rental: excludeRental,
          exclude_backoffice_departments: excludeBackofficeDepartments,
        })}`,
        apiGet,
      ),
    enabled: activeTab === "tickets" && Boolean(selectedGroup?.group_code),
  });

  useEffect(() => {
    setTicketPage(1);
  }, [
    selectedGroup?.group_code,
    ticketsViewMode,
    currentStartDate,
    currentEndDate,
    priorStartDate,
    priorEndDate,
    selectedProductTicketParams.goods_code,
    selectedProductTicketParams.barcode,
    selectedProductTicketParams.supplier_code,
    excludeRental,
    excludeBackofficeDepartments,
  ]);

  const ticketDetailQuery = useQuery<TicketDetail>({
    queryKey: ["/api/sales/tickets", selectedBillno],
    queryFn: () => apiGet(`/api/sales/tickets/${encodeURIComponent(selectedBillno ?? "")}`),
    enabled: Boolean(selectedBillno),
  });

  const salesDataFetching = useMemo(
    () =>
      storesQuery.isFetching ||
      departmentsQuery.isFetching ||
      groupsQuery.isFetching ||
      departmentGoodsQuery.isFetching ||
      departmentSuppliersQuery.isFetching ||
      ticketsQuery.isFetching ||
      ticketsSummaryQuery.isFetching ||
      (Boolean(selectedBillno) && ticketDetailQuery.isFetching),
    [
      storesQuery.isFetching,
      departmentsQuery.isFetching,
      groupsQuery.isFetching,
      departmentGoodsQuery.isFetching,
      departmentSuppliersQuery.isFetching,
      ticketsQuery.isFetching,
      ticketsSummaryQuery.isFetching,
      selectedBillno,
      ticketDetailQuery.isFetching,
    ],
  );

  const storesInitialLoading = storesQuery.isLoading;
  const departmentsInitialLoading = departmentsQuery.isLoading;
  const groupsInitialLoading = groupsQuery.isLoading;
  const departmentGoodsInitialLoading = departmentGoodsQuery.isLoading;
  const departmentSuppliersInitialLoading = departmentSuppliersQuery.isLoading;
  const ticketsInitialLoading = ticketsQuery.isLoading || ticketsSummaryQuery.isLoading;
  const activeDataInitialLoading =
    (activeTab === "stores" && storesInitialLoading) ||
    (activeTab === "departments" && departmentsInitialLoading) ||
    (activeTab === "groups" && groupsInitialLoading) ||
    (activeTab === "department-products" &&
      (departmentProductView === "goods" ? departmentGoodsInitialLoading : departmentSuppliersInitialLoading)) ||
    (activeTab === "tickets" && ticketsInitialLoading);
  const activeDataError =
    activeTab === "stores"
      ? storesQuery.error
      : activeTab === "departments"
        ? departmentsQuery.error
        : activeTab === "groups"
          ? groupsQuery.error
          : activeTab === "department-products"
            ? departmentProductView === "goods"
              ? departmentGoodsQuery.error
              : departmentSuppliersQuery.error
            : activeTab === "tickets"
              ? ticketsQuery.error || ticketsSummaryQuery.error
              : null;

  /** 与当前 Tab、日期及下钻一致：各 Tab 对应当前列表数据；门店 Tab 且在面包屑中选中了门店时只统计该门店一行 */
  const totals = useMemo(() => {
    const empty = { sales: 0, profit: 0, tickets: 0, groups: 0 };
    if (activeDataError) return empty;
    if (activeTab === "tickets") {
      const summary = ticketsSummaryQuery.data;
      return summary
        ? {
            sales: Number(summary.effective_sales || 0),
            profit: Number(summary.net_profit || 0),
            tickets: Number(summary.ticket_count || 0),
            groups: summary.ticket_count > 0 ? 1 : 0,
          }
        : empty;
    }
    if (activeTab === "groups") {
      const rows = groupsQuery.data ?? [];
      return rows.reduce(
        (acc, row) => ({
          sales: acc.sales + Number(row.effective_sales || 0),
          profit: acc.profit + Number(row.net_profit || 0),
          tickets: acc.tickets + Number(row.ticket_count || 0),
          groups: acc.groups + 1,
        }),
        { ...empty },
      );
    }
    if (activeTab === "department-products") {
      const rows = departmentProductView === "suppliers" ? departmentSuppliersQuery.data ?? [] : departmentGoodsQuery.data ?? [];
      return rows.reduce(
        (acc, row) => ({
          sales: acc.sales + Number(row.sales_revenue || 0),
          profit: acc.profit + Number(row.gross_profit || 0),
          tickets: acc.tickets + Number(row.ticket_count || 0),
          groups: acc.groups + ("group_count" in row ? Number(row.group_count || 0) : row.group_code ? 1 : 0),
        }),
        { ...empty },
      );
    }
    if (activeTab === "departments") {
      const rows = departmentsQuery.data ?? [];
      return rows.reduce(
        (acc, row) => ({
          sales: acc.sales + Number(row.effective_sales || 0),
          profit: acc.profit + Number(row.net_profit || 0),
          tickets: acc.tickets + Number(row.ticket_count || 0),
          groups: acc.groups + Number(row.group_count || 0),
        }),
        { ...empty },
      );
    }
    const storeRows = storesQuery.data ?? [];
    if (selectedStore) {
      const one = storeRows.find((r) => `${r.store_id}` === `${selectedStore.store_id}`);
      if (one) {
        return {
          sales: Number(one.effective_sales || 0),
          profit: Number(one.net_profit || 0),
          tickets: Number(one.ticket_count || 0),
          groups: Number(one.group_count || 0),
        };
      }
      if (storeRows.length > 0) {
        return { ...empty };
      }
    }
    return storeRows.reduce(
      (acc, row) => ({
        sales: acc.sales + Number(row.effective_sales || 0),
        profit: acc.profit + Number(row.net_profit || 0),
        tickets: acc.tickets + Number(row.ticket_count || 0),
        groups: acc.groups + Number(row.group_count || 0),
      }),
      { ...empty },
    );
  }, [
    activeTab,
    activeDataError,
    departmentProductView,
    selectedStore,
    storesQuery.data,
    departmentsQuery.data,
    groupsQuery.data,
    departmentGoodsQuery.data,
    departmentSuppliersQuery.data,
    ticketsSummaryQuery.data,
  ]);

  const storesTableTotals = useMemo(() => {
    const rows = storesQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        department_count: acc.department_count + Number(row.department_count || 0),
        group_count: acc.group_count + Number(row.group_count || 0),
        ticket_count: acc.ticket_count + Number(row.ticket_count || 0),
        quantity: acc.quantity + Number(row.quantity || 0),
        effective_sales: acc.effective_sales + Number(row.effective_sales || 0),
        net_profit: acc.net_profit + Number(row.net_profit || 0),
        same_period_effective_sales: acc.same_period_effective_sales + Number(row.same_period_effective_sales || 0),
        same_period_net_profit: acc.same_period_net_profit + Number(row.same_period_net_profit || 0),
        same_period_ticket_count: acc.same_period_ticket_count + Number(row.same_period_ticket_count || 0),
      }),
      {
        department_count: 0,
        group_count: 0,
        ticket_count: 0,
        quantity: 0,
        effective_sales: 0,
        net_profit: 0,
        same_period_effective_sales: 0,
        same_period_net_profit: 0,
        same_period_ticket_count: 0,
      },
    );
  }, [storesQuery.data]);

  const storesTableMarginTotal = useMemo(() => {
    const t = storesTableTotals;
    return t.effective_sales > 0 ? t.net_profit / t.effective_sales : 0;
  }, [storesTableTotals]);

  const storesTableSamePeriodMarginTotal = useMemo(() => {
    const t = storesTableTotals;
    return t.same_period_effective_sales > 0 ? t.same_period_net_profit / t.same_period_effective_sales : 0;
  }, [storesTableTotals]);

  const departmentsTableTotals = useMemo(() => {
    const rows = departmentsQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        group_count: acc.group_count + Number(row.group_count || 0),
        ticket_count: acc.ticket_count + Number(row.ticket_count || 0),
        quantity: acc.quantity + Number(row.quantity || 0),
        effective_sales: acc.effective_sales + Number(row.effective_sales || 0),
        net_profit: acc.net_profit + Number(row.net_profit || 0),
        same_period_effective_sales: acc.same_period_effective_sales + Number(row.same_period_effective_sales || 0),
        same_period_net_profit: acc.same_period_net_profit + Number(row.same_period_net_profit || 0),
        same_period_ticket_count: acc.same_period_ticket_count + Number(row.same_period_ticket_count || 0),
      }),
      {
        group_count: 0,
        ticket_count: 0,
        quantity: 0,
        effective_sales: 0,
        net_profit: 0,
        same_period_effective_sales: 0,
        same_period_net_profit: 0,
        same_period_ticket_count: 0,
      },
    );
  }, [departmentsQuery.data]);

  const departmentsTableMarginTotal = useMemo(() => {
    const t = departmentsTableTotals;
    return t.effective_sales > 0 ? t.net_profit / t.effective_sales : 0;
  }, [departmentsTableTotals]);

  const departmentsTableSamePeriodMarginTotal = useMemo(() => {
    const t = departmentsTableTotals;
    return t.same_period_effective_sales > 0 ? t.same_period_net_profit / t.same_period_effective_sales : 0;
  }, [departmentsTableTotals]);

  const groupsTableTotals = useMemo(() => {
    const rows = groupsQuery.data ?? [];
    const sums = rows.reduce(
      (acc, row) => ({
        ticket_count: acc.ticket_count + Number(row.ticket_count || 0),
        quantity: acc.quantity + Number(row.quantity || 0),
        priced_sales_amount: acc.priced_sales_amount + Number(row.priced_sales_amount || 0),
        effective_sales: acc.effective_sales + Number(row.effective_sales || 0),
        net_profit: acc.net_profit + Number(row.net_profit || 0),
        same_period_ticket_count: acc.same_period_ticket_count + Number(row.same_period_ticket_count || 0),
        same_period_effective_sales: acc.same_period_effective_sales + Number(row.same_period_effective_sales || 0),
        same_period_net_profit: acc.same_period_net_profit + Number(row.same_period_net_profit || 0),
      }),
      {
        ticket_count: 0,
        quantity: 0,
        priced_sales_amount: 0,
        effective_sales: 0,
        net_profit: 0,
        same_period_ticket_count: 0,
        same_period_effective_sales: 0,
        same_period_net_profit: 0,
      },
    );
    const ticket_margin = sums.effective_sales > 0 ? sums.net_profit / sums.effective_sales : 0;
    const same_period_margin =
      sums.same_period_effective_sales > 0 ? sums.same_period_net_profit / sums.same_period_effective_sales : 0;
    return { ...sums, ticket_margin, same_period_margin };
  }, [groupsQuery.data]);

  const departmentGoodsTableTotals = useMemo(() => {
    const rows = departmentGoodsQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        ticket_count: acc.ticket_count + Number(row.ticket_count || 0),
        sales_qty: acc.sales_qty + Number(row.sales_qty || 0),
        sales_amount: acc.sales_amount + Number(row.sales_amount || 0),
        sales_revenue: acc.sales_revenue + Number(row.sales_revenue || 0),
        sales_cost: acc.sales_cost + Number(row.sales_cost || 0),
        sales_cost_adjustment: acc.sales_cost_adjustment + Number(row.sales_cost_adjustment || 0),
        supplier_discount: acc.supplier_discount + Number(row.supplier_discount || 0),
        gross_profit: acc.gross_profit + Number(row.gross_profit || 0),
      }),
      {
        ticket_count: 0,
        sales_qty: 0,
        sales_amount: 0,
        sales_revenue: 0,
        sales_cost: 0,
        sales_cost_adjustment: 0,
        supplier_discount: 0,
        gross_profit: 0,
      },
    );
  }, [departmentGoodsQuery.data]);

  const departmentSuppliersTableTotals = useMemo(() => {
    const rows = departmentSuppliersQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        group_count: acc.group_count + Number(row.group_count || 0),
        goods_count: acc.goods_count + Number(row.goods_count || 0),
        ticket_count: acc.ticket_count + Number(row.ticket_count || 0),
        sales_qty: acc.sales_qty + Number(row.sales_qty || 0),
        sales_amount: acc.sales_amount + Number(row.sales_amount || 0),
        sales_revenue: acc.sales_revenue + Number(row.sales_revenue || 0),
        sales_cost: acc.sales_cost + Number(row.sales_cost || 0),
        sales_cost_adjustment: acc.sales_cost_adjustment + Number(row.sales_cost_adjustment || 0),
        supplier_discount: acc.supplier_discount + Number(row.supplier_discount || 0),
        gross_profit: acc.gross_profit + Number(row.gross_profit || 0),
      }),
      {
        group_count: 0,
        goods_count: 0,
        ticket_count: 0,
        sales_qty: 0,
        sales_amount: 0,
        sales_revenue: 0,
        sales_cost: 0,
        sales_cost_adjustment: 0,
        supplier_discount: 0,
        gross_profit: 0,
      },
    );
  }, [departmentSuppliersQuery.data]);

  const departmentGoodsMarginTotal = useMemo(() => {
    const t = departmentGoodsTableTotals;
    return t.sales_revenue > 0 ? t.gross_profit / t.sales_revenue : 0;
  }, [departmentGoodsTableTotals]);

  const departmentSuppliersMarginTotal = useMemo(() => {
    const t = departmentSuppliersTableTotals;
    return t.sales_revenue > 0 ? t.gross_profit / t.sales_revenue : 0;
  }, [departmentSuppliersTableTotals]);

  const ticketsTableTotals = useMemo(() => {
    const rows = ticketsQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        priced_sales_amount: acc.priced_sales_amount + Number(row.priced_sales_amount || 0),
        effective_sales: acc.effective_sales + Number(row.effective_sales || 0),
        net_profit: acc.net_profit + Number(row.net_profit || 0),
        authorized_discount: acc.authorized_discount + Number(row.authorized_discount ?? 0),
        mzk: acc.mzk + Number(row.mzk ?? 0),
        lq: acc.lq + Number(row.lq ?? 0),
        consumption_point: acc.consumption_point + Number(row.consumption_point ?? 0),
        birthday_month_member_point:
          acc.birthday_month_member_point + Number(row.birthday_month_member_point ?? 0),
      }),
      {
        priced_sales_amount: 0,
        effective_sales: 0,
        net_profit: 0,
        authorized_discount: 0,
        mzk: 0,
        lq: 0,
        consumption_point: 0,
        birthday_month_member_point: 0,
      },
    );
  }, [ticketsQuery.data]);

  const ticketsTableMarginTotal = useMemo(() => {
    const t = ticketsTableTotals;
    return t.effective_sales > 0 ? t.net_profit / t.effective_sales : 0;
  }, [ticketsTableTotals]);

  const ticketTotalCount = Number(ticketsSummaryQuery.data?.ticket_count ?? 0);
  const ticketTotalPages = Math.max(1, Math.ceil(ticketTotalCount / TICKET_PAGE_SIZE));

  useEffect(() => {
    if (ticketPage > ticketTotalPages) setTicketPage(ticketTotalPages);
  }, [ticketPage, ticketTotalPages]);

  const refresh = () => {
    recordSalesQuery(
      activeTab === "department-products" ? departmentProductView : activeTab,
      {
        keyword: activeTab === "groups" ? keyword : activeTab === "department-products" ? departmentProductKeyword : undefined,
        supplier_code: departmentProductSupplierCode,
        page: activeTab === "tickets" ? ticketPage : undefined,
        view_mode: activeTab === "tickets" ? ticketsViewMode : undefined,
        refresh: true,
      },
    );
    if (activeTab === "stores") storesQuery.refetch();
    if (activeTab === "departments") departmentsQuery.refetch();
    if (activeTab === "groups") groupsQuery.refetch();
    if (activeTab === "department-products" && departmentProductView === "groups") groupsQuery.refetch();
    if (activeTab === "department-products" && departmentProductView === "goods") departmentGoodsQuery.refetch();
    if (activeTab === "department-products" && departmentProductView === "suppliers") departmentSuppliersQuery.refetch();
    if (activeTab === "tickets" && selectedGroup?.group_code) {
      ticketsQuery.refetch();
      ticketsSummaryQuery.refetch();
    }
    if (selectedBillno) ticketDetailQuery.refetch();
  };

  const applyDateRange = () => {
    const ranges = {
      currentStartDate: draftCurrentStartDate,
      currentEndDate: draftCurrentEndDate,
      priorStartDate: draftPriorStartDate,
      priorEndDate: draftPriorEndDate,
    };
    const validationError = validateSalesDashboardDateRanges(ranges);
    if (validationError) {
      toast({ title: "日期范围有误", description: validationError, variant: "destructive" });
      return;
    }
    const unchanged =
      currentStartDate === draftCurrentStartDate &&
      currentEndDate === draftCurrentEndDate &&
      priorStartDate === draftPriorStartDate &&
      priorEndDate === draftPriorEndDate;
    if (unchanged) {
      refresh();
      return;
    }
    recordSalesQuery(activeTab === "department-products" ? departmentProductView : activeTab, {
      start_date: draftCurrentStartDate,
      end_date: draftCurrentEndDate,
      prior_start_date: draftPriorStartDate,
      prior_end_date: draftPriorEndDate,
      keyword: activeTab === "groups" ? keyword : activeTab === "department-products" ? departmentProductKeyword : undefined,
      supplier_code: departmentProductSupplierCode,
      page: activeTab === "tickets" ? ticketPage : undefined,
      view_mode: activeTab === "tickets" ? ticketsViewMode : undefined,
    });
    setCurrentStartDate(draftCurrentStartDate);
    setCurrentEndDate(draftCurrentEndDate);
    setPriorStartDate(draftPriorStartDate);
    setPriorEndDate(draftPriorEndDate);
  };

  const applyRecentRange = (days: number) => {
    const end = new Date(`${draftCurrentEndDate || today}T00:00:00`);
    if (Number.isNaN(end.getTime())) return;
    const start = new Date(end);
    start.setDate(start.getDate() - Math.max(0, days - 1));
    const pad = (value: number) => String(value).padStart(2, "0");
    const format = (value: Date) => `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
    const nextCurrentStart = format(start);
    const nextCurrentEnd = format(end);
    const nextPrior = priorYearRange(nextCurrentStart, nextCurrentEnd);
    if (!nextPrior) return;
    setDraftCurrentStartDate(nextCurrentStart);
    setDraftCurrentEndDate(nextCurrentEnd);
    setDraftPriorStartDate(nextPrior.start_date);
    setDraftPriorEndDate(nextPrior.end_date);
    setCurrentStartDate(nextCurrentStart);
    setCurrentEndDate(nextCurrentEnd);
    setPriorStartDate(nextPrior.start_date);
    setPriorEndDate(nextPrior.end_date);
    recordSalesQuery("stores", {
      start_date: nextCurrentStart,
      end_date: nextCurrentEnd,
      prior_start_date: nextPrior.start_date,
      prior_end_date: nextPrior.end_date,
      preset_days: days,
    });
  };

  const drillToStore = (store: StoreSummary) => {
    recordSalesQuery("departments", {
      store_id: store.store_id,
      store_name: store.store_name,
    });
    setSelectedStore(store);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setDepartmentProductSupplierCode(null);
    setActiveTab("departments");
  };

  const drillToDepartment = (department: DepartmentSummary) => {
    recordSalesQuery("groups", {
      department_code: department.department_code,
      department_name: department.department_name,
      unassigned_department: isUnassignedDepartmentRow(department),
    });
    setSelectedDepartment(department);
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setDepartmentProductSupplierCode(null);
    setDepartmentProductView("goods");
    setActiveTab(getDepartmentDrilldownTab(department));
  };

  const drillToGroup = (group: GroupSummary) => {
    const nextTab = getGroupDrilldownTab(selectedDepartment);
    recordSalesQuery(nextTab === "department-products" ? "goods" : "tickets", {
      group_code: group.group_code,
      group_name: group.group_name,
    });
    setSelectedGroup(group);
    setSelectedDepartmentProduct(null);
    setTicketsViewMode("current");
    setDepartmentProductView("goods");
    setActiveTab(nextTab);
  };

  const drillToDepartmentProduct = (product: DepartmentGoodsSummary) => {
    recordSalesQuery("tickets", {
      group_code: product.group_code,
      group_name: product.group_name,
      goods_code: product.goods_code,
      barcode: product.barcode,
      supplier_code: product.supplier_code,
    });
    if (product.group_code && (!selectedGroup || selectedGroup.group_code !== product.group_code)) {
      setSelectedGroup({
        group_code: product.group_code,
        group_name: product.group_name,
        department_code: selectedDepartment?.department_code,
        department_name: selectedDepartment?.department_name,
        ticket_count: 0,
        line_count: 0,
        quantity: 0,
        priced_sales_amount: 0,
        gross_sales: 0,
        effective_sales: 0,
        net_profit: 0,
        net_margin: 0,
        ticket_margin: 0,
      });
    }
    setSelectedDepartmentProduct(product);
    setTicketsViewMode("current");
    setActiveTab("tickets");
  };

  const openPriorPeriodTickets = (event: MouseEvent, group: GroupSummary) => {
    event.stopPropagation();
    if (!Number(group.same_period_ticket_count ?? 0)) return;
    recordSalesQuery("tickets", {
      start_date: priorStartDate,
      end_date: priorEndDate,
      view_mode: "prior",
      group_code: group.group_code,
      group_name: group.group_name,
    });
    setSelectedGroup(group);
    setSelectedDepartmentProduct(null);
    setTicketsViewMode("prior");
    setActiveTab("tickets");
  };

  const resetDrilldown = () => {
    recordSalesQuery("stores", {
      navigation_action: "back",
      from_level: activeTab,
      to_level: "stores",
    });
    setSelectedStore(null);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setDepartmentProductSupplierCode(null);
    setTicketsViewMode("current");
    setActiveTab("stores");
  };

  const backToStores = () => {
    recordSalesQuery("stores", {
      navigation_action: "back",
      from_level: activeTab,
      to_level: "stores",
    });
    setSelectedStore(null);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setDepartmentProductSupplierCode(null);
    setTicketsViewMode("current");
    setActiveTab("stores");
  };

  const backToDepartments = () => {
    recordSalesQuery("departments", {
      navigation_action: "back",
      from_level: activeTab,
      to_level: "departments",
    });
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setDepartmentProductSupplierCode(null);
    setTicketsViewMode("current");
    setActiveTab("departments");
  };

  const backToGroups = () => {
    recordSalesQuery("groups", {
      navigation_action: "back",
      from_level: activeTab,
      to_level: "groups",
    });
    setSelectedGroup(null);
    setSelectedDepartmentProduct(null);
    setTicketsViewMode("current");
    setActiveTab("groups");
  };

  const backFromTickets = () => {
    setTicketsViewMode("current");
    if (selectedDepartmentProduct && isSupermarketDepartment(selectedDepartment)) {
      recordSalesQuery("goods", {
        navigation_action: "back",
        from_level: "tickets",
        to_level: "goods",
      });
      setSelectedDepartmentProduct(null);
      setActiveTab("department-products");
      return;
    }
    backToGroups();
  };

  const toggleExcludeRental = () => {
    const nextValue = !excludeRental;
    recordSalesQuery(activeTab === "department-products" ? departmentProductView : activeTab, {
      exclude_rental: nextValue,
      filter_action: nextValue ? "exclude_rental" : "include_rental",
    });
    setExcludeRental(nextValue);
  };

  const toggleExcludeBackofficeDepartments = () => {
    const nextValue = !excludeBackofficeDepartments;
    recordSalesQuery(activeTab === "department-products" ? departmentProductView : activeTab, {
      exclude_backoffice_departments: nextValue,
      filter_action: nextValue ? "exclude_backoffice_departments" : "include_backoffice_departments",
    });
    setExcludeBackofficeDepartments(nextValue);
  };

  const openTicketDetail = (row: TicketSummary) => {
    recordSalesQuery("detail", {
      start_date: ticketsQueryParams.start_date,
      end_date: ticketsQueryParams.end_date,
      view_mode: ticketsViewMode,
      goods_code: selectedDepartmentProduct?.goods_code,
      barcode: selectedDepartmentProduct?.barcode,
      supplier_code: selectedDepartmentProduct?.supplier_code,
      ticket_no: `${row.invoice_no || row.billno}`,
      bill_no: `${row.billno}`,
    });
    setSelectedBillno(`${row.billno}`);
  };

  const handleExportStores = () => {
    const rows = storesQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无数据可导出", variant: "destructive" });
      return;
    }
    try {
      exportStoresToExcel(rows, currentStartDate, currentEndDate);
      toast({ title: "已导出 Excel" });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  const handleExportDepartments = () => {
    const rows = departmentsQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无数据可导出", variant: "destructive" });
      return;
    }
    try {
      exportDepartmentsToExcel(rows, currentStartDate, currentEndDate);
      toast({ title: "已导出 Excel" });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  const handleExportGroups = () => {
    const rows = groupsQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无数据可导出", variant: "destructive" });
      return;
    }
    try {
      exportGroupsToExcel(rows, currentStartDate, currentEndDate, {
        includePricedSalesAmount: showPricedSalesAmount,
      });
      toast({ title: "已导出 Excel" });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  const handleExportDepartmentGoods = () => {
    const rows = departmentGoodsQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无商品明细可导出", variant: "destructive" });
      return;
    }
    try {
      exportDepartmentGoodsToExcel(rows, {
        startDate: currentStartDate,
        endDate: currentEndDate,
        departmentName: selectedDepartment?.department_name,
      });
      toast({ title: "已导出 Excel" });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  const handleExportDepartmentSuppliers = () => {
    const rows = departmentSuppliersQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无供应商汇总可导出", variant: "destructive" });
      return;
    }
    try {
      exportDepartmentSuppliersToExcel(rows, {
        startDate: currentStartDate,
        endDate: currentEndDate,
        departmentName: selectedDepartment?.department_name,
      });
      toast({ title: "已导出 Excel" });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    }
  };

  const handleAnalyzeGroups = async () => {
    if ((groupsQuery.data ?? []).length === 0) {
      toast({ title: "暂无柜组数据可分析", variant: "destructive" });
      return;
    }
    setAnalysisOpen(true);
    setAnalysisLoading(true);
    try {
      const result = await apiPost<SalesAnalysisResult>("/api/sales/analysis", {
        level: "groups",
        start_date: currentStartDate,
        end_date: currentEndDate,
        prior_start_date: priorStartDate,
        prior_end_date: priorEndDate,
        store_id: selectedStore?.store_id,
        department_code: groupsUnassigned ? undefined : selectedDepartment?.department_code,
        unassigned_department: groupsUnassigned,
        keyword,
        exclude_rental: excludeRental,
        exclude_backoffice_departments: excludeBackofficeDepartments,
        limit: 200,
        include_ai: true,
      });
      setAnalysisResult(result);
      if (result.ai?.status && !["success", "skipped"].includes(result.ai.status)) {
        toast({
          title: "已返回规则分析",
          description: result.ai.error || "AI 报告暂不可用，可先查看规则分析结果。",
        });
      }
    } catch (err) {
      toast({
        title: "AI 分析失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleExportTickets = async () => {
    if (!selectedGroup?.group_code) {
      toast({ title: "请先选择柜组并打开小票列表", variant: "destructive" });
      return;
    }
    setTicketsExporting(true);
    try {
      const baseParams = {
        ...ticketsQueryParams,
        ...selectedProductTicketParams,
        exclude_rental: excludeRental,
        exclude_backoffice_departments: excludeBackofficeDepartments,
      };
      const summary = await apiGet<TicketSummaryTotals>(
        `/api/sales/groups/${encodeURIComponent(selectedGroup.group_code)}/tickets/summary${buildQuery(baseParams)}`,
      );
      if (!summary.ticket_count) {
        toast({ title: "暂无小票数据可导出", variant: "destructive" });
        return;
      }

      const rows: TicketSummary[] = [];
      for (let offset = 0; offset < summary.ticket_count; offset += TICKET_EXPORT_BATCH_SIZE) {
        const batch = await apiGet<TicketSummary[]>(
          `/api/sales/groups/${encodeURIComponent(selectedGroup.group_code)}/tickets${buildQuery({
            ...baseParams,
            limit: TICKET_EXPORT_BATCH_SIZE,
            offset,
          })}`,
        );
        rows.push(...batch);
        if (batch.length === 0 && rows.length < summary.ticket_count) {
          throw new Error(`小票明细仅返回 ${rows.length.toLocaleString("zh-CN")} / ${summary.ticket_count.toLocaleString("zh-CN")} 张，请重试`);
        }
      }
      if (rows.length < summary.ticket_count) {
        throw new Error(`小票明细仅返回 ${rows.length.toLocaleString("zh-CN")} / ${summary.ticket_count.toLocaleString("zh-CN")} 张，请重试`);
      }
      exportTicketsToExcel(rows.slice(0, summary.ticket_count), {
        startDate: ticketsQueryParams.start_date,
        endDate: ticketsQueryParams.end_date,
        groupCode: selectedGroup.group_code,
        groupName: selectedGroup.group_name,
        viewMode: ticketsViewMode,
        includePricedSalesAmount: showPricedSalesAmount,
      });
      toast({ title: `已导出 ${summary.ticket_count.toLocaleString("zh-CN")} 张小票` });
    } catch (err) {
      toast({
        title: "导出失败",
        description: err instanceof Error ? err.message : String(err),
        variant: "destructive",
      });
    } finally {
      setTicketsExporting(false);
    }
  };

  return (
    <div className="relative w-full space-y-6 p-6">
      {salesDataFetching && (
        <div
          className="sales-dashboard-fetch-track pointer-events-none absolute left-6 right-6 top-0 z-10 h-1 rounded-full bg-slate-200/90"
          role="progressbar"
          aria-valuetext="加载中"
        >
          <div className="sales-dashboard-fetch-bar" />
        </div>
      )}

      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-slate-900">销售看板</h1>
            {salesDataFetching && (
              <>
                <Loader2 className="h-5 w-5 shrink-0 animate-spin text-blue-600" aria-hidden />
                <span className="sr-only">数据加载中</span>
                <span className="text-sm font-medium text-blue-600" aria-hidden>
                  加载中…
                </span>
              </>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">按权限范围查看门店、部门、柜组与小票明细。</p>
        </div>
        <div className="grid w-full grid-cols-2 items-end gap-3 sm:w-auto xl:grid-cols-[repeat(4,minmax(136px,1fr))_auto]">
          <div className="space-y-1">
            <Label htmlFor="sales-current-start">本期开始日期</Label>
            <Input
              id="sales-current-start"
              type="date"
              value={draftCurrentStartDate}
              onChange={(event) => {
                const v = event.target.value;
                setDraftCurrentStartDate(v);
                syncPriorRangeFromCurrent(v, draftCurrentEndDate);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-current-end">本期结束日期</Label>
            <Input
              id="sales-current-end"
              type="date"
              value={draftCurrentEndDate}
              onChange={(event) => {
                const v = event.target.value;
                setDraftCurrentEndDate(v);
                syncPriorRangeFromCurrent(draftCurrentStartDate, v);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-prior-start">同期开始日期</Label>
            <Input
              id="sales-prior-start"
              type="date"
              value={draftPriorStartDate}
              onChange={(event) => setDraftPriorStartDate(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-prior-end">同期结束日期</Label>
            <Input
              id="sales-prior-end"
              type="date"
              value={draftPriorEndDate}
              onChange={(event) => setDraftPriorEndDate(event.target.value)}
            />
          </div>
          <Button
            onClick={applyDateRange}
            disabled={salesDataFetching}
            aria-busy={salesDataFetching}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", salesDataFetching && "animate-spin")} />
            {salesDataFetching ? "查询中…" : "查询"}
          </Button>
        </div>
      </div>

      {draftRangeDays > 92 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
          <span>当前本期跨度 {draftRangeDays} 天。大范围查询可能较慢；修改日期后点击“查询”才会重新加载。</span>
          <Button type="button" variant="outline" size="sm" onClick={() => applyRecentRange(30)} disabled={salesDataFetching}>
            查询近 30 天
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <SummaryMetricCard title="销售收入" value={money(totals.sales)} loading={activeDataInitialLoading} unavailable={Boolean(activeDataError)} />
        <SummaryMetricCard title="净毛利" value={money(totals.profit)} loading={activeDataInitialLoading} unavailable={Boolean(activeDataError)} />
        <SummaryMetricCard title="小票数" value={number(totals.tickets)} loading={activeDataInitialLoading} unavailable={Boolean(activeDataError)} />
        <SummaryMetricCard title="柜组数" value={number(totals.groups)} loading={activeDataInitialLoading} unavailable={Boolean(activeDataError)} />
      </div>

      {activeDataError && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert">
          <span>{salesDataStatusText(activeDataError, "")}</span>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={refresh} disabled={salesDataFetching}>
              重试
            </Button>
            {isSalesDashboardTimeoutError(activeDataError) && (
              <Button type="button" variant="outline" size="sm" onClick={() => applyRecentRange(30)} disabled={salesDataFetching}>
                查询近 30 天
              </Button>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
        <button className="font-medium text-slate-900 hover:text-blue-700" onClick={resetDrilldown}>
          门店
        </button>
        {selectedStore && (
          <>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <button className="font-medium text-slate-900 hover:text-blue-700" onClick={() => setActiveTab("departments")}>
              {selectedStore.store_name || selectedStore.store_id}
            </button>
          </>
        )}
        {selectedDepartment && (
          <>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <button
              className="font-medium text-slate-900 hover:text-blue-700"
              onClick={() => setActiveTab(isSupermarketDepartment(selectedDepartment) ? "department-products" : "groups")}
            >
              {selectedDepartment.department_name}
            </button>
          </>
        )}
        {selectedGroup && (
          <>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <button
              className="font-medium text-slate-900 hover:text-blue-700"
              onClick={() => setActiveTab(getGroupDrilldownTab(selectedDepartment))}
            >
              {selectedGroup.group_name || selectedGroup.group_code}
            </button>
          </>
        )}
        {selectedDepartmentProduct && (
          <>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <button className="font-medium text-slate-900 hover:text-blue-700" onClick={() => setActiveTab("tickets")}>
              {selectedDepartmentProduct.goods_name || selectedDepartmentProduct.goods_code}
            </button>
          </>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <TabsList>
            <TabsTrigger value="stores"><Building2 className="mr-2 h-4 w-4" />门店</TabsTrigger>
            <TabsTrigger value="departments"><BarChart3 className="mr-2 h-4 w-4" />部门</TabsTrigger>
            <TabsTrigger value="department-products" disabled={!selectedDepartment}><FileText className="mr-2 h-4 w-4" />商品</TabsTrigger>
            <TabsTrigger value="groups"><Search className="mr-2 h-4 w-4" />柜组</TabsTrigger>
            <TabsTrigger value="tickets" disabled={!selectedGroup}><FileText className="mr-2 h-4 w-4" />小票</TabsTrigger>
          </TabsList>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant={excludeRental ? "default" : "outline"}
              aria-pressed={excludeRental}
              onClick={toggleExcludeRental}
            >
              {excludeRental && <Check className="mr-2 h-4 w-4" />}
              排除租赁销售
            </Button>
            <Button
              type="button"
              size="sm"
              variant={excludeBackofficeDepartments ? "default" : "outline"}
              aria-pressed={excludeBackofficeDepartments}
              onClick={toggleExcludeBackofficeDepartments}
            >
              {excludeBackofficeDepartments && <Check className="mr-2 h-4 w-4" />}
              排除后台部门销售
            </Button>
          </div>
        </div>

        <TabsContent value="stores">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle>门店销售汇总</CardTitle>
              <Button type="button" variant="outline" size="sm" onClick={handleExportStores}>
                <Download className="mr-2 h-4 w-4" />
                导出 Excel
              </Button>
            </CardHeader>
            <CardContent className="pb-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>门店</TableHead>
                    <TableHead className="text-right">本期销售收入</TableHead>
                    <TableHead className="text-right">同期销售收入</TableHead>
                    <TableHead className="text-right">销售收入同比</TableHead>
                    <TableHead className="text-right">毛利</TableHead>
                    <TableHead className="text-right">同期毛利</TableHead>
                    <TableHead className="text-right">本期毛利率</TableHead>
                    <TableHead className="text-right">同期毛利率</TableHead>
                    <TableHead className="text-right">同期小票数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {storesInitialLoading || storesQuery.isError || (storesQuery.data ?? []).length === 0 ? (
                    <TableStatusRow
                      colSpan={9}
                      loading={storesInitialLoading}
                      emptyText={salesTableStatusText(storesQuery.error, "当前日期和权限范围内暂无门店销售数据。")}
                    />
                  ) : (
                    (storesQuery.data ?? []).map((row) => (
                      <TableRow key={row.store_id} className="cursor-pointer hover:bg-slate-50" onClick={() => drillToStore(row)}>
                        <TableCell className="py-2">
                          <div className="font-medium">{row.store_name || row.store_id}</div>
                          <div className="text-xs text-slate-500">{row.store_id}</div>
                        </TableCell>
                        <TableCell className="py-2 text-right">{money(row.effective_sales)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_effective_sales)}</TableCell>
                        <SalesYoYTableCell effectiveSales={Number(row.effective_sales)} samePeriodSales={Number(row.same_period_effective_sales ?? 0)} />
                        <TableCell className="py-2 text-right">{money(row.net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.ticket_margin ?? row.net_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.same_period_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">{number(row.same_period_ticket_count)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
                {!storesQuery.isError && (storesQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold">合计</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(storesTableTotals.effective_sales)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(storesTableTotals.same_period_effective_sales)}</TableCell>
                      <SalesYoYTableCell
                        footer
                        effectiveSales={storesTableTotals.effective_sales}
                        samePeriodSales={storesTableTotals.same_period_effective_sales}
                      />
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(storesTableTotals.net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(storesTableTotals.same_period_net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(storesTableMarginTotal)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(storesTableSamePeriodMarginTotal)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(storesTableTotals.same_period_ticket_count)}</TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="departments">
          <Card>
            <CardHeader className="flex flex-col gap-3 py-3 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>部门销售汇总</CardTitle>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {selectedStore && <Badge variant="outline">{selectedStore.store_name || selectedStore.store_id}</Badge>}
                  {selectedStore && (
                    <Button variant="ghost" size="sm" onClick={backToStores}>
                      返回门店
                    </Button>
                  )}
                </div>
              </div>
              <Button type="button" variant="outline" size="sm" className="shrink-0" onClick={handleExportDepartments}>
                <Download className="mr-2 h-4 w-4" />
                导出 Excel
              </Button>
            </CardHeader>
            <CardContent className="pb-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>部门</TableHead>
                    <TableHead className="text-right">本期销售收入</TableHead>
                    <TableHead className="text-right">同期销售收入</TableHead>
                    <TableHead className="text-right">销售收入同比</TableHead>
                    <TableHead className="text-right">毛利</TableHead>
                    <TableHead className="text-right">同期毛利</TableHead>
                    <TableHead className="text-right">本期毛利率</TableHead>
                    <TableHead className="text-right">同期毛利率</TableHead>
                    <TableHead className="text-right">同期小票数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {departmentsInitialLoading || departmentsQuery.isError || (departmentsQuery.data ?? []).length === 0 ? (
                    <TableStatusRow
                      colSpan={9}
                      loading={departmentsInitialLoading}
                      emptyText={salesTableStatusText(departmentsQuery.error, "当前日期和权限范围内暂无部门销售数据。")}
                    />
                  ) : (
                    (departmentsQuery.data ?? []).map((row) => (
                      <TableRow key={`${row.department_code}-${row.department_name}`} className="cursor-pointer hover:bg-slate-50" onClick={() => drillToDepartment(row)}>
                        <TableCell className="py-2">
                          <div className="font-medium">{row.department_name}</div>
                          <div className="text-xs text-slate-500">{row.department_code || "未设置编码"}</div>
                        </TableCell>
                        <TableCell className="py-2 text-right">{money(row.effective_sales)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_effective_sales)}</TableCell>
                        <SalesYoYTableCell effectiveSales={Number(row.effective_sales)} samePeriodSales={Number(row.same_period_effective_sales ?? 0)} />
                        <TableCell className="py-2 text-right">{money(row.net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.ticket_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.same_period_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">{number(row.same_period_ticket_count)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
                {!departmentsQuery.isError && (departmentsQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold">合计</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(departmentsTableTotals.effective_sales)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(departmentsTableTotals.same_period_effective_sales)}</TableCell>
                      <SalesYoYTableCell
                        footer
                        effectiveSales={departmentsTableTotals.effective_sales}
                        samePeriodSales={departmentsTableTotals.same_period_effective_sales}
                      />
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(departmentsTableTotals.net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(departmentsTableTotals.same_period_net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(departmentsTableMarginTotal)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(departmentsTableSamePeriodMarginTotal)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(departmentsTableTotals.same_period_ticket_count)}</TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="department-products">
          <Card>
            <CardHeader className="flex flex-col gap-3 py-3 md:flex-row md:items-start md:justify-between">
              <div>
                <CardTitle>部门商品分析</CardTitle>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {selectedStore && <Badge variant="outline">{selectedStore.store_name || selectedStore.store_id}</Badge>}
                  {selectedDepartment && <Badge variant="outline">{selectedDepartment.department_name}</Badge>}
                  {selectedGroup && <Badge variant="outline">{selectedGroup.group_name || selectedGroup.group_code}</Badge>}
                  {departmentProductSupplierCode && (
                    <Badge variant="secondary" className="font-normal">
                      供应商 {departmentProductSupplierCode}
                    </Badge>
                  )}
                  <Button variant="ghost" size="sm" onClick={backToDepartments}>
                    返回部门
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedGroup(null);
                      setSelectedDepartmentProduct(null);
                      setActiveTab("groups");
                    }}
                  >
                    查看柜组汇总
                  </Button>
                </div>
              </div>
              <div className="flex w-full flex-col gap-2 md:w-auto">
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant={departmentProductView === "goods" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setDepartmentProductView("goods")}
                  >
                    商品明细
                  </Button>
                  <Button
                    type="button"
                    variant={departmentProductView === "suppliers" ? "default" : "outline"}
                    size="sm"
                    onClick={() => {
                      setDepartmentProductSupplierCode(null);
                      setDepartmentProductView("suppliers");
                    }}
                  >
                    供应商汇总
                  </Button>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Input
                    className="max-w-xs"
                    placeholder={departmentProductView === "suppliers" ? "搜索供应商编码/名称" : "搜索商品/条码/柜组/供应商"}
                    value={departmentProductKeyword}
                    onChange={(event) => setDepartmentProductKeyword(event.target.value)}
                  />
                  {departmentProductSupplierCode && (
                    <Button type="button" variant="outline" size="sm" onClick={() => setDepartmentProductSupplierCode(null)}>
                      清除供应商筛选
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={departmentProductView === "suppliers" ? handleExportDepartmentSuppliers : handleExportDepartmentGoods}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    导出 Excel
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pb-3">
              {departmentProductView === "suppliers" ? (
                <Table className="min-w-[1500px] table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[260px] whitespace-nowrap">供应商</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">柜组数</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">商品数</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">小票数</TableHead>
                      <TableHead className="w-[110px] whitespace-nowrap text-right">销售数量</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售金额</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售收入</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售成本</TableHead>
                      <TableHead className="w-[110px] whitespace-nowrap text-right">成本调整</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">供应商折扣</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">毛利</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">毛利率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {departmentSuppliersInitialLoading || departmentSuppliersQuery.isError || (departmentSuppliersQuery.data ?? []).length === 0 ? (
                      <TableStatusRow
                        colSpan={12}
                        loading={departmentSuppliersInitialLoading}
                        emptyText={salesTableStatusText(departmentSuppliersQuery.error, "当前筛选条件下暂无供应商汇总数据。")}
                      />
                    ) : (
                      (departmentSuppliersQuery.data ?? []).map((row) => (
                        <TableRow
                          key={row.supplier_code}
                          className="cursor-pointer hover:bg-slate-50"
                          onClick={() => {
                            recordSalesQuery("goods", {
                              supplier_code: row.supplier_code,
                              supplier_name: row.supplier_name,
                            });
                            setDepartmentProductSupplierCode(row.supplier_code);
                            setDepartmentProductView("goods");
                          }}
                        >
                          <TableCell className="py-2">
                            <div className="truncate font-medium" title={row.supplier_name || row.supplier_code}>{row.supplier_name || row.supplier_code}</div>
                            <div className="text-xs text-slate-500">{row.supplier_code || "未设置编码"}</div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.group_count)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.goods_count)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.ticket_count)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.sales_qty)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_amount)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_revenue)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_cost)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_cost_adjustment)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.supplier_discount)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.gross_profit)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{percentRatio(row.gross_margin_rate)}%</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                  {!departmentSuppliersQuery.isError && (departmentSuppliersQuery.data ?? []).length > 0 && (
                    <TableFooter>
                      <TableRow className="hover:bg-muted/50">
                        <TableCell className="py-2 font-semibold">合计</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentSuppliersTableTotals.group_count)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentSuppliersTableTotals.goods_count)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentSuppliersTableTotals.ticket_count)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentSuppliersTableTotals.sales_qty)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.sales_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.sales_revenue)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.sales_cost)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.sales_cost_adjustment)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.supplier_discount)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentSuppliersTableTotals.gross_profit)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{percentRatio(departmentSuppliersMarginTotal)}%</TableCell>
                      </TableRow>
                    </TableFooter>
                  )}
                </Table>
              ) : (
                <Table className="min-w-[1900px] table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[260px] whitespace-nowrap">商品</TableHead>
                      <TableHead className="w-[220px] whitespace-nowrap">柜组</TableHead>
                      <TableHead className="w-[220px] whitespace-nowrap">类别/品牌</TableHead>
                      <TableHead className="w-[260px] whitespace-nowrap">供应商</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap">经营方式</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">小票数</TableHead>
                      <TableHead className="w-[100px] whitespace-nowrap text-right">销售数量</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售金额</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售收入</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">销售成本</TableHead>
                      <TableHead className="w-[110px] whitespace-nowrap text-right">成本调整</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">供应商折扣</TableHead>
                      <TableHead className="w-[120px] whitespace-nowrap text-right">毛利</TableHead>
                      <TableHead className="w-[90px] whitespace-nowrap text-right">毛利率</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {departmentGoodsInitialLoading || departmentGoodsQuery.isError || (departmentGoodsQuery.data ?? []).length === 0 ? (
                      <TableStatusRow
                        colSpan={14}
                        loading={departmentGoodsInitialLoading}
                        emptyText={salesTableStatusText(departmentGoodsQuery.error, "当前筛选条件下暂无商品销售明细。")}
                      />
                    ) : (
                      (departmentGoodsQuery.data ?? []).map((row) => (
                        <TableRow
                          key={`${row.group_code}-${row.goods_code}-${row.barcode}-${row.supplier_code}-${row.operation_method}`}
                          className="cursor-pointer hover:bg-slate-50"
                          onClick={() => drillToDepartmentProduct(row)}
                        >
                          <TableCell className="py-2">
                            <div className="truncate font-medium" title={row.goods_name || row.goods_code}>{row.goods_name || row.goods_code}</div>
                            <div className="text-xs text-slate-500">{row.goods_code}{row.barcode ? ` / ${row.barcode}` : ""}</div>
                          </TableCell>
                          <TableCell className="py-2">
                            <div className="truncate" title={row.group_name || row.group_code || "-"}>{row.group_name || row.group_code || "-"}</div>
                            <div className="text-xs text-slate-500">{row.group_code || ""}</div>
                          </TableCell>
                          <TableCell className="py-2">
                            <div className="truncate" title={row.category_name || row.category_code || "-"}>{row.category_name || row.category_code || "-"}</div>
                            <div className="truncate text-xs text-slate-500" title={row.brand_name || row.brand_code || ""}>{row.brand_name || row.brand_code || ""}</div>
                          </TableCell>
                          <TableCell className="py-2">
                            <div className="truncate" title={row.supplier_name || row.supplier_code || "-"}>{row.supplier_name || row.supplier_code || "-"}</div>
                            <div className="text-xs text-slate-500">{row.supplier_code || ""}</div>
                          </TableCell>
                          <TableCell className="whitespace-nowrap py-2">{row.operation_method || "-"}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.ticket_count)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{number(row.sales_qty)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_amount)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_revenue)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_cost)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.sales_cost_adjustment)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.supplier_discount)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{money(row.gross_profit)}</TableCell>
                          <TableCell className="whitespace-nowrap py-2 text-right tabular-nums">{percentRatio(row.gross_margin_rate)}%</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                  {!departmentGoodsQuery.isError && (departmentGoodsQuery.data ?? []).length > 0 && (
                    <TableFooter>
                      <TableRow className="hover:bg-muted/50">
                        <TableCell className="py-2 font-semibold" colSpan={5}>合计</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentGoodsTableTotals.ticket_count)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{number(departmentGoodsTableTotals.sales_qty)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.sales_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.sales_revenue)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.sales_cost)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.sales_cost_adjustment)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.supplier_discount)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{money(departmentGoodsTableTotals.gross_profit)}</TableCell>
                        <TableCell className="whitespace-nowrap py-2 text-right font-semibold tabular-nums">{percentRatio(departmentGoodsMarginTotal)}%</TableCell>
                      </TableRow>
                    </TableFooter>
                  )}
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="groups">
          <Card>
            <CardHeader className="flex flex-col gap-3 py-3 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle>柜组销售汇总</CardTitle>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {selectedStore && <Badge variant="outline">{selectedStore.store_name || selectedStore.store_id}</Badge>}
                  {selectedDepartment && <Badge variant="outline">{selectedDepartment.department_name}</Badge>}
                  {selectedDepartment && (
                    <Button variant="ghost" size="sm" onClick={() => { setSelectedGroup(null); setActiveTab("departments"); }}>
                      返回部门
                    </Button>
                  )}
                  {selectedStore && (
                    <Button variant="ghost" size="sm" onClick={backToStores}>
                      返回门店
                    </Button>
                  )}
                </div>
              </div>
              <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center md:w-auto">
                <Input className="max-w-xs" placeholder="搜索柜组编码/名称" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={handleAnalyzeGroups}
                  disabled={analysisLoading || groupsQuery.isFetching}
                  aria-busy={analysisLoading}
                >
                  {analysisLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="mr-2 h-4 w-4" />
                  )}
                  {analysisLoading ? "分析中…" : "AI 分析"}
                </Button>
                <Button type="button" variant="outline" size="sm" className="shrink-0" onClick={handleExportGroups}>
                  <Download className="mr-2 h-4 w-4" />
                  导出 Excel
                </Button>
              </div>
            </CardHeader>
            <CardContent className="pb-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>柜组</TableHead>
                    {showPricedSalesAmount && <TableHead className="text-right">零售价</TableHead>}
                    <TableHead className="text-right">本期销售收入</TableHead>
                    <TableHead className="text-right">同期销售收入</TableHead>
                    <TableHead className="text-right">销售收入同比</TableHead>
                    <TableHead className="text-right">毛利</TableHead>
                    <TableHead className="text-right">同期毛利</TableHead>
                    <TableHead className="text-right">本期毛利率</TableHead>
                    <TableHead className="text-right">同期毛利率</TableHead>
                    <TableHead className="text-right">同期小票数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groupsInitialLoading || groupsQuery.isError || (groupsQuery.data ?? []).length === 0 ? (
                    <TableStatusRow
                      colSpan={showPricedSalesAmount ? 10 : 9}
                      loading={groupsInitialLoading}
                      emptyText={salesTableStatusText(groupsQuery.error, "当前筛选条件下暂无柜组销售数据。")}
                    />
                  ) : (
                    (groupsQuery.data ?? []).map((row) => (
                      <TableRow key={row.group_code} className="cursor-pointer hover:bg-slate-50" onClick={() => drillToGroup(row)}>
                        <TableCell className="py-2">
                          <div className="font-medium">{row.group_name || row.group_code}</div>
                          <div className="text-xs text-slate-500">{row.group_code}</div>
                        </TableCell>
                        {showPricedSalesAmount && (
                          <TableCell className="py-2 text-right">{money(row.priced_sales_amount)}</TableCell>
                        )}
                        <TableCell className="py-2 text-right">{money(row.effective_sales)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_effective_sales)}</TableCell>
                        <SalesYoYTableCell effectiveSales={Number(row.effective_sales)} samePeriodSales={Number(row.same_period_effective_sales ?? 0)} />
                        <TableCell className="py-2 text-right">{money(row.net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{money(row.same_period_net_profit)}</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.ticket_margin ?? row.net_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">{percentRatio(row.same_period_margin)}%</TableCell>
                        <TableCell className="py-2 text-right">
                          {Number(row.same_period_ticket_count ?? 0) > 0 ? (
                            <button
                              type="button"
                              className="font-medium text-blue-600 underline-offset-2 hover:underline"
                              onClick={(e) => openPriorPeriodTickets(e, row)}
                            >
                              {number(row.same_period_ticket_count)}
                            </button>
                          ) : (
                            <span className="tabular-nums text-slate-600">{number(row.same_period_ticket_count)}</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
                {!groupsQuery.isError && (groupsQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold">合计</TableCell>
                      {showPricedSalesAmount && (
                        <TableCell className="py-2 text-right font-semibold tabular-nums">
                          {money(groupsTableTotals.priced_sales_amount)}
                        </TableCell>
                      )}
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(groupsTableTotals.effective_sales)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(groupsTableTotals.same_period_effective_sales)}</TableCell>
                      <SalesYoYTableCell
                        footer
                        effectiveSales={groupsTableTotals.effective_sales}
                        samePeriodSales={groupsTableTotals.same_period_effective_sales}
                      />
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(groupsTableTotals.net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(groupsTableTotals.same_period_net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(groupsTableTotals.ticket_margin)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(groupsTableTotals.same_period_margin)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(groupsTableTotals.same_period_ticket_count)}</TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tickets">
          <Card>
            <CardHeader className="flex flex-col gap-3 py-3 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0 flex-1">
                <CardTitle>
                  {selectedGroup ? `${selectedGroup.group_name || selectedGroup.group_code} 小票` : "小票"}
                  {ticketsViewMode === "prior" && (
                    <span className="ml-2 text-base font-normal text-amber-700">（上年同期明细）</span>
                  )}
                  {selectedDepartmentProduct && (
                    <span className="ml-2 text-base font-normal text-slate-600">
                      · {selectedDepartmentProduct.goods_name || selectedDepartmentProduct.goods_code}
                    </span>
                  )}
                </CardTitle>
                {selectedGroup && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{selectedGroup.group_code}</Badge>
                    {selectedDepartmentProduct && (
                      <Badge variant="secondary" className="font-normal">
                        商品 {selectedDepartmentProduct.goods_code}
                      </Badge>
                    )}
                    {ticketsViewMode === "prior" && (
                      <Badge variant="secondary" className="font-normal">
                        {priorStartDate} ~ {priorEndDate}
                      </Badge>
                    )}
                    {ticketsViewMode === "prior" && (
                      <Button variant="outline" size="sm" onClick={() => setTicketsViewMode("current")}>
                        查看本期小票
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={backFromTickets}>
                      {selectedDepartmentProduct && isSupermarketDepartment(selectedDepartment) ? "返回商品" : "返回柜组"}
                    </Button>
                  </div>
                )}
              </div>
              {selectedGroup && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={handleExportTickets}
                  disabled={ticketsExporting}
                >
                  {ticketsExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                  {ticketsExporting ? "导出中…" : "导出 Excel"}
                </Button>
              )}
            </CardHeader>
            <CardContent className="pb-3">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>单据号</TableHead>
                    <TableHead>日期</TableHead>
                    <TableHead>销售类型</TableHead>
                    <TableHead>收银机号</TableHead>
                    <TableHead>小票号</TableHead>
                    {showPricedSalesAmount && <TableHead className="text-right">零售价</TableHead>}
                    <TableHead className="text-right">销售收入</TableHead>
                    <TableHead className="text-right">毛利</TableHead>
                    <TableHead className="text-right">毛利率</TableHead>
                    <TableHead className="text-right">授权折扣</TableHead>
                    <TableHead className="text-right">面值卡(MZK)</TableHead>
                    <TableHead className="text-right">礼券(LQ)</TableHead>
                    <TableHead className="text-right">消费加积分</TableHead>
                    <TableHead className="text-right">生日月会员加积分</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ticketsInitialLoading || ticketsQuery.isError || (ticketsQuery.data ?? []).length === 0 ? (
                    <TableStatusRow
                      colSpan={showPricedSalesAmount ? 14 : 13}
                      loading={ticketsInitialLoading}
                      emptyText={salesTableStatusText(
                        ticketsQuery.error,
                        selectedGroup
                          ? `${ticketsViewMode === "prior" ? "同期" : "本期"}区间暂无小票数据。`
                          : "请先选择柜组查看小票。",
                      )}
                    />
                  ) : (
                    (ticketsQuery.data ?? []).map((row) => (
                      <TableRow key={`${row.billno}`} className="cursor-pointer hover:bg-slate-50" onClick={() => openTicketDetail(row)}>
                        <TableCell className="py-2 font-medium">{row.billno}</TableCell>
                        <TableCell className="py-2 whitespace-nowrap">
                          {formatTicketSaleDateTime(row.sale_datetime, row.sale_date)}
                        </TableCell>
                        <TableCell className="py-2">{row.transaction_type?.trim() || "-"}</TableCell>
                        <TableCell className="py-2">{row.cash_register_no || "-"}</TableCell>
                        <TableCell className="py-2">{row.invoice_no || "-"}</TableCell>
                        {showPricedSalesAmount && (
                          <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">
                            {money(row.priced_sales_amount)}
                          </TableCell>
                        )}
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.effective_sales)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.net_profit)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{percentRatio(row.ticket_margin)}%</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.authorized_discount)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.mzk)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.lq)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{number(row.consumption_point)}</TableCell>
                        <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{number(row.birthday_month_member_point)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
                {!ticketsQuery.isError && (ticketsQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold" colSpan={5}>
                        本页合计
                      </TableCell>
                      {showPricedSalesAmount && (
                        <TableCell className="py-2 text-right font-semibold tabular-nums">
                          {money(ticketsTableTotals.priced_sales_amount)}
                        </TableCell>
                      )}
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(ticketsTableTotals.effective_sales)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(ticketsTableTotals.net_profit)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{percentRatio(ticketsTableMarginTotal)}%</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(ticketsTableTotals.authorized_discount)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(ticketsTableTotals.mzk)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{money(ticketsTableTotals.lq)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(ticketsTableTotals.consumption_point)}</TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(ticketsTableTotals.birthday_month_member_point)}</TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
              {!ticketsQuery.isError && ticketTotalCount > 0 && (
                <div className="mt-3 flex flex-col gap-2 border-t pt-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    共 <span className="font-semibold text-slate-900">{number(ticketTotalCount)}</span> 张小票，
                    每页 {TICKET_PAGE_SIZE} 张；当前第 {ticketPage} / {ticketTotalPages} 页
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={ticketPage <= 1 || ticketsQuery.isFetching}
                      onClick={() => setTicketPage((page) => Math.max(1, page - 1))}
                    >
                      上一页
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={ticketPage >= ticketTotalPages || ticketsQuery.isFetching}
                      onClick={() => setTicketPage((page) => Math.min(ticketTotalPages, page + 1))}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={analysisOpen} onOpenChange={setAnalysisOpen}>
        <DialogContent className="max-h-[85vh] max-w-5xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600" />
              柜组 AI 分析
            </DialogTitle>
          </DialogHeader>
          {analysisLoading ? (
            <div className="flex min-h-48 items-center justify-center gap-3 text-sm text-slate-600">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
              正在分析当前柜组数据…
            </div>
          ) : analysisResult ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant="outline">{currentStartDate} ~ {currentEndDate}</Badge>
                <Badge variant="outline">同期 {priorStartDate} ~ {priorEndDate}</Badge>
                {selectedStore && <Badge variant="secondary">{selectedStore.store_name || selectedStore.store_id}</Badge>}
                {selectedDepartment && <Badge variant="secondary">{selectedDepartment.department_name}</Badge>}
                {keyword.trim() && <Badge variant="outline">搜索：{keyword.trim()}</Badge>}
              </div>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">销售收入</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">{money(analysisResult.summary.sales)}</div>
                </div>
                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">销售同比</div>
                  <div className={cn("mt-1 text-lg font-semibold tabular-nums", rateColorClass(analysisResult.summary.sales_yoy_rate))}>
                    {formatSalesYoYPercent(
                      analysisResult.summary.sales_yoy_rate == null ? null : analysisResult.summary.sales_yoy_rate * 100,
                    )}
                  </div>
                </div>
                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">净毛利</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">{money(analysisResult.summary.net_profit)}</div>
                </div>
                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="text-xs text-slate-500">综合毛利率</div>
                  <div className="mt-1 text-lg font-semibold tabular-nums">{percentRatio(analysisResult.summary.margin)}%</div>
                </div>
              </div>

              <section className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-base font-semibold text-slate-900">AI 报告</h3>
                  {analysisResult.ai?.provider && (
                    <span className="text-xs text-slate-500">
                      {analysisResult.ai.provider} / {analysisResult.ai.model || "-"}
                    </span>
                  )}
                </div>
                {analysisResult.ai?.report ? (
                  <div className="whitespace-pre-wrap rounded border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-800">
                    {analysisResult.ai.report}
                  </div>
                ) : (
                  <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {analysisResult.ai?.error || "AI 报告暂不可用，已展示规则分析结果。"}
                  </div>
                )}
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-slate-900">异常柜组</h3>
                {analysisResult.anomalies.length > 0 ? (
                  <div className="space-y-2">
                    {analysisResult.anomalies.slice(0, 12).map((item, index) => (
                      <div key={`${item.rule_id}-${item.group_code}-${index}`} className="rounded border border-slate-200 bg-white px-3 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="outline" className={severityBadgeClass(item.severity)}>
                            {severityLabel(item.severity)}
                          </Badge>
                          <span className="font-medium text-slate-900">{item.group_name || item.group_code}</span>
                          <span className="text-xs text-slate-500">{item.rule_id} · {item.title}</span>
                        </div>
                        <div className="mt-1 text-sm leading-6 text-slate-700">{item.message}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    当前阈值下暂无明显异常。
                  </div>
                )}
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-slate-900">建议动作</h3>
                <div className="grid gap-2 md:grid-cols-2">
                  {analysisResult.actions.map((item, index) => (
                    <div key={`${item.title}-${index}`} className="rounded border border-slate-200 bg-slate-50 px-3 py-2">
                      <div className="font-medium text-slate-900">{item.title}</div>
                      <div className="mt-1 text-sm leading-6 text-slate-600">{item.description}</div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : (
            <div className="rounded border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              点击“AI 分析”生成当前柜组范围的分析结果。
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(selectedBillno)} onOpenChange={(open) => !open && setSelectedBillno(null)}>
        <DialogContent className="max-h-[85vh] max-w-5xl overflow-y-auto">
          <DialogHeader><DialogTitle>小票详情 {selectedBillno}</DialogTitle></DialogHeader>
          {ticketDetailQuery.isLoading ? (
            <div className="flex items-center justify-center gap-2 rounded border border-slate-200 bg-slate-50 px-4 py-8 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              小票详情加载中…
            </div>
          ) : ticketDetailQuery.isError ? (
            <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              小票详情加载失败，请稍后重试。
            </div>
          ) : (
            <div className="space-y-4">
            <ReceiptTicketHeaderBlock
              source={ticketDetailQuery.data?.source || "-"}
              head={ticketDetailQuery.data?.head ?? null}
              fallbackFirstRow={ticketDetailQuery.data?.goods?.[0]}
            />
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>商品</TableHead>
                  <TableHead>柜组</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead className="text-right">成本</TableHead>
                  <TableHead className="text-right">毛利</TableHead>
                  <TableHead className="text-right">折扣</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(ticketDetailQuery.data?.goods ?? []).map((row, index) => {
                  const productDisplay = getReceiptProductDisplay(row);
                  return (
                    <TableRow key={index}>
                      <TableCell className="py-2">
                        <div className="font-medium">{productDisplay.name}</div>
                        {productDisplay.identifiers.map((identifier) => (
                          <div key={identifier} className="text-xs text-slate-500">{identifier}</div>
                        ))}
                      </TableCell>
                      <TableCell className="py-2">{String(row.group_code || "-")}</TableCell>
                      <TableCell className="py-2 text-right">{number(Number(row.sl ?? row.quantity ?? 0))}</TableCell>
                      <TableCell className="py-2 text-right">{money(Number(row.hjje ?? row.effective_sales ?? 0))}</TableCell>
                      <TableCell className="py-2 text-right">{money(Number(row.cost_amount ?? 0))}</TableCell>
                      <TableCell className="py-2 text-right">{money(Number(row.net_profit ?? 0))}</TableCell>
                      <TableCell className="py-2 text-right">{money(Number(row.hjzk ?? 0))}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            {(ticketDetailQuery.data?.payments?.length ?? 0) > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>付款方式</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead className="text-right">金额</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ticketDetailQuery.data?.payments.map((row, index) => (
                    <TableRow key={index}>
                      <TableCell>{String(row.payname || row.paycode || "-")}</TableCell>
                      <TableCell>{String(row.paytype || row.flag || "-")}</TableCell>
                      <TableCell className="text-right">{money(Number(row.je || 0))}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
