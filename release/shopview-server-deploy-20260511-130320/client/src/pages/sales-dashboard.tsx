import { useMemo, useState, type MouseEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Building2, ChevronRight, Download, FileText, Loader2, RefreshCw, Search, Sparkles } from "lucide-react";
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
  exportDepartmentsToExcel,
  exportGroupsToExcel,
  exportStoresToExcel,
  exportTicketsToExcel,
} from "@/lib/export-sales-excel";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

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

type TicketSummary = {
  billno: string | number;
  sale_date?: string | null;
  sale_datetime?: string | null;
  invoice_no?: string | number | null;
  cashier?: string | null;
  line_count: number;
  /** 商品件数：salegoodslist 汇总 sglsl */
  quantity: number;
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
  /** 礼券 LQ：sum(sglgcert)-sum(sgltimes) */
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
  const [keyword, setKeyword] = useState("");
  const [selectedStore, setSelectedStore] = useState<StoreSummary | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentSummary | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<GroupSummary | null>(null);
  const [selectedBillno, setSelectedBillno] = useState<string | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<SalesAnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  /** 小票列表用本期日期或上年同期日期（与「同期小票数」下钻一致） */
  const [ticketsViewMode, setTicketsViewMode] = useState<"current" | "prior">("current");

  const commonParams = useMemo(
    () => ({
      start_date: currentStartDate,
      end_date: currentEndDate,
      prior_start_date: priorStartDate,
      prior_end_date: priorEndDate,
    }),
    [currentStartDate, currentEndDate, priorStartDate, priorEndDate],
  );
  const ticketsQueryParams = useMemo(() => {
    if (ticketsViewMode === "prior") {
      return { start_date: priorStartDate, end_date: priorEndDate };
    }
    return { start_date: currentStartDate, end_date: currentEndDate };
  }, [ticketsViewMode, currentStartDate, currentEndDate, priorStartDate, priorEndDate]);

  const syncPriorRangeFromCurrent = (start: string, end: string) => {
    const r = priorYearRange(start, end);
    if (r) {
      setPriorStartDate(r.start_date);
      setPriorEndDate(r.end_date);
    }
  };

  const storesQuery = useQuery<StoreSummary[]>({
    queryKey: ["/api/sales/summary/stores", commonParams],
    queryFn: () => apiGet(`/api/sales/summary/stores${buildQuery(commonParams)}`),
  });

  const departmentsQuery = useQuery<DepartmentSummary[]>({
    queryKey: ["/api/sales/summary/departments", commonParams, selectedStore?.store_id],
    queryFn: () =>
      apiGet(
        `/api/sales/summary/departments${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
        })}`,
      ),
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
      apiGet(
        `/api/sales/summary/groups${buildQuery({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: groupsUnassigned ? undefined : selectedDepartment?.department_code,
          unassigned_department: groupsUnassigned ? true : undefined,
          keyword,
        })}`,
      ),
  });

  const ticketsQuery = useQuery<TicketSummary[]>({
    queryKey: ["/api/sales/groups/tickets", selectedGroup?.group_code, ticketsQueryParams, ticketsViewMode],
    queryFn: () =>
      apiGet(`/api/sales/groups/${encodeURIComponent(selectedGroup?.group_code ?? "")}/tickets${buildQuery(ticketsQueryParams)}`),
    enabled: Boolean(selectedGroup?.group_code),
  });

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
      ticketsQuery.isFetching ||
      (Boolean(selectedBillno) && ticketDetailQuery.isFetching),
    [
      storesQuery.isFetching,
      departmentsQuery.isFetching,
      groupsQuery.isFetching,
      ticketsQuery.isFetching,
      selectedBillno,
      ticketDetailQuery.isFetching,
    ],
  );

  /** 与当前 Tab、日期及下钻一致：各 Tab 对应当前列表数据；门店 Tab 且在面包屑中选中了门店时只统计该门店一行 */
  const totals = useMemo(() => {
    const empty = { sales: 0, profit: 0, tickets: 0, groups: 0 };
    if (activeTab === "tickets") {
      const rows = ticketsQuery.data ?? [];
      return rows.reduce(
        (acc, row) => ({
          sales: acc.sales + Number(row.effective_sales || 0),
          profit: acc.profit + Number(row.net_profit || 0),
          tickets: acc.tickets + 1,
          groups: 1,
        }),
        { ...empty },
      );
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
  }, [activeTab, selectedStore, storesQuery.data, departmentsQuery.data, groupsQuery.data, ticketsQuery.data]);

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
        effective_sales: acc.effective_sales + Number(row.effective_sales || 0),
        net_profit: acc.net_profit + Number(row.net_profit || 0),
        same_period_ticket_count: acc.same_period_ticket_count + Number(row.same_period_ticket_count || 0),
        same_period_effective_sales: acc.same_period_effective_sales + Number(row.same_period_effective_sales || 0),
        same_period_net_profit: acc.same_period_net_profit + Number(row.same_period_net_profit || 0),
      }),
      {
        ticket_count: 0,
        quantity: 0,
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

  const ticketsTableTotals = useMemo(() => {
    const rows = ticketsQuery.data ?? [];
    return rows.reduce(
      (acc, row) => ({
        quantity: acc.quantity + Number(row.quantity || 0),
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
        quantity: 0,
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

  const refresh = () => {
    storesQuery.refetch();
    departmentsQuery.refetch();
    groupsQuery.refetch();
    ticketsQuery.refetch();
    ticketDetailQuery.refetch();
  };

  const drillToStore = (store: StoreSummary) => {
    setSelectedStore(store);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setActiveTab("departments");
  };

  const drillToDepartment = (department: DepartmentSummary) => {
    setSelectedDepartment(department);
    setSelectedGroup(null);
    setActiveTab("groups");
  };

  const drillToGroup = (group: GroupSummary) => {
    setSelectedGroup(group);
    setTicketsViewMode("current");
    setActiveTab("tickets");
  };

  const openPriorPeriodTickets = (event: MouseEvent, group: GroupSummary) => {
    event.stopPropagation();
    if (!Number(group.same_period_ticket_count ?? 0)) return;
    setSelectedGroup(group);
    setTicketsViewMode("prior");
    setActiveTab("tickets");
  };

  const resetDrilldown = () => {
    setSelectedStore(null);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setTicketsViewMode("current");
    setActiveTab("stores");
  };

  const backToStores = () => {
    setSelectedStore(null);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setTicketsViewMode("current");
    setActiveTab("stores");
  };

  const backToGroups = () => {
    setSelectedGroup(null);
    setTicketsViewMode("current");
    setActiveTab("groups");
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
      exportGroupsToExcel(rows, currentStartDate, currentEndDate);
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

  const handleExportTickets = () => {
    if (!selectedGroup?.group_code) {
      toast({ title: "请先选择柜组并打开小票列表", variant: "destructive" });
      return;
    }
    const rows = ticketsQuery.data ?? [];
    if (rows.length === 0) {
      toast({ title: "暂无小票数据可导出", variant: "destructive" });
      return;
    }
    try {
      exportTicketsToExcel(rows, {
        startDate: ticketsQueryParams.start_date,
        endDate: ticketsQueryParams.end_date,
        groupCode: selectedGroup.group_code,
        groupName: selectedGroup.group_name,
        viewMode: ticketsViewMode,
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

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
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
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label htmlFor="sales-current-start">本期开始日期</Label>
            <Input
              id="sales-current-start"
              type="date"
              value={currentStartDate}
              onChange={(event) => {
                const v = event.target.value;
                setCurrentStartDate(v);
                syncPriorRangeFromCurrent(v, currentEndDate);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-current-end">本期结束日期</Label>
            <Input
              id="sales-current-end"
              type="date"
              value={currentEndDate}
              onChange={(event) => {
                const v = event.target.value;
                setCurrentEndDate(v);
                syncPriorRangeFromCurrent(currentStartDate, v);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-prior-start">同期开始日期</Label>
            <Input
              id="sales-prior-start"
              type="date"
              value={priorStartDate}
              onChange={(event) => setPriorStartDate(event.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sales-prior-end">同期结束日期</Label>
            <Input
              id="sales-prior-end"
              type="date"
              value={priorEndDate}
              onChange={(event) => setPriorEndDate(event.target.value)}
            />
          </div>
          <Button
            variant="outline"
            onClick={refresh}
            disabled={salesDataFetching}
            aria-busy={salesDataFetching}
          >
            <RefreshCw className={cn("mr-2 h-4 w-4", salesDataFetching && "animate-spin")} />
            {salesDataFetching ? "刷新中…" : "刷新"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">销售收入</CardTitle></CardHeader>
          <CardContent className="py-3"><div className="text-2xl font-semibold">{money(totals.sales)}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">净毛利</CardTitle></CardHeader>
          <CardContent className="py-3"><div className="text-2xl font-semibold">{money(totals.profit)}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">小票数</CardTitle></CardHeader>
          <CardContent className="py-3"><div className="text-2xl font-semibold">{number(totals.tickets)}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">柜组数</CardTitle></CardHeader>
          <CardContent className="py-3"><div className="text-2xl font-semibold">{number(totals.groups)}</div></CardContent>
        </Card>
      </div>

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
            <button className="font-medium text-slate-900 hover:text-blue-700" onClick={() => setActiveTab("groups")}>
              {selectedDepartment.department_name}
            </button>
          </>
        )}
        {selectedGroup && (
          <>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <button className="font-medium text-slate-900 hover:text-blue-700" onClick={() => setActiveTab("tickets")}>
              {selectedGroup.group_name || selectedGroup.group_code}
            </button>
          </>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="stores"><Building2 className="mr-2 h-4 w-4" />门店</TabsTrigger>
          <TabsTrigger value="departments"><BarChart3 className="mr-2 h-4 w-4" />部门</TabsTrigger>
          <TabsTrigger value="groups"><Search className="mr-2 h-4 w-4" />柜组</TabsTrigger>
          <TabsTrigger value="tickets" disabled={!selectedGroup}><FileText className="mr-2 h-4 w-4" />小票</TabsTrigger>
        </TabsList>

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
                  {(storesQuery.data ?? []).map((row) => (
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
                  ))}
                </TableBody>
                {(storesQuery.data ?? []).length > 0 && (
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
                  {(departmentsQuery.data ?? []).map((row) => (
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
                  ))}
                </TableBody>
                {(departmentsQuery.data ?? []).length > 0 && (
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
                  {(groupsQuery.data ?? []).map((row) => (
                    <TableRow key={row.group_code} className="cursor-pointer hover:bg-slate-50" onClick={() => drillToGroup(row)}>
                      <TableCell className="py-2">
                        <div className="font-medium">{row.group_name || row.group_code}</div>
                        <div className="text-xs text-slate-500">{row.group_code}</div>
                      </TableCell>
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
                  ))}
                </TableBody>
                {(groupsQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold">合计</TableCell>
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
                </CardTitle>
                {selectedGroup && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{selectedGroup.group_code}</Badge>
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
                    <Button variant="ghost" size="sm" onClick={backToGroups}>
                      返回柜组
                    </Button>
                  </div>
                )}
              </div>
              {selectedGroup && (
                <Button type="button" variant="outline" size="sm" className="shrink-0" onClick={handleExportTickets}>
                  <Download className="mr-2 h-4 w-4" />
                  导出 Excel
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
                    <TableHead>小票号</TableHead>
                    <TableHead>收银员</TableHead>
                    <TableHead className="text-right">商品数</TableHead>
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
                  {(ticketsQuery.data ?? []).map((row) => (
                    <TableRow key={`${row.billno}`} className="cursor-pointer hover:bg-slate-50" onClick={() => setSelectedBillno(`${row.billno}`)}>
                      <TableCell className="py-2 font-medium">{row.billno}</TableCell>
                      <TableCell className="py-2">{row.sale_datetime || row.sale_date || "-"}</TableCell>
                      <TableCell className="py-2">{row.transaction_type?.trim() || "-"}</TableCell>
                      <TableCell className="py-2">{row.invoice_no || "-"}</TableCell>
                      <TableCell className="py-2">{row.cashier || "-"}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{number(row.quantity)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.effective_sales)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.net_profit)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{percentRatio(row.ticket_margin)}%</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.authorized_discount)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.mzk)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{money(row.lq)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{number(row.consumption_point)}</TableCell>
                      <TableCell className="py-2 text-right whitespace-nowrap tabular-nums">{number(row.birthday_month_member_point)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                {(ticketsQuery.data ?? []).length > 0 && (
                  <TableFooter>
                    <TableRow className="hover:bg-muted/50">
                      <TableCell className="py-2 font-semibold" colSpan={5}>
                        合计
                      </TableCell>
                      <TableCell className="py-2 text-right font-semibold tabular-nums">{number(ticketsTableTotals.quantity)}</TableCell>
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
                {(ticketDetailQuery.data?.goods ?? []).map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="py-2">
                      <div className="font-medium">{String(row.name || row.goods_name || row.goods_code || "-")}</div>
                      <div className="text-xs text-slate-500">{String(row.barcode || row.code || "")}</div>
                    </TableCell>
                    <TableCell className="py-2">{String(row.group_code || "-")}</TableCell>
                    <TableCell className="py-2 text-right">{number(Number(row.sl ?? row.quantity ?? 0))}</TableCell>
                    <TableCell className="py-2 text-right">{money(Number(row.hjje ?? row.effective_sales ?? 0))}</TableCell>
                    <TableCell className="py-2 text-right">{money(Number(row.cost_amount ?? 0))}</TableCell>
                    <TableCell className="py-2 text-right">{money(Number(row.net_profit ?? 0))}</TableCell>
                    <TableCell className="py-2 text-right">{money(Number(row.hjzk ?? 0))}</TableCell>
                  </TableRow>
                ))}
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
        </DialogContent>
      </Dialog>
    </div>
  );
}
