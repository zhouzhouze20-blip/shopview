import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  ChevronRight,
  FileText,
  Home,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useLocation } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import { apiGet } from "@/lib/api";
import { canAccessModule } from "@/lib/module-permissions";
import { buildMobileSalesDatePresets } from "@/lib/mobile-sales-date-presets";
import {
  buildProductTicketParams,
  getReceiptProductDisplay,
  isCosmeticsRetailPriceScope,
  isSupermarketDepartment,
} from "@/lib/sales-dashboard-drilldown";
import {
  getSalesDashboardData,
  isSalesDashboardTimeoutError,
  validateSalesDashboardDateRanges,
} from "@/lib/sales-dashboard-request";

type MobileLevel = "stores" | "departments" | "groups" | "department-products" | "tickets";
type DepartmentProductView = "goods" | "suppliers";

type StoreSummary = {
  store_id: string;
  store_name: string;
  department_count: number;
  group_count: number;
  ticket_count: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
};

type DepartmentSummary = {
  department_code: string;
  department_name: string;
  group_count: number;
  ticket_count: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
};

type GroupSummary = {
  group_code: string;
  group_name?: string | null;
  ticket_count: number;
  priced_sales_amount: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
  net_margin: number;
  same_period_effective_sales?: number;
  same_period_net_profit?: number;
};

type DepartmentGoodsSummary = {
  group_code?: string | null;
  group_name?: string | null;
  goods_code: string;
  barcode?: string | null;
  goods_name?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  operation_method?: string | null;
  ticket_count: number;
  sales_qty: number;
  sales_revenue: number;
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
  sales_revenue: number;
  gross_profit: number;
  gross_margin_rate: number;
};

type TicketSummary = {
  billno: string | number;
  sale_date?: string | null;
  sale_datetime?: string | null;
  cash_register_no?: string | null;
  invoice_no?: string | number | null;
  transaction_type?: string | null;
  quantity: number;
  priced_sales_amount: number;
  effective_sales: number;
  net_profit: number;
  ticket_margin: number;
};

type TicketDetail = {
  source: string;
  head: Record<string, unknown> | null;
  goods: Array<Record<string, unknown>>;
  payments: Array<Record<string, unknown>>;
};

const currency = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

const decimal = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

const tenThousands = (value?: number | null) => `${(Number(value || 0) / 10_000).toFixed(2)}万`;

const percent = (value?: number | null) => `${(Number(value || 0) * 100).toFixed(2)}%`;

function yoyPercent(current?: number | null, prior?: number | null): number | null {
  const baseline = Number(prior || 0);
  if (!(baseline > 0)) return null;
  return ((Number(current || 0) - baseline) / baseline) * 100;
}

function formatYoy(current?: number | null, prior?: number | null): string {
  const value = yoyPercent(current, prior);
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function yoyClass(current?: number | null, prior?: number | null): string {
  const value = yoyPercent(current, prior);
  if (value == null || value === 0) return "text-slate-500";
  return value > 0 ? "text-red-600" : "text-emerald-600";
}

function todayString(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function shiftYear(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  const candidate = new Date(year - 1, month - 1, day);
  if (candidate.getMonth() !== month - 1) candidate.setDate(0);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${candidate.getFullYear()}-${pad(candidate.getMonth() + 1)}-${pad(candidate.getDate())}`;
}

function queryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || `${value}`.trim() === "") continue;
    search.set(key, `${value}`);
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function isUnassignedDepartment(row: DepartmentSummary): boolean {
  return !String(row.department_code || "").trim();
}

function OverviewMetric({
  label,
  value,
  priorLabel,
  priorValue,
  yoyLabel,
  current,
  prior,
  hasError,
}: {
  label: string;
  value: string;
  priorLabel: string;
  priorValue: string;
  yoyLabel: string;
  current: number;
  prior: number | null;
  hasError: boolean;
}) {
  const yoyUnavailable = hasError || prior == null;
  return (
    <div className="min-w-0 px-3 py-2.5">
      <div className="text-[10px] leading-4 text-slate-500">{label}</div>
      <div className="whitespace-nowrap text-lg font-semibold leading-6 tabular-nums tracking-tight text-slate-950">{value}</div>
      <div className="mt-1 grid grid-cols-2 gap-2">
        <div className="min-w-0 text-[9px] leading-3 text-slate-400">
          <div>{priorLabel}</div>
          <div className="whitespace-nowrap font-medium tabular-nums text-slate-600">{priorValue}</div>
        </div>
        <div className="min-w-0 text-right text-[9px] leading-3 text-slate-400">
          <div>{yoyLabel}</div>
          <div className={`whitespace-nowrap font-semibold tabular-nums ${yoyUnavailable ? "text-slate-500" : yoyClass(current, prior)}`}>
            {yoyUnavailable ? "—" : formatYoy(current, prior)}
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ loading, error, label }: { loading: boolean; error: unknown; label: string }) {
  if (loading) {
    return (
      <div className="flex min-h-40 items-center justify-center gap-2 text-sm text-blue-700">
        <Loader2 className="h-5 w-5 animate-spin" /> 正在查询销售数据…
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
        {isSalesDashboardTimeoutError(error)
          ? "查询超时，本次没有返回数据，页面不会把它当成 0。请缩短日期范围后重试。"
          : "销售数据加载失败，请稍后重试。"}
      </div>
    );
  }
  return <div className="py-14 text-center text-sm text-slate-500">{label}</div>;
}

function SummaryRow({
  title,
  code,
  sales,
  priorSales,
  profit,
  priorProfit,
  margin,
  tickets,
  pricedSalesAmount,
  showPricedSalesAmount = false,
  dense = false,
  onClick,
}: {
  title: string;
  code?: string;
  sales: number;
  priorSales?: number;
  profit: number;
  priorProfit?: number;
  margin: number;
  tickets: number;
  pricedSalesAmount?: number;
  showPricedSalesAmount?: boolean;
  dense?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border border-slate-200 bg-white text-left shadow-sm transition active:scale-[0.99] active:bg-slate-50 ${dense ? "px-2.5 py-2" : "px-3 py-2.5"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-baseline gap-2">
          <div className={`truncate font-semibold text-slate-950 ${dense ? "text-sm leading-4" : "text-sm"}`}>{title}</div>
          {code ? <div className="shrink-0 text-[10px] tabular-nums text-slate-400">{code}</div> : null}
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
      </div>
      <div className={`grid grid-cols-2 gap-2 ${dense ? "mt-1.5" : "mt-2"}`}>
        <div className="min-w-0 rounded-lg bg-slate-50 px-2 py-1.5">
          {dense ? (
            <div>
              <div className="text-[10px] leading-3 text-slate-400">销售收入</div>
              <div className="mt-0.5 grid grid-cols-2 gap-2 text-[10px] leading-4 text-slate-400">
                <div className="min-w-0 whitespace-nowrap">
                  本期 <span className="text-[11px] font-semibold tabular-nums text-slate-950">{tenThousands(sales)}</span>
                </div>
                <div className="min-w-0 whitespace-nowrap text-right">
                  同期 <span className="text-[11px] font-medium tabular-nums text-slate-600">{tenThousands(priorSales)}</span>
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="text-[9px] leading-3 text-slate-400">销售收入</div>
              <div className="truncate text-sm font-semibold leading-5 tabular-nums text-slate-950">{currency(sales)}</div>
            </>
          )}
          {!dense ? (
            <div className="mt-0.5 truncate text-[9px] leading-3 text-slate-400">
              同期销售 <span className="font-medium tabular-nums text-slate-600">{currency(priorSales)}</span>
            </div>
          ) : null}
        </div>
        <div className="min-w-0 rounded-lg bg-slate-50 px-2 py-1.5">
          {dense ? (
            <div>
              <div className="text-[10px] leading-3 text-slate-400">净毛利</div>
              <div className="mt-0.5 grid grid-cols-2 gap-2 text-[10px] leading-4 text-slate-400">
                <div className="min-w-0 whitespace-nowrap">
                  本期 <span className="text-[11px] font-semibold tabular-nums text-slate-950">{tenThousands(profit)}</span>
                </div>
                <div className="min-w-0 whitespace-nowrap text-right">
                  同期 <span className="text-[11px] font-medium tabular-nums text-slate-600">{tenThousands(priorProfit)}</span>
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="text-[9px] leading-3 text-slate-400">净毛利</div>
              <div className="truncate text-sm font-semibold leading-5 tabular-nums text-slate-950">{currency(profit)}</div>
            </>
          )}
          {!dense ? (
            <div className="mt-0.5 truncate text-[9px] leading-3 text-slate-400">
              同期毛利 <span className="font-medium tabular-nums text-slate-600">{currency(priorProfit)}</span>
            </div>
          ) : null}
        </div>
      </div>
      {showPricedSalesAmount ? (
        <div className={`flex items-center justify-between rounded-lg bg-blue-50 text-blue-900 ${dense ? "mt-1.5 px-2 py-1 text-[10px]" : "mt-2 px-2.5 py-1.5 text-xs"}`}>
          <span className="text-blue-600">本期零售价</span>
          <span className="font-semibold tabular-nums">{currency(pricedSalesAmount)}</span>
        </div>
      ) : null}
      <div className={`grid grid-cols-3 divide-x divide-slate-100 rounded-lg border border-slate-100 text-center ${dense ? "mt-1.5 py-1" : "mt-2 py-1.5"}`}>
        <div className={`min-w-0 px-1 leading-3 text-slate-400 ${dense ? "text-[10px]" : "text-[9px]"}`}>
          <div>销售同比</div>
          <div className={`truncate font-semibold tabular-nums ${yoyClass(sales, priorSales)}`}>{formatYoy(sales, priorSales)}</div>
        </div>
        <div className={`min-w-0 px-1 leading-3 text-slate-400 ${dense ? "text-[10px]" : "text-[9px]"}`}>
          <div>毛利率</div>
          <div className="truncate font-medium tabular-nums text-slate-700">{percent(margin)}</div>
        </div>
        <div className={`min-w-0 px-1 leading-3 text-slate-400 ${dense ? "text-[10px]" : "text-[9px]"}`}>
          <div>小票数</div>
          <div className="truncate font-medium tabular-nums text-slate-700">{decimal(tickets)}</div>
        </div>
      </div>
    </button>
  );
}

function ProductRow({ row, onClick }: { row: DepartmentGoodsSummary; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] active:bg-slate-50"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-slate-950">{row.goods_name || row.goods_code}</div>
          <div className="mt-0.5 truncate text-xs text-slate-400">
            {row.goods_code}{row.barcode ? ` · ${row.barcode}` : ""}
          </div>
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-slate-300" />
      </div>
      <div className="mt-2 truncate text-xs text-slate-500">
        {row.group_name || row.group_code || "未归属柜组"}
        {row.supplier_name || row.supplier_code ? ` · ${row.supplier_name || row.supplier_code}` : ""}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div className="text-slate-500">销售 <span className="font-semibold text-slate-900">{currency(row.sales_revenue)}</span></div>
        <div className="text-slate-500">毛利 <span className="font-semibold text-slate-900">{currency(row.gross_profit)}</span></div>
        <div className="text-slate-500">毛利率 <span className="text-slate-900">{percent(row.gross_margin_rate)}</span></div>
        <div className="text-slate-500">小票 <span className="text-slate-900">{decimal(row.ticket_count)}</span></div>
      </div>
    </button>
  );
}

function SupplierRow({ row, onClick }: { row: DepartmentSupplierSummary; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition active:scale-[0.99] active:bg-slate-50"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-slate-950">{row.supplier_name || row.supplier_code}</div>
          <div className="mt-0.5 truncate text-xs text-slate-400">{row.supplier_code || "未设置供应商编码"}</div>
        </div>
        <ChevronRight className="mt-1 h-5 w-5 shrink-0 text-slate-300" />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div className="text-slate-500">销售 <span className="font-semibold text-slate-900">{currency(row.sales_revenue)}</span></div>
        <div className="text-slate-500">毛利 <span className="font-semibold text-slate-900">{currency(row.gross_profit)}</span></div>
        <div className="text-slate-500">商品 <span className="text-slate-900">{decimal(row.goods_count)}</span></div>
        <div className="text-slate-500">柜组 <span className="text-slate-900">{decimal(row.group_count)}</span></div>
      </div>
    </button>
  );
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

export default function MobileSalesDashboardPage() {
  const { user, menuUser, logout } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-sales-dashboard");
  const today = todayString();
  const datePresets = buildMobileSalesDatePresets(today);
  const [level, setLevel] = useState<MobileLevel>("stores");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [draftStartDate, setDraftStartDate] = useState(today);
  const [draftEndDate, setDraftEndDate] = useState(today);
  const [selectedStore, setSelectedStore] = useState<StoreSummary | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentSummary | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<GroupSummary | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<DepartmentGoodsSummary | null>(null);
  const [groupKeyword, setGroupKeyword] = useState("");
  const [productKeyword, setProductKeyword] = useState("");
  const [productView, setProductView] = useState<DepartmentProductView>("goods");
  const [supplierCode, setSupplierCode] = useState<string | null>(null);
  const [selectedBillno, setSelectedBillno] = useState<string | null>(null);
  const [dateError, setDateError] = useState("");
  const [dateFiltersOpen, setDateFiltersOpen] = useState(false);
  const [includeRentalAndBackofficeSales, setIncludeRentalAndBackofficeSales] = useState(false);
  const showPricedSalesAmount = isCosmeticsRetailPriceScope(selectedStore, selectedDepartment);

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-sales-dashboard",
    moduleName: "手机端销售看板",
    clientType: "mobile",
    enabled: hasAccess,
    initialQueryConditions: {
      query_type: "sales",
      start_date: startDate,
      end_date: endDate,
      prior_start_date: shiftYear(startDate),
      prior_end_date: shiftYear(endDate),
      query_level: "stores",
      exclude_rental: true,
      exclude_backoffice_departments: true,
    },
  });

  const priorStartDate = shiftYear(startDate);
  const priorEndDate = shiftYear(endDate);
  const commonParams = useMemo(
    () => ({
      start_date: startDate,
      end_date: endDate,
      prior_start_date: priorStartDate,
      prior_end_date: priorEndDate,
      exclude_rental: !includeRentalAndBackofficeSales,
      exclude_backoffice_departments: !includeRentalAndBackofficeSales,
    }),
    [endDate, includeRentalAndBackofficeSales, priorEndDate, priorStartDate, startDate],
  );

  const storesQuery = useQuery<StoreSummary[]>({
    queryKey: ["/api/sales/summary/stores", "mobile", commonParams],
    queryFn: () =>
      getSalesDashboardData(`/api/sales/summary/stores${queryString(commonParams)}`, apiGet),
    enabled: level === "stores" && hasAccess,
  });

  const departmentsQuery = useQuery<DepartmentSummary[]>({
    queryKey: ["/api/sales/summary/departments", "mobile", commonParams, selectedStore?.store_id],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/departments${queryString({ ...commonParams, store_id: selectedStore?.store_id })}`,
        apiGet,
      ),
    enabled: level === "departments" && Boolean(selectedStore) && hasAccess,
  });

  const groupsQuery = useQuery<GroupSummary[]>({
    queryKey: [
      "/api/sales/summary/groups",
      "mobile",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      groupKeyword,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/groups${queryString({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: isUnassignedDepartment(selectedDepartment!) ? undefined : selectedDepartment?.department_code,
          unassigned_department: selectedDepartment ? isUnassignedDepartment(selectedDepartment) : undefined,
          keyword: groupKeyword,
          limit: 300,
        })}`,
        apiGet,
      ),
    enabled: level === "groups" && Boolean(selectedDepartment) && hasAccess,
  });

  const departmentGoodsQuery = useQuery<DepartmentGoodsSummary[]>({
    queryKey: [
      "/api/sales/summary/department-goods",
      "mobile",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      selectedGroup?.group_code,
      supplierCode,
      productKeyword,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/department-goods${queryString({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: isUnassignedDepartment(selectedDepartment!) ? undefined : selectedDepartment?.department_code,
          unassigned_department: selectedDepartment ? isUnassignedDepartment(selectedDepartment) : undefined,
          group_code: selectedGroup?.group_code,
          supplier_code: supplierCode || undefined,
          keyword: productKeyword,
          limit: 500,
        })}`,
        apiGet,
      ),
    enabled:
      level === "department-products" &&
      productView === "goods" &&
      Boolean(selectedDepartment) &&
      hasAccess,
  });

  const departmentSuppliersQuery = useQuery<DepartmentSupplierSummary[]>({
    queryKey: [
      "/api/sales/summary/department-suppliers",
      "mobile",
      commonParams,
      selectedStore?.store_id,
      selectedDepartment?.department_code,
      productKeyword,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/summary/department-suppliers${queryString({
          ...commonParams,
          store_id: selectedStore?.store_id,
          department_code: isUnassignedDepartment(selectedDepartment!) ? undefined : selectedDepartment?.department_code,
          unassigned_department: selectedDepartment ? isUnassignedDepartment(selectedDepartment) : undefined,
          keyword: productKeyword,
          limit: 300,
        })}`,
        apiGet,
      ),
    enabled:
      level === "department-products" &&
      productView === "suppliers" &&
      Boolean(selectedDepartment) &&
      hasAccess,
  });

  const selectedProductTicketParams = useMemo(() => buildProductTicketParams(selectedProduct), [selectedProduct]);

  const ticketsQuery = useQuery<TicketSummary[]>({
    queryKey: [
      "/api/sales/groups/tickets",
      "mobile",
      selectedGroup?.group_code,
      startDate,
      endDate,
      selectedProductTicketParams,
      includeRentalAndBackofficeSales,
    ],
    queryFn: () =>
      getSalesDashboardData(
        `/api/sales/groups/${encodeURIComponent(selectedGroup?.group_code ?? "")}/tickets${queryString({
          start_date: startDate,
          end_date: endDate,
          ...selectedProductTicketParams,
          exclude_rental: !includeRentalAndBackofficeSales,
          exclude_backoffice_departments: !includeRentalAndBackofficeSales,
        })}`,
        apiGet,
      ),
    enabled: level === "tickets" && Boolean(selectedGroup) && hasAccess,
  });

  const ticketDetailQuery = useQuery<TicketDetail>({
    queryKey: ["/api/sales/tickets", "mobile", selectedBillno],
    queryFn: () => apiGet(`/api/sales/tickets/${encodeURIComponent(selectedBillno ?? "")}`),
    enabled: Boolean(selectedBillno),
  });

  const ticketFirstGood = ticketDetailQuery.data?.goods?.[0];

  const activeQuery =
    level === "stores"
      ? storesQuery
      : level === "departments"
        ? departmentsQuery
        : level === "groups"
          ? groupsQuery
          : level === "department-products"
            ? productView === "goods"
              ? departmentGoodsQuery
              : departmentSuppliersQuery
            : ticketsQuery;

  const totals = useMemo(() => {
    if (level === "stores") {
      return (storesQuery.data ?? []).reduce(
        (sum, row) => ({
          sales: sum.sales + Number(row.effective_sales || 0),
          priorSales: sum.priorSales + Number(row.same_period_effective_sales || 0),
          profit: sum.profit + Number(row.net_profit || 0),
          priorProfit: sum.priorProfit + Number(row.same_period_net_profit || 0),
          tickets: sum.tickets + Number(row.ticket_count || 0),
          groups: sum.groups + Number(row.group_count || 0),
        }),
        { sales: 0, priorSales: 0, profit: 0, priorProfit: 0, tickets: 0, groups: 0 },
      );
    }
    if (level === "departments") {
      return (departmentsQuery.data ?? []).reduce(
        (sum, row) => ({
          sales: sum.sales + Number(row.effective_sales || 0),
          priorSales: sum.priorSales + Number(row.same_period_effective_sales || 0),
          profit: sum.profit + Number(row.net_profit || 0),
          priorProfit: sum.priorProfit + Number(row.same_period_net_profit || 0),
          tickets: sum.tickets + Number(row.ticket_count || 0),
          groups: sum.groups + Number(row.group_count || 0),
        }),
        { sales: 0, priorSales: 0, profit: 0, priorProfit: 0, tickets: 0, groups: 0 },
      );
    }
    if (level === "groups") {
      return (groupsQuery.data ?? []).reduce(
        (sum, row) => ({
          sales: sum.sales + Number(row.effective_sales || 0),
          priorSales: sum.priorSales + Number(row.same_period_effective_sales || 0),
          profit: sum.profit + Number(row.net_profit || 0),
          priorProfit: sum.priorProfit + Number(row.same_period_net_profit || 0),
          tickets: sum.tickets + Number(row.ticket_count || 0),
          groups: sum.groups + 1,
        }),
        { sales: 0, priorSales: 0, profit: 0, priorProfit: 0, tickets: 0, groups: 0 },
      );
    }
    if (level === "department-products") {
      if (productView === "suppliers") {
        return (departmentSuppliersQuery.data ?? []).reduce(
          (sum, row) => ({
            sales: sum.sales + Number(row.sales_revenue || 0),
            priorSales: null,
            profit: sum.profit + Number(row.gross_profit || 0),
            priorProfit: null,
            tickets: sum.tickets + Number(row.ticket_count || 0),
            groups: sum.groups + Number(row.group_count || 0),
          }),
          { sales: 0, priorSales: null, profit: 0, priorProfit: null, tickets: 0, groups: 0 },
        );
      }
      const groupCodes = new Set<string>();
      return (departmentGoodsQuery.data ?? []).reduce(
        (sum, row) => {
          const groupCode = String(row.group_code || "").trim();
          if (groupCode) groupCodes.add(groupCode);
          return {
            sales: sum.sales + Number(row.sales_revenue || 0),
            priorSales: null,
            profit: sum.profit + Number(row.gross_profit || 0),
            priorProfit: null,
            tickets: sum.tickets + Number(row.ticket_count || 0),
            groups: groupCodes.size,
          };
        },
        { sales: 0, priorSales: null, profit: 0, priorProfit: null, tickets: 0, groups: 0 },
      );
    }
    return (ticketsQuery.data ?? []).reduce(
      (sum, row) => ({
        sales: sum.sales + Number(row.effective_sales || 0),
        priorSales: null,
        profit: sum.profit + Number(row.net_profit || 0),
        priorProfit: null,
        tickets: sum.tickets + 1,
        groups: selectedGroup ? 1 : 0,
      }),
      { sales: 0, priorSales: null, profit: 0, priorProfit: null, tickets: 0, groups: 0 },
    );
  }, [
    departmentGoodsQuery.data,
    departmentSuppliersQuery.data,
    departmentsQuery.data,
    groupsQuery.data,
    level,
    productView,
    selectedGroup,
    storesQuery.data,
    ticketsQuery.data,
  ]);

  const goBack = () => {
    if (level === "tickets") {
      const nextLevel = selectedProduct ? "department-products" : "groups";
      recordQuery({
        query_type: "sales",
        ...commonParams,
        query_level: nextLevel,
        navigation_action: "back",
        from_level: "tickets",
        to_level: nextLevel,
        store_id: selectedStore?.store_id,
        store_name: selectedStore?.store_name,
        department_code: selectedDepartment?.department_code,
        department_name: selectedDepartment?.department_name,
        group_code: selectedGroup?.group_code,
        group_name: selectedGroup?.group_name,
      });
      setLevel(nextLevel);
      setSelectedBillno(null);
      return;
    }
    if (level === "department-products") {
      recordQuery({
        query_type: "sales",
        ...commonParams,
        query_level: "groups",
        navigation_action: "back",
        from_level: "department-products",
        to_level: "groups",
        store_id: selectedStore?.store_id,
        store_name: selectedStore?.store_name,
        department_code: selectedDepartment?.department_code,
        department_name: selectedDepartment?.department_name,
      });
      setLevel("groups");
      setSelectedProduct(null);
      setSupplierCode(null);
      setProductView("goods");
      return;
    }
    if (level === "groups") {
      recordQuery({
        query_type: "sales",
        ...commonParams,
        query_level: "departments",
        navigation_action: "back",
        from_level: "groups",
        to_level: "departments",
        store_id: selectedStore?.store_id,
        store_name: selectedStore?.store_name,
        department_code: selectedDepartment?.department_code,
        department_name: selectedDepartment?.department_name,
      });
      setLevel("departments");
      setSelectedGroup(null);
      return;
    }
    if (level === "departments") {
      recordQuery({
        query_type: "sales",
        ...commonParams,
        query_level: "stores",
        navigation_action: "back",
        from_level: "departments",
        to_level: "stores",
        store_id: selectedStore?.store_id,
        store_name: selectedStore?.store_name,
      });
      setLevel("stores");
      setSelectedDepartment(null);
      return;
    }
  };

  const applyDates = (nextStart = draftStartDate, nextEnd = draftEndDate) => {
    const validation = validateSalesDashboardDateRanges({
      currentStartDate: nextStart,
      currentEndDate: nextEnd,
      priorStartDate: shiftYear(nextStart),
      priorEndDate: shiftYear(nextEnd),
    });
    if (validation) {
      setDateError(validation);
      setDateFiltersOpen(true);
      return;
    }
    setDateError("");
    setDraftStartDate(nextStart);
    setDraftEndDate(nextEnd);
    setStartDate(nextStart);
    setEndDate(nextEnd);
    setLevel("stores");
    setSelectedStore(null);
    setSelectedDepartment(null);
    setSelectedGroup(null);
    setSelectedProduct(null);
    setSupplierCode(null);
    setProductView("goods");
    setDateFiltersOpen(false);
    recordQuery({
      query_type: "sales",
      start_date: nextStart,
      end_date: nextEnd,
      prior_start_date: shiftYear(nextStart),
      prior_end_date: shiftYear(nextEnd),
      query_level: "stores",
    });
  };

  const toggleRentalAndBackofficeSales = () => {
    const nextIncluded = !includeRentalAndBackofficeSales;
    setIncludeRentalAndBackofficeSales(nextIncluded);
    recordQuery({
      query_type: "sales",
      ...commonParams,
      query_level: "stores",
      filter_action: nextIncluded ? "include_rental_and_backoffice_sales" : "exclude_rental_and_backoffice_sales",
      exclude_rental: !nextIncluded,
      exclude_backoffice_departments: !nextIncluded,
    });
  };

  const levelLabel = {
    stores: "门店销售汇总",
    departments: selectedStore?.store_name || "部门销售汇总",
    groups: selectedDepartment?.department_name || "柜组销售汇总",
    "department-products": selectedGroup
      ? `${selectedGroup.group_name || selectedGroup.group_code}商品`
      : `${selectedDepartment?.department_name || "部门"}商品`,
    tickets: selectedProduct
      ? `${selectedProduct.goods_name || selectedProduct.goods_code}小票`
      : `${selectedGroup?.group_name || selectedGroup?.group_code || "柜组"}小票`,
  }[level];

  if (!hasAccess) {
    return (
      <main className="min-h-[100dvh] bg-slate-50 p-5">
        <Card className="mx-auto mt-16 max-w-md rounded-3xl">
          <CardContent className="p-6 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <h1 className="mt-4 text-lg font-semibold">暂无销售看板权限</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              请联系管理员为当前账号同时开通“手机端销售看板”和“查看销售”权限。
            </p>
            <div className="mt-5 flex justify-center gap-2">
              <Button variant="outline" onClick={() => setLocation("/mobile")}><Home className="mr-2 h-4 w-4" />返回首页</Button>
              <Button variant="outline" onClick={() => logout()}>退出登录</Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  const rows =
    level === "stores"
      ? storesQuery.data ?? []
      : level === "departments"
        ? departmentsQuery.data ?? []
        : level === "groups"
          ? groupsQuery.data ?? []
          : level === "department-products"
            ? productView === "goods"
              ? departmentGoodsQuery.data ?? []
              : departmentSuppliersQuery.data ?? []
            : ticketsQuery.data ?? [];

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 px-3 pb-2.5 pt-[max(.65rem,env(safe-area-inset-top))] text-white shadow-md">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 rounded-full text-white hover:bg-white/10 hover:text-white"
              onClick={() => setLocation("/mobile")}
              aria-label="返回移动工作台"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <div className="text-[9px] font-medium tracking-[0.14em] text-teal-200">SHOPVIEW</div>
              <h1 className="truncate text-base font-semibold">销售看板</h1>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 rounded-full text-white hover:bg-white/10 hover:text-white"
            onClick={() => logout()}
            aria-label="退出登录"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-1 flex items-center justify-between gap-3 text-[10px] text-slate-300">
          <span className="truncate">{user?.real_name || user?.username}</span>
          <button
            type="button"
            className="shrink-0 rounded px-1 py-0.5 active:bg-white/10"
            onClick={() => setDateFiltersOpen((open) => !open)}
            aria-label="打开日期筛选"
          >
            {startDate} 至 {endDate}
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-xl space-y-2 px-2.5 pt-2.5">
        {dateFiltersOpen ? <Card className="rounded-2xl border-0 shadow-sm">
          <CardContent className="p-2">
            <button
              type="button"
              className="flex h-8 w-full items-center gap-2 rounded-xl px-1.5 text-left text-xs active:bg-slate-50"
              onClick={() => setDateFiltersOpen((open) => !open)}
              aria-expanded={dateFiltersOpen}
            >
              <CalendarDays className="h-4 w-4 shrink-0 text-teal-700" />
              <span className="min-w-0 flex-1 truncate font-medium text-slate-700">{startDate} 至 {endDate}</span>
              <span className="shrink-0 text-teal-700">{dateFiltersOpen ? "收起" : "筛选日期"}</span>
            </button>
            {dateFiltersOpen ? (
              <div className="mt-2 space-y-2 border-t border-slate-100 px-1.5 pt-2">
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label htmlFor="mobile-sales-start" className="text-[10px] text-slate-500">开始日期</Label>
                    <Input className="h-9 px-2 text-xs" id="mobile-sales-start" type="date" value={draftStartDate} onChange={(e) => setDraftStartDate(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="mobile-sales-end" className="text-[10px] text-slate-500">结束日期</Label>
                    <Input className="h-9 px-2 text-xs" id="mobile-sales-end" type="date" value={draftEndDate} onChange={(e) => setDraftEndDate(e.target.value)} />
                  </div>
                </div>
                <div className="flex items-center gap-1.5 overflow-x-auto">
                  {datePresets.map((preset) => (
                    <Button
                      key={preset.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 shrink-0 rounded-full px-3 text-xs"
                      onClick={() => applyDates(preset.start, preset.end)}
                    >
                      {preset.label}
                    </Button>
                  ))}
                  <Button type="button" size="sm" className="ml-auto h-8 shrink-0 rounded-full px-3 text-xs" onClick={() => applyDates()}>
                    <RefreshCw className="mr-1 h-3.5 w-3.5" />查询
                  </Button>
                </div>
                {dateError ? <div className="text-[11px] text-red-600">{dateError}</div> : null}
                <div className="text-[10px] text-slate-400">同期 {priorStartDate} 至 {priorEndDate}</div>
              </div>
            ) : null}
          </CardContent>
        </Card> : null}

        <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm">
          <div className="grid grid-cols-2 divide-x divide-slate-100">
            <OverviewMetric
              label="销售收入"
              value={activeQuery.isError ? "—" : currency(totals.sales)}
              priorLabel="同期销售"
              priorValue={activeQuery.isError || totals.priorSales == null ? "—" : currency(totals.priorSales)}
              yoyLabel="销售同比"
              current={totals.sales}
              prior={totals.priorSales}
              hasError={activeQuery.isError}
            />
            <OverviewMetric
              label="净毛利"
              value={activeQuery.isError ? "—" : currency(totals.profit)}
              priorLabel="同期毛利"
              priorValue={activeQuery.isError || totals.priorProfit == null ? "—" : currency(totals.priorProfit)}
              yoyLabel="毛利同比"
              current={totals.profit}
              prior={totals.priorProfit}
              hasError={activeQuery.isError}
            />
          </div>
        </div>

        <section>
          <div className="mb-2 flex min-h-8 items-center gap-2 px-0.5">
            {level !== "stores" ? (
              <Button variant="outline" size="icon" className="h-8 w-8 shrink-0 rounded-full bg-white" onClick={goBack} aria-label="返回上一级">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            ) : (
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-teal-100 text-teal-700">
                <Building2 className="h-4 w-4" />
              </div>
            )}
            <div className="flex min-w-0 flex-1 items-baseline gap-2">
              <h2 className="truncate text-sm font-semibold text-slate-950">{levelLabel}</h2>
              <div className="shrink-0 text-[10px] text-slate-400">{rows.length} 项 · 权限范围</div>
            </div>
            {level === "stores" ? (
              <Button
                type="button"
                size="sm"
                variant={includeRentalAndBackofficeSales ? "secondary" : "outline"}
                className="h-7 shrink-0 rounded-full bg-white px-2 text-[10px] text-teal-700 shadow-sm"
                aria-pressed={includeRentalAndBackofficeSales}
                onClick={toggleRentalAndBackofficeSales}
              >
                {!includeRentalAndBackofficeSales ? <Plus className="mr-1 h-3 w-3" /> : null}
                {includeRentalAndBackofficeSales ? "去除租赁/后台销售" : "添加租赁/后台销售"}
              </Button>
            ) : null}
            {activeQuery.isFetching ? <Loader2 className="h-5 w-5 animate-spin text-blue-600" /> : null}
          </div>

          {level === "groups" ? (
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input className="rounded-2xl bg-white pl-9" placeholder="搜索柜组编码或名称" value={groupKeyword} onChange={(e) => setGroupKeyword(e.target.value)} />
            </div>
          ) : null}

          {level === "department-products" ? (
            <div className="mb-3 space-y-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={productView === "goods" ? "default" : "outline"}
                  className="rounded-xl"
                  onClick={() => setProductView("goods")}
                >
                  商品明细
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={productView === "suppliers" ? "default" : "outline"}
                  className="rounded-xl"
                  onClick={() => {
                    setSupplierCode(null);
                    setProductView("suppliers");
                  }}
                >
                  供应商汇总
                </Button>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  className="rounded-xl bg-slate-50 pl-9"
                  placeholder={productView === "suppliers" ? "搜索供应商编码或名称" : "搜索商品、条码、柜组或供应商"}
                  value={productKeyword}
                  onChange={(event) => setProductKeyword(event.target.value)}
                />
              </div>
              {supplierCode ? (
                <div className="flex items-center justify-between gap-2 rounded-xl bg-teal-50 px-3 py-2 text-xs text-teal-800">
                  <span className="truncate">供应商筛选：{supplierCode}</span>
                  <Button type="button" variant="ghost" size="sm" className="h-7 shrink-0 px-2" onClick={() => setSupplierCode(null)}>
                    清除
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="space-y-1.5">
            {activeQuery.isLoading || activeQuery.isError || rows.length === 0 ? (
              <EmptyState loading={activeQuery.isLoading} error={activeQuery.error} label="当前筛选条件下暂无销售数据。" />
            ) : level === "stores" ? (
              (storesQuery.data ?? []).map((row) => (
                <SummaryRow
                  key={row.store_id}
                  title={row.store_name || row.store_id}
                  code={row.store_id}
                  sales={row.effective_sales}
                  priorSales={row.same_period_effective_sales}
                  profit={row.net_profit}
                  priorProfit={row.same_period_net_profit}
                  margin={row.ticket_margin}
                  tickets={row.ticket_count}
                  dense
                  onClick={() => {
                    recordQuery({
                      query_type: "sales",
                      ...commonParams,
                      query_level: "departments",
                      store_id: row.store_id,
                      store_name: row.store_name,
                    });
                    setSelectedStore(row);
                    setSelectedDepartment(null);
                    setSelectedGroup(null);
                    setSelectedProduct(null);
                    setSupplierCode(null);
                    setLevel("departments");
                  }}
                />
              ))
            ) : level === "departments" ? (
              (departmentsQuery.data ?? []).map((row) => (
                <SummaryRow
                  key={`${row.department_code}:${row.department_name}`}
                  title={row.department_name || "未归属部门"}
                  code={row.department_code || "未设置部门编码"}
                  sales={row.effective_sales}
                  priorSales={row.same_period_effective_sales}
                  profit={row.net_profit}
                  priorProfit={row.same_period_net_profit}
                  margin={row.ticket_margin}
                  tickets={row.ticket_count}
                  dense
                  onClick={() => {
                    recordQuery({
                      query_type: "sales",
                      ...commonParams,
                      query_level: "groups",
                      store_id: selectedStore?.store_id,
                      store_name: selectedStore?.store_name,
                      department_code: row.department_code,
                      department_name: row.department_name,
                    });
                    setSelectedDepartment(row);
                    setSelectedGroup(null);
                    setSelectedProduct(null);
                    setSupplierCode(null);
                    setProductView("goods");
                    setLevel("groups");
                  }}
                />
              ))
            ) : level === "groups" ? (
              (groupsQuery.data ?? []).map((row) => (
                <SummaryRow
                  key={row.group_code}
                  title={row.group_name || row.group_code}
                  code={row.group_code}
                  sales={row.effective_sales}
                  priorSales={row.same_period_effective_sales}
                  profit={row.net_profit}
                  priorProfit={row.same_period_net_profit}
                  margin={row.ticket_margin ?? row.net_margin}
                  tickets={row.ticket_count}
                  pricedSalesAmount={row.priced_sales_amount}
                  showPricedSalesAmount={showPricedSalesAmount}
                  onClick={() => {
                    const nextLevel = isSupermarketDepartment(selectedDepartment) ? "goods" : "tickets";
                    recordQuery({
                      query_type: "sales",
                      ...commonParams,
                      query_level: nextLevel,
                      store_id: selectedStore?.store_id,
                      store_name: selectedStore?.store_name,
                      department_code: selectedDepartment?.department_code,
                      department_name: selectedDepartment?.department_name,
                      group_code: row.group_code,
                      group_name: row.group_name,
                    });
                    setSelectedGroup(row);
                    setSelectedProduct(null);
                    setSupplierCode(null);
                    setProductView("goods");
                    setLevel(isSupermarketDepartment(selectedDepartment) ? "department-products" : "tickets");
                  }}
                />
              ))
            ) : level === "department-products" ? (
              productView === "suppliers" ? (
                (departmentSuppliersQuery.data ?? []).map((row) => (
                  <SupplierRow
                    key={row.supplier_code}
                    row={row}
                    onClick={() => {
                      recordQuery({
                        query_type: "sales",
                        ...commonParams,
                        query_level: "goods",
                        store_id: selectedStore?.store_id,
                        store_name: selectedStore?.store_name,
                        department_code: selectedDepartment?.department_code,
                        department_name: selectedDepartment?.department_name,
                        supplier_code: row.supplier_code,
                      });
                      setSupplierCode(row.supplier_code);
                      setProductView("goods");
                    }}
                  />
                ))
              ) : (
                (departmentGoodsQuery.data ?? []).map((row) => (
                  <ProductRow
                    key={`${row.group_code}:${row.goods_code}:${row.barcode}:${row.supplier_code}`}
                    row={row}
                    onClick={() => {
                      recordQuery({
                        query_type: "sales",
                        ...commonParams,
                        query_level: "tickets",
                        store_id: selectedStore?.store_id,
                        store_name: selectedStore?.store_name,
                        department_code: selectedDepartment?.department_code,
                        department_name: selectedDepartment?.department_name,
                        group_code: row.group_code,
                        group_name: row.group_name,
                        goods_code: row.goods_code,
                        barcode: row.barcode,
                        supplier_code: row.supplier_code,
                      });
                      if (row.group_code && row.group_code !== selectedGroup?.group_code) {
                        setSelectedGroup({
                          group_code: row.group_code,
                          group_name: row.group_name,
                          ticket_count: 0,
                          priced_sales_amount: 0,
                          effective_sales: 0,
                          net_profit: 0,
                          ticket_margin: 0,
                          net_margin: 0,
                        });
                      }
                      setSelectedProduct(row);
                      setLevel("tickets");
                    }}
                  />
                ))
              )
            ) : (
              (ticketsQuery.data ?? []).map((row) => (
                <button
                  key={`${row.billno}`}
                  type="button"
                  className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm active:bg-slate-50"
                  onClick={() => {
                    recordQuery({
                      query_type: "sales",
                      start_date: startDate,
                      end_date: endDate,
                      query_level: "detail",
                      store_id: selectedStore?.store_id,
                      store_name: selectedStore?.store_name,
                      department_code: selectedDepartment?.department_code,
                      department_name: selectedDepartment?.department_name,
                      group_code: selectedGroup?.group_code,
                      group_name: selectedGroup?.group_name,
                      goods_code: selectedProduct?.goods_code,
                      barcode: selectedProduct?.barcode,
                      ticket_no: `${row.invoice_no || row.billno}`,
                      bill_no: `${row.billno}`,
                    });
                    setSelectedBillno(`${row.billno}`);
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-950">小票 {row.invoice_no || row.billno}</div>
                      <div className="mt-1 text-xs text-slate-400">{row.sale_datetime || row.sale_date || "-"}</div>
                    </div>
                    <FileText className="h-5 w-5 text-slate-300" />
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                    {showPricedSalesAmount ? (
                      <div className="col-span-2 flex items-center justify-between rounded-xl bg-blue-50 px-3 py-2 text-blue-900">
                        <span className="text-blue-600">本期零售价</span>
                        <span className="font-semibold tabular-nums">{currency(row.priced_sales_amount)}</span>
                      </div>
                    ) : null}
                    <div className="text-slate-500">销售 <span className="font-semibold text-slate-900">{currency(row.effective_sales)}</span></div>
                    <div className="text-slate-500">毛利 <span className="font-semibold text-slate-900">{currency(row.net_profit)}</span></div>
                    <div className="text-slate-500">毛利率 <span className="text-slate-900">{percent(row.ticket_margin)}</span></div>
                    <div className="text-slate-500">数量 <span className="text-slate-900">{decimal(row.quantity)}</span></div>
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <div className="flex items-center justify-center gap-2 py-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4" /> 手机端模块权限与业务数据范围共同控制
        </div>
      </div>

      <Dialog open={Boolean(selectedBillno)} onOpenChange={(open) => !open && setSelectedBillno(null)}>
        <DialogContent className="max-h-[88dvh] w-[calc(100vw-1.5rem)] max-w-lg overflow-y-auto rounded-3xl p-4">
          <DialogHeader>
            <DialogTitle>小票详情 {selectedBillno}</DialogTitle>
          </DialogHeader>
          {ticketDetailQuery.isLoading ? (
            <div className="flex min-h-40 items-center justify-center gap-2 text-sm text-blue-700">
              <Loader2 className="h-5 w-5 animate-spin" />加载中…
            </div>
          ) : ticketDetailQuery.isError ? (
            <div className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-800">小票详情加载失败。</div>
          ) : (
            <div className="space-y-4 text-sm">
              <div className="rounded-2xl bg-slate-50 p-3">
                <div className="mb-2 flex items-center justify-between"><span className="text-slate-500">数据来源</span><Badge variant="outline">{ticketDetailQuery.data?.source || "-"}</Badge></div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <span className="text-slate-500">交易时间</span><span className="text-right">{valueText(ticketDetailQuery.data?.head?.rqsj ?? ticketFirstGood?.sale_datetime ?? ticketFirstGood?.sale_date ?? ticketFirstGood?.rqsj)}</span>
                  <span className="text-slate-500">收银机号</span><span className="text-right">{valueText(ticketDetailQuery.data?.head?.syjh ?? ticketFirstGood?.cash_register_no)}</span>
                  <span className="text-slate-500">收款员</span><span className="text-right">{valueText(ticketDetailQuery.data?.head?.syyh ?? ticketFirstGood?.cashier)}</span>
                  <span className="text-slate-500">会员卡号</span><span className="text-right">{valueText(ticketDetailQuery.data?.head?.hykh)}</span>
                </div>
              </div>
              <div>
                <h3 className="font-semibold">商品明细</h3>
                <div className="mt-2 space-y-2">
                  {(ticketDetailQuery.data?.goods ?? []).map((item, index) => {
                    const productDisplay = getReceiptProductDisplay(item);
                    return (
                      <div key={`${valueText(item.code ?? item.goods_code ?? item.sglgdid)}:${index}`} className="rounded-2xl border border-slate-200 p-3">
                        <div className="font-medium">{productDisplay.name}</div>
                        {productDisplay.identifiers.map((identifier) => (
                          <div key={identifier} className="mt-0.5 text-xs text-slate-400">{identifier}</div>
                        ))}
                        <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                          <span>数量 {decimal(Number(item.sl ?? item.quantity ?? item.sglsl ?? 0))}</span>
                          <span>销售 {currency(Number(item.hjje ?? item.effective_sales ?? item.sglxssr ?? 0))}</span>
                        </div>
                      </div>
                    );
                  })}
                  {(ticketDetailQuery.data?.goods ?? []).length === 0 ? <div className="text-slate-500">暂无商品明细。</div> : null}
                </div>
              </div>
              {(ticketDetailQuery.data?.payments?.length ?? 0) > 0 ? (
                <div>
                  <h3 className="font-semibold">付款明细</h3>
                  <div className="mt-2 space-y-2">
                    {ticketDetailQuery.data?.payments.map((payment, index) => (
                      <div key={`${valueText(payment.paycode)}:${index}`} className="flex items-center justify-between rounded-2xl border border-slate-200 p-3">
                        <div>
                          <div className="font-medium">{valueText(payment.payname || payment.paycode)}</div>
                          <div className="mt-0.5 text-xs text-slate-400">类型 {valueText(payment.paytype || payment.flag)}</div>
                        </div>
                        <div className="font-semibold tabular-nums">{currency(Number(payment.je ?? 0))}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </main>
  );
}
