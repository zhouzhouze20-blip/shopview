import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Building2, ChevronRight, CircleDollarSign, Download, Link2, Loader2, Search, Store } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPost } from "@/lib/api";
import { findFinancialMonthContaining, getFinancialMonthWindow, localDateFromToday } from "@/lib/financialMonth";
import {
  exportRevenueDashboardExcel,
  type RevenueDashboardExtraExportItem,
  type RevenueDashboardFeeBreakdown,
} from "@/lib/revenue-dashboard-export";

type RevenueDashboardItem = {
  store_id: number;
  store_code?: string | null;
  store_name?: string | null;
  department_code?: string | null;
  department_name: string;
  department_sort_order?: number | null;
  group_code?: string | null;
  group_name: string;
  unit_codes?: string | null;
  unit_count: number;
  raw_sales_gross_profit_amount: number;
  raw_fee_amount: number;
  raw_extra_amount: number;
  sales_adjustment_amount: number;
  fee_adjustment_amount: number;
  extra_adjustment_amount: number;
  tax_adjustment_amount: number;
  close_adjustment_amount: number;
  sales_gross_profit_amount: number;
  fee_amount: number;
  extra_amount: number;
  total_amount: number;
  fee_breakdown?: RevenueDashboardFeeBreakdown[];
};

type RevenueDashboardResponse = {
  start_date: string;
  end_date: string;
  permission_scoped: boolean;
  grain: string;
  date_basis: {
    sales: "financial_date";
    fees: "payment_date";
    extra: "revenue_date" | "financial_period";
  };
  fee_scope_note: string;
  accounting_basis: "REALTIME" | "MONTH_CLOSED" | "MIXED";
  fully_closed_store_ids: number[];
  nc_6051_summary: {
    available: boolean;
    subject_prefix: "6051";
    amount_basis: "local_credit_minus_local_debit";
    tax_basis: "explanation_matches_accrual_tax";
    tax_period_basis: "confirmed_month_close_only";
    store_amounts: Array<{
      store_id: number;
      store_code: string;
      amount: number;
      tax_amount: number;
    }>;
    department_amounts: Array<{
      store_id: number;
      store_code: string;
      department_code?: string | null;
      department_name: string;
      amount: number;
      tax_amount: number;
    }>;
  };
  month_closes: Array<{
    id: number;
    store_id: number;
    store_code?: string | null;
    store_name?: string | null;
    period_month: string;
    nc_amount_before_tax: number;
    accrued_tax_amount: number;
    nc_control_amount: number;
    close_adjustment_amount: number;
    final_fee_extra_amount: number;
    source_snapshot_id: string;
    confirmed_at?: string | null;
  }>;
  items: RevenueDashboardItem[];
};

type RevenueDashboardExtraExportResponse = {
  start_date: string;
  end_date: string;
  permission_scoped: boolean;
  total_count: number;
  returned_count: number;
  is_truncated: boolean;
  items: RevenueDashboardExtraExportItem[];
};

type RevenueMonthCloseNcDetail = {
  detail_id?: string | null;
  voucher_id?: string | null;
  subject_code?: string | null;
  department_code?: string | null;
  department_name?: string | null;
  explanation?: string | null;
  debit_amount: number;
  credit_amount: number;
  amount: number;
  is_accrued_tax: boolean;
  load_date?: string | null;
};

type RevenueMonthCloseFujiDetail = {
  business_type: "JOINT" | "RENTAL" | string;
  source_bill_no?: string | null;
  source_row_no?: string | null;
  payment_bill_no?: string | null;
  source_group_code?: string | null;
  source_group_name?: string | null;
  fuji_department_code?: string | null;
  fuji_department_name?: string | null;
  supplier_code?: string | null;
  supplier_name?: string | null;
  contract_code?: string | null;
  fee_type_code?: string | null;
  fee_type_name?: string | null;
  audit_date?: string | null;
  amount: number;
};

type RevenueMonthCloseBindingResponse = {
  start_date: string;
  end_date: string;
  pending_count: number;
  pending_amount: number;
  auto_matched_count: number;
  auto_matched_amount: number;
  direction_summary: Record<"NC_ONLY" | "FUJI_ONLY" | "AMOUNT_DIFFERENCE" | "OTHER", {
    count: number;
    amount: number;
  }>;
  store_summaries: Array<{
    store_id: number;
    store_code?: string | null;
    store_name?: string | null;
    pending_count: number;
    pending_amount: number;
    auto_matched_count: number;
    auto_matched_amount: number;
    direction_summary: Record<"NC_ONLY" | "FUJI_ONLY" | "AMOUNT_DIFFERENCE" | "OTHER", {
      count: number;
      amount: number;
    }>;
  }>;
  items: Array<{
    id: number;
    month_close_id: number;
    store_id: number;
    store_code?: string | null;
    store_name?: string | null;
    period_month: string;
    target_component: "FEE" | "EXTRA";
    adjustment_category: string;
    department_code?: string | null;
    department_name?: string | null;
    source_department_code?: string | null;
    source_department_name?: string | null;
    source_subject_code?: string | null;
    source_subject_name?: string | null;
    source_business_type: "NC_EXTRA_DIFFERENCE" | "FEE_DIFFERENCE" | "JOINT" | "RENTAL" | string;
    source_group_code?: string | null;
    source_group_name?: string | null;
    difference_direction: "NC_ONLY" | "FUJI_ONLY" | "AMOUNT_DIFFERENCE" | "OTHER";
    supplier_code?: string | null;
    supplier_name?: string | null;
    fee_type_code?: string | null;
    fee_type_name?: string | null;
    raw_amount: number;
    accrued_tax_amount: number;
    adjustment_amount: number;
    final_amount: number;
    adjustment_reason?: string | null;
    allocation_basis?: string | null;
    nc_detail_count: number;
    nc_detail_amount: number;
    nc_details: RevenueMonthCloseNcDetail[];
    tax_detail_count: number;
    tax_detail_amount: number;
    tax_details: RevenueMonthCloseNcDetail[];
    fuji_detail_count: number;
    fuji_detail_amount: number;
    fuji_details: RevenueMonthCloseFujiDetail[];
    auto_matched_count: number;
    auto_matched_amount: number;
    binding_lines: Array<{
      source_line_key: string;
      source_type: "NC" | "FUJI" | "ADJUSTMENT";
      source_detail_id?: string | null;
      source_voucher_id?: string | null;
      source_bill_no?: string | null;
      source_row_no?: string | null;
      source_amount: number;
      suggested_binding_amount: number;
    }>;
  }>;
  unit_options: Array<{
    store_id: number;
    unit_id: number;
    unit_code: string;
    floor_name?: string | null;
    group_options: Array<{
      group_id?: number | null;
      group_code: string;
      group_name: string;
      department_code?: string | null;
      department_name?: string | null;
    }>;
  }>;
};

type SummaryRow = {
  key: string;
  label: string;
  code?: string | null;
  department_sort_order?: number | null;
  department_count: number;
  group_count: number;
  unit_codes?: string | null;
  sales: number;
  fee: number;
  extra: number;
  adjustment: number;
  tax?: number | null;
  nc_6051_amount?: number | null;
  total: number;
};

type DrillLevel = "stores" | "departments" | "groups";
type DetailMode = "gross-profit" | "fees" | "extras";

type RevenueDashboardGroupDetail = {
  store: {
    store_id: number;
    store_code?: string | null;
    store_name?: string | null;
  };
  department: {
    department_code?: string | null;
    department_name: string;
  };
  group: {
    group_code: string;
    group_name: string;
  };
  start_date: string;
  end_date: string;
  gross_profit: {
    total_amount: number;
    items: Array<{
      revenue_date: string;
      gross_profit_amount: number;
      source_count: number;
    }>;
  };
  fees: {
    date_basis: "payment_date";
    total_count: number;
    returned_count: number;
    is_truncated: boolean;
    raw_total_amount: number;
    adjustment_amount: number;
    total_amount: number;
    month_close_adjustments: Array<{
      id: number;
      adjustment_category: string;
      subject_code?: string | null;
      subject_name?: string | null;
      fee_type_code?: string | null;
      fee_type_name?: string | null;
      raw_amount: number;
      accrued_tax_amount: number;
      adjustment_amount: number;
      final_amount: number;
      allocation_basis?: string | null;
      adjustment_reason?: string | null;
    }>;
    items: Array<{
      id: string;
      revenue_date: string;
      payment_no?: string | null;
      settlement_no?: string | null;
      contract_code?: string | null;
      contract_name?: string | null;
      fee_type_code?: string | null;
      fee_type_name?: string | null;
      tax_included_amount: number;
      source_tax_excluded_amount: number;
      tax_excluded_amount: number;
      source_type?: string | null;
    }>;
  };
};

type RevenueDashboardExtraDetail = {
  store: {
    store_id: number;
    store_code?: string | null;
    store_name?: string | null;
  };
  target: {
    department_code?: string | null;
    department_name?: string | null;
    group_code?: string | null;
    group_name?: string | null;
    unit_code?: string | null;
  };
  start_date: string;
  end_date: string;
  date_basis: "revenue_date";
  total_count: number;
  returned_count: number;
  is_truncated: boolean;
  raw_total_amount: number;
  adjustment_amount: number;
  total_amount: number;
  month_close_adjustments: Array<{
    id: number;
    adjustment_category: string;
    subject_code?: string | null;
    subject_name?: string | null;
    raw_amount: number;
    accrued_tax_amount: number;
    adjustment_amount: number;
    final_amount: number;
    allocation_basis?: string | null;
    adjustment_reason?: string | null;
  }>;
  subjects: Array<{
    subject_code: string;
    subject_name: string;
    detail_count: number;
    amount: number;
  }>;
  items: Array<{
    id: string;
    revenue_date: string;
    subject_code?: string | null;
    subject_name?: string | null;
    extra_type?: string | null;
    department_code?: string | null;
    department_name?: string | null;
    explanation?: string | null;
    voucher_no?: string | null;
    amount: number;
    source_detail_key?: string | null;
    source_group_code?: string | null;
    source_group_name?: string | null;
    unit_code?: string | null;
    match_method?: string | null;
    match_status?: string | null;
    match_reason?: string | null;
  }>;
};

const financialRange = (year: number, month: number | null) => {
  if (month == null) return { startDate: `${year}-01-01`, endDate: `${year}-12-31` };
  const window = getFinancialMonthWindow(year, month);
  return { startDate: window.start, endDate: window.end };
};

const money = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(value || 0);

const detailMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0);

const tenThousandMoney = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format((value || 0) / 10000);

const compactMoney = (value: number) => {
  const absolute = Math.abs(value);
  if (absolute >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (absolute >= 10000) return `${(value / 10000).toFixed(1)}万`;
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value);
};

const departmentKey = (row: RevenueDashboardItem) =>
  row.department_code || `name:${row.department_name}`;

const groupKey = (row: RevenueDashboardItem) =>
  row.group_code || `unit:${row.unit_codes || "未绑定"}:name:${row.group_name}`;

const departmentSortOrder = (left: SummaryRow, right: SummaryRow) =>
  (left.department_sort_order ?? Number.MAX_SAFE_INTEGER)
    - (right.department_sort_order ?? Number.MAX_SAFE_INTEGER)
  || left.label.localeCompare(right.label, "zh-CN")
  || String(left.code || "").localeCompare(String(right.code || ""));

const aggregateRows = (
  rows: RevenueDashboardItem[],
  keyOf: (row: RevenueDashboardItem) => string,
  labelOf: (row: RevenueDashboardItem) => string,
  codeOf: (row: RevenueDashboardItem) => string | null | undefined,
): SummaryRow[] => {
  const buckets = new Map<string, SummaryRow & { departments: Set<string>; groups: Set<string>; units: Set<string> }>();
  rows.forEach((row) => {
    const key = keyOf(row);
    const target = buckets.get(key) ?? {
      key,
      label: labelOf(row),
      code: codeOf(row),
      department_sort_order: row.department_sort_order ?? null,
      department_count: 0,
      group_count: 0,
      sales: 0,
      fee: 0,
      extra: 0,
      adjustment: 0,
      tax: 0,
      total: 0,
      departments: new Set<string>(),
      groups: new Set<string>(),
      units: new Set<string>(),
    };
    target.departments.add(departmentKey(row));
    target.groups.add(groupKey(row));
    String(row.unit_codes || "")
      .split("、")
      .map((value) => value.trim())
      .filter(Boolean)
      .forEach((value) => target.units.add(value));
    target.sales += row.raw_sales_gross_profit_amount;
    target.fee += row.raw_fee_amount;
    target.extra += row.raw_extra_amount;
    target.adjustment += row.close_adjustment_amount;
    target.tax = (target.tax ?? 0) + row.tax_adjustment_amount;
    target.total += row.total_amount;
    buckets.set(key, target);
  });

  return Array.from(buckets.values())
    .map(({ departments, groups, units, ...row }) => ({
      ...row,
      department_count: departments.size,
      group_count: groups.size,
      unit_codes: Array.from(units).join("、") || null,
    }))
    .sort((a, b) => b.total - a.total);
};

const otherBusinessIncomeTotal = (row: SummaryRow) =>
  row.nc_6051_amount ?? 0;

const shortDate = (value?: string | null) => value ? value.slice(0, 10) : "—";

function FujiSideDetails({
  details,
  count,
  amount,
}: {
  details: RevenueMonthCloseFujiDetail[];
  count: number;
  amount: number;
}) {
  return (
    <div className="min-w-80 text-xs">
      <div className="mb-2 flex items-center justify-between rounded bg-blue-50 px-2 py-1 font-medium text-blue-950">
        <span>{count} 行富基未匹配明细</span>
        <span className="tabular-nums">合计 {detailMoney(amount)}</span>
      </div>
      {details.length ? (
        <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
          {details.map((detail, index) => (
            <div key={`${detail.source_bill_no || "fuji"}-${detail.source_row_no || index}`} className="border-b pb-2 last:border-b-0">
              <div className="flex items-start justify-between gap-3">
                <span className="font-medium">
                  审核日期 {shortDate(detail.audit_date)} · {detail.business_type === "RENTAL" ? "租赁" : "联营"}
                </span>
                <span className="shrink-0 font-semibold tabular-nums">{detailMoney(detail.amount)}</span>
              </div>
              <div>{detail.source_group_code || "—"} {detail.source_group_name || "未识别柜组"}</div>
              <div>{detail.supplier_code || "—"} {detail.supplier_name || "未识别供应商"}</div>
              <div>{detail.fee_type_code || "—"} {detail.fee_type_name || "未识别费用"}</div>
              <div className="break-all text-muted-foreground">
                源单 {detail.source_bill_no || "—"} / 行 {detail.source_row_no || "—"}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded border border-dashed px-2 py-3 text-center text-muted-foreground">本侧没有未匹配源行</div>
      )}
    </div>
  );
}

function NcSideDetails({
  details,
  count,
  amount,
}: {
  details: RevenueMonthCloseNcDetail[];
  count: number;
  amount: number;
}) {
  return (
    <div className="min-w-80 text-xs">
      <div className="mb-2 flex items-center justify-between rounded bg-emerald-50 px-2 py-1 font-medium text-emerald-950">
        <span>{count} 行 NC 未匹配明细</span>
        <span className="tabular-nums">合计 {detailMoney(amount)}</span>
      </div>
      {details.length ? (
        <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
          {details.map((detail, index) => (
            <div key={`${detail.detail_id || "nc"}-${index}`} className="border-b pb-2 last:border-b-0">
              <div className="flex items-start justify-between gap-3">
                <span className={detail.is_accrued_tax ? "font-medium text-amber-700" : "font-medium"}>
                  {detail.is_accrued_tax ? "计提税" : `${detail.subject_code || "6051"} 凭证明细`}
                </span>
                <span className="shrink-0 font-semibold tabular-nums">{detailMoney(detail.amount)}</span>
              </div>
              <div>{detail.explanation || "无摘要"}</div>
              <div className="break-all text-muted-foreground">凭证 {detail.voucher_id || "—"}</div>
              <div className="break-all text-muted-foreground">明细 {detail.detail_id || "—"}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded border border-dashed px-2 py-3 text-center text-muted-foreground">本侧没有未匹配 NC 源行</div>
      )}
    </div>
  );
}

function MetricCard({
  title,
  value,
  note,
  icon,
}: {
  title: string;
  value: string;
  note: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{note}</p>
        </div>
        <div className="rounded-lg bg-slate-100 p-2 text-slate-700">{icon}</div>
      </CardContent>
    </Card>
  );
}

export default function RevenueDashboardPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const initialFinancialMonth = findFinancialMonthContaining(localDateFromToday());
  const [financialYear, setFinancialYear] = useState(initialFinancialMonth.year);
  const [financialMonth, setFinancialMonth] = useState<number | null>(initialFinancialMonth.index);
  const [appliedPeriod, setAppliedPeriod] = useState({
    year: initialFinancialMonth.year,
    month: initialFinancialMonth.index as number | null,
    ...financialRange(initialFinancialMonth.year, initialFinancialMonth.index),
  });
  const [level, setLevel] = useState<DrillLevel>("stores");
  const [selectedStoreKey, setSelectedStoreKey] = useState<string | null>(null);
  const [selectedDepartmentKey, setSelectedDepartmentKey] = useState<string | null>(null);
  const [detailSelection, setDetailSelection] = useState<{ row: SummaryRow; mode: DetailMode } | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [pendingBindingOpen, setPendingBindingOpen] = useState(false);
  const [pendingBindingStoreId, setPendingBindingStoreId] = useState<number | null>(null);
  const [bindingTargetByLine, setBindingTargetByLine] = useState<Record<string, "FEE" | "EXTRA">>({});
  const [bindingUnitByLine, setBindingUnitByLine] = useState<Record<string, string>>({});
  const [bindingGroupByLine, setBindingGroupByLine] = useState<Record<string, string>>({});

  const query = useQuery({
    queryKey: ["revenue-dashboard", appliedPeriod.year, appliedPeriod.month],
    queryFn: () => {
      const params = new URLSearchParams({
        start_date: appliedPeriod.startDate,
        end_date: appliedPeriod.endDate,
        financial_year: String(appliedPeriod.year),
      });
      if (appliedPeriod.month != null) params.set("financial_month", String(appliedPeriod.month));
      return apiGet<RevenueDashboardResponse>(`/api/revenue-map/dashboard?${params.toString()}`);
    },
  });

  const detailQuery = useQuery({
    queryKey: [
      "revenue-dashboard-group-detail",
      selectedStoreKey,
      detailSelection?.row.code,
      detailSelection?.mode,
      appliedPeriod.year,
      appliedPeriod.month,
    ],
    queryFn: () => {
      const groupCode = detailSelection?.row.code;
      if (!selectedStoreKey || !groupCode) throw new Error("缺少门店或柜位编码");
      const params = new URLSearchParams({
        store_id: selectedStoreKey,
        start_date: appliedPeriod.startDate,
        end_date: appliedPeriod.endDate,
        financial_year: String(appliedPeriod.year),
        detail_type: detailSelection?.mode || "all",
      });
      if (appliedPeriod.month != null) params.set("financial_month", String(appliedPeriod.month));
      return apiGet<RevenueDashboardGroupDetail>(
        `/api/revenue-map/dashboard/groups/${encodeURIComponent(groupCode)}/details?${params.toString()}`,
      );
    },
    enabled: Boolean(
      selectedStoreKey
      && detailSelection?.row.code
      && detailSelection.mode !== "extras"
    ),
  });

  const extraDetailQuery = useQuery({
    queryKey: [
      "revenue-dashboard-extra-detail",
      selectedStoreKey,
      detailSelection?.row.key,
      appliedPeriod.year,
      appliedPeriod.month,
    ],
    queryFn: () => {
      if (!selectedStoreKey || !detailSelection) throw new Error("缺少门店或其他收益行");
      const params = new URLSearchParams({
        store_id: selectedStoreKey,
        start_date: appliedPeriod.startDate,
        end_date: appliedPeriod.endDate,
        financial_year: String(appliedPeriod.year),
        source_group_name: detailSelection.row.label,
      });
      if (appliedPeriod.month != null) params.set("financial_month", String(appliedPeriod.month));
      if (detailSelection.row.code) {
        params.set("source_group_code", detailSelection.row.code);
      }
      return apiGet<RevenueDashboardExtraDetail>(
        `/api/revenue-map/dashboard/extra-details?${params.toString()}`,
      );
    },
    enabled: Boolean(selectedStoreKey && detailSelection?.mode === "extras"),
  });

  const pendingBindingQuery = useQuery({
    queryKey: ["revenue-dashboard-month-close-bindings", appliedPeriod.year, appliedPeriod.month],
    queryFn: () => {
      const params = new URLSearchParams({
        start_date: appliedPeriod.startDate,
        end_date: appliedPeriod.endDate,
        financial_year: String(appliedPeriod.year),
      });
      if (appliedPeriod.month != null) params.set("financial_month", String(appliedPeriod.month));
      return apiGet<RevenueMonthCloseBindingResponse>(
        `/api/revenue-map/dashboard/month-close-bindings?${params.toString()}`,
      );
    },
    enabled: Boolean(query.data?.month_closes.length),
  });

  const pendingBindingStoreSummaries = pendingBindingQuery.data?.store_summaries ?? [];
  const pendingAdjustmentByStore = useMemo(
    () => new Map(
      pendingBindingStoreSummaries.map((summary) => [
        String(summary.store_id),
        summary.pending_amount,
      ]),
    ),
    [pendingBindingStoreSummaries],
  );
  const pendingAdjustmentByDepartment = useMemo(() => {
    const amounts = new Map<string, number>();
    (pendingBindingQuery.data?.items ?? []).forEach((item) => {
      const department = item.department_code || item.department_name || "未归属部门";
      const key = `${item.store_id}|${department}`;
      amounts.set(key, (amounts.get(key) ?? 0) + item.adjustment_amount);
    });
    return amounts;
  }, [pendingBindingQuery.data?.items]);
  const pendingAdjustmentByGroup = useMemo(() => {
    const amounts = new Map<string, number>();
    (pendingBindingQuery.data?.items ?? []).forEach((item) => {
      const department = item.department_code || item.department_name || "未归属部门";
      const group = item.source_group_code || item.source_group_name;
      if (!group) return;
      const key = `${item.store_id}|${department}|${group}`;
      amounts.set(key, (amounts.get(key) ?? 0) + item.adjustment_amount);
    });
    return amounts;
  }, [pendingBindingQuery.data?.items]);
  const selectedPendingBindingStore = pendingBindingStoreId == null
    ? null
    : pendingBindingStoreSummaries.find((summary) => summary.store_id === pendingBindingStoreId) ?? null;
  const displayedPendingBindingItems = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.items ?? []
    : (pendingBindingQuery.data?.items ?? []).filter((item) => item.store_id === pendingBindingStoreId);
  const displayedPendingBindingCount = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.pending_count ?? 0
    : selectedPendingBindingStore?.pending_count ?? 0;
  const displayedPendingBindingAmount = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.pending_amount ?? 0
    : selectedPendingBindingStore?.pending_amount ?? 0;
  const displayedPendingBindingLineCount = displayedPendingBindingItems.reduce(
    (total, item) => total + (item.binding_lines?.length ?? 0),
    0,
  );
  const displayedPendingBindingDirectionSummary = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.direction_summary
    : selectedPendingBindingStore?.direction_summary;
  const displayedAutoMatchedCount = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.auto_matched_count ?? 0
    : selectedPendingBindingStore?.auto_matched_count ?? 0;
  const displayedAutoMatchedAmount = pendingBindingStoreId == null
    ? pendingBindingQuery.data?.auto_matched_amount ?? 0
    : selectedPendingBindingStore?.auto_matched_amount ?? 0;

  const bindDifferenceMutation = useMutation({
    mutationFn: ({
      adjustmentId,
      targetComponent,
      unitId,
      sourceGroupCode,
      sourceLineKey,
      adjustmentAmount,
    }: {
      adjustmentId: number;
      targetComponent: "FEE" | "EXTRA";
      unitId: number;
      sourceGroupCode: string;
      sourceLineKey: string;
      adjustmentAmount: number;
    }) =>
      apiPost(`/api/revenue-map/dashboard/month-close-bindings/${adjustmentId}/bind`, {
        target_component: targetComponent,
        unit_id: unitId,
        source_group_code: sourceGroupCode,
        source_line_key: sourceLineKey,
        adjustment_amount: adjustmentAmount,
        note: "收益看板按来源明细人工绑定",
      }),
    onSuccess: async (_result, variables) => {
      const bindingKey = `${variables.adjustmentId}:${variables.sourceLineKey}`;
      setBindingTargetByLine((current) => {
        const next = { ...current };
        delete next[bindingKey];
        return next;
      });
      setBindingUnitByLine((current) => {
        const next = { ...current };
        delete next[bindingKey];
        return next;
      });
      setBindingGroupByLine((current) => {
        const next = { ...current };
        delete next[bindingKey];
        return next;
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["revenue-dashboard-month-close-bindings"] }),
        queryClient.invalidateQueries({ queryKey: ["revenue-dashboard"] }),
      ]);
      toast({
        title: "绑定成功",
        description: `该来源明细已计入${variables.targetComponent === "FEE" ? "富基收费" : "NC非富基收费"}，并关联到所选柜位和柜组。`,
      });
    },
    onError: (error) => {
      toast({
        title: "绑定失败",
        description: error instanceof Error ? error.message : "请稍后重试。",
        variant: "destructive",
      });
    },
  });

  const permissionRows = query.data?.items ?? [];
  const fullyClosedStoreIds = useMemo(
    () => new Set((query.data?.fully_closed_store_ids ?? []).map(String)),
    [query.data?.fully_closed_store_ids],
  );
  const closedStoreIds = useMemo(
    () => new Set((query.data?.month_closes ?? []).map((close) => String(close.store_id))),
    [query.data?.month_closes],
  );
  const latestClosedPeriodLabel = useMemo(() => {
    const latestPeriod = (query.data?.month_closes ?? []).reduce(
      (latest, close) => close.period_month > latest ? close.period_month : latest,
      "",
    );
    if (!latestPeriod) return null;
    const [year, month] = latestPeriod.split("-");
    return `${year}年${Number(month)}月`;
  }, [query.data?.month_closes]);
  const nc6051StoreAmounts = useMemo(
    () => new Map(
      (query.data?.nc_6051_summary?.store_amounts ?? []).map((row) => [row.store_code, row]),
    ),
    [query.data?.nc_6051_summary?.store_amounts],
  );
  const nc6051DepartmentAmounts = useMemo(
    () => new Map(
      (query.data?.nc_6051_summary?.department_amounts ?? []).map((row) => [
        `${row.store_code}|${row.department_code || row.department_name}`,
        row,
      ]),
    ),
    [query.data?.nc_6051_summary?.department_amounts],
  );
  const storeSummaries = useMemo(
    () => {
      const rows = aggregateRows(
        permissionRows,
        (row) => String(row.store_id),
        (row) => row.store_name || row.store_code || String(row.store_id),
        (row) => row.store_code,
      );
      return rows.map((row) => {
        const nc6051 = nc6051StoreAmounts.get(row.code || "");
        const tax = closedStoreIds.has(row.key) ? (nc6051?.tax_amount ?? 0) : null;
        return {
          ...row,
          adjustment: fullyClosedStoreIds.has(row.key) && pendingBindingQuery.data
            ? (pendingAdjustmentByStore.get(row.key) ?? 0)
            : row.adjustment,
          tax,
          nc_6051_amount: nc6051?.amount ?? 0,
        };
      });
    },
    [closedStoreIds, fullyClosedStoreIds, nc6051StoreAmounts, pendingAdjustmentByStore, pendingBindingQuery.data, permissionRows],
  );

  const selectedStore = storeSummaries.find((row) => row.key === selectedStoreKey) ?? null;
  const storeRows = useMemo(
    () => permissionRows.filter((row) => selectedStoreKey == null || String(row.store_id) === selectedStoreKey),
    [permissionRows, selectedStoreKey],
  );
  const departmentSummaries = useMemo(
    () => {
      const rows = aggregateRows(
        storeRows,
        departmentKey,
        (row) => row.department_name,
        (row) => row.department_code,
      );
      return rows.map((row) => {
        const nc6051 = nc6051DepartmentAmounts.get(
          `${selectedStore?.code || ""}|${row.code || row.label}`,
        );
        const tax = selectedStoreKey && closedStoreIds.has(selectedStoreKey)
          ? (nc6051?.tax_amount ?? 0)
          : null;
        return {
          ...row,
          adjustment: selectedStoreKey
            && fullyClosedStoreIds.has(selectedStoreKey)
            && pendingBindingQuery.data
            ? (pendingAdjustmentByDepartment.get(`${selectedStoreKey}|${row.code || row.label}`) ?? 0)
            : row.adjustment,
          tax,
          nc_6051_amount: nc6051?.amount ?? 0,
        };
      }).sort(departmentSortOrder);
    },
    [closedStoreIds, fullyClosedStoreIds, nc6051DepartmentAmounts, pendingAdjustmentByDepartment, pendingBindingQuery.data, selectedStore?.code, selectedStoreKey, storeRows],
  );

  const selectedDepartment =
    departmentSummaries.find((row) => row.key === selectedDepartmentKey) ?? null;
  const departmentRows = useMemo(
    () => storeRows.filter((row) => selectedDepartmentKey == null || departmentKey(row) === selectedDepartmentKey),
    [selectedDepartmentKey, storeRows],
  );
  const groupSummaries = useMemo(
    () => {
      const rows = aggregateRows(
        departmentRows,
        groupKey,
        (row) => row.group_name || row.group_code || "未归属柜位",
        (row) => row.group_code,
      );
      const taxIsApplied = selectedStoreKey != null && closedStoreIds.has(selectedStoreKey);
      return rows.map((row) => ({
        ...row,
        adjustment: taxIsApplied && pendingBindingQuery.data && selectedDepartment
          ? (pendingAdjustmentByGroup.get(
            `${selectedStoreKey}|${selectedDepartment.code || selectedDepartment.label}|${row.code || row.label}`,
          ) ?? 0)
          : row.adjustment,
        tax: taxIsApplied ? (row.tax ?? 0) : null,
      }));
    },
    [closedStoreIds, departmentRows, fullyClosedStoreIds, pendingAdjustmentByGroup, pendingBindingQuery.data, selectedDepartment, selectedStoreKey],
  );

  const currentRows =
    level === "stores" ? permissionRows : level === "departments" ? storeRows : departmentRows;
  const currentSummaries =
    level === "stores" ? storeSummaries : level === "departments" ? departmentSummaries : groupSummaries;
  const currentTitle =
    level === "stores" ? "门店收益汇总" : level === "departments" ? "部门收益汇总" : "柜位收益明细";
  const currentChartTitle =
    level === "stores" ? "门店收益构成" : level === "departments" ? "部门收益构成" : "柜位收益构成";

  const totals = useMemo(
    () =>
      currentSummaries.reduce(
        (sum, row) => ({
          total: sum.total + row.total,
          sales: sum.sales + row.sales,
          fee: sum.fee + row.fee,
          extra: sum.extra + row.extra,
          adjustment: sum.adjustment + row.adjustment,
          tax: sum.tax + (row.tax ?? 0),
        }),
        { total: 0, sales: 0, fee: 0, extra: 0, adjustment: 0, tax: 0 },
      ),
    [currentSummaries],
  );

  const chartRows = currentSummaries.slice(0, 10);
  const currentCabinetCount = new Set(currentRows.map(groupKey)).size;
  const queryError = query.error instanceof Error ? query.error.message : "收益看板加载失败";

  const resetDrilldown = () => {
    setDetailSelection(null);
    setLevel("stores");
    setSelectedStoreKey(null);
    setSelectedDepartmentKey(null);
  };

  const drillToStore = (row: SummaryRow) => {
    setSelectedStoreKey(row.key);
    setSelectedDepartmentKey(null);
    setLevel("departments");
  };

  const drillToDepartment = (row: SummaryRow) => {
    setSelectedDepartmentKey(row.key);
    setLevel("groups");
  };

  const backToDepartments = () => {
    setDetailSelection(null);
    setSelectedDepartmentKey(null);
    setLevel("departments");
  };

  const applyFinancialPeriod = () => {
    const range = financialRange(financialYear, financialMonth);
    resetDrilldown();
    setAppliedPeriod({ year: financialYear, month: financialMonth, ...range });
  };

  const openDetail = (row: SummaryRow, mode: DetailMode) => {
    if (!selectedStoreKey || (mode !== "extras" && !row.code)) return;
    setDetailSelection({ row, mode });
  };

  const handleExport = async () => {
    if (!permissionRows.length) {
      toast({ title: "暂无数据可导出", variant: "destructive" });
      return;
    }
    setIsExporting(true);
    try {
      const params = new URLSearchParams({
        start_date: appliedPeriod.startDate,
        end_date: appliedPeriod.endDate,
        financial_year: String(appliedPeriod.year),
      });
      if (appliedPeriod.month != null) params.set("financial_month", String(appliedPeriod.month));
      const extraDetails = await apiGet<RevenueDashboardExtraExportResponse>(
        `/api/revenue-map/dashboard/extra-export-details?${params.toString()}`,
      );
      if (extraDetails.is_truncated) {
        throw new Error(
          `其他收益明细共 ${extraDetails.total_count.toLocaleString()} 条，已超过单次导出上限，请缩短日期范围后重试。`,
        );
      }
      exportRevenueDashboardExcel(
        permissionRows,
        appliedPeriod.startDate,
        appliedPeriod.endDate,
        extraDetails.items,
      );
      toast({
        title: "收益明细已导出",
        description: "已增加其他收益科目汇总和 NC 摘要明细表页。",
      });
    } catch (error) {
      console.error("导出收益看板柜组明细失败", error);
      toast({
        title: "导出失败",
        description: error instanceof Error ? error.message : "Excel 文件生成失败，请稍后重试。",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="container mx-auto space-y-5 p-4" data-testid="revenue-dashboard-page">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">收益看板</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            从门店汇总逐级钻取到部门、柜位；数据范围以当前账号权限为准。收费按付款日期统计，剔除票减及保证金，仅包含已关联付款记录的数据。
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          口径：销售毛利（不含税）＋富基收费＋NC非富基收费＋月结调整（不含税）＋税
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="grid gap-4 lg:grid-cols-[12rem_minmax(0,1fr)] lg:items-end">
            <div className="space-y-2">
              <Label htmlFor="revenue-dashboard-year">年份</Label>
              <Select value={String(financialYear)} onValueChange={(value) => setFinancialYear(Number(value))}>
                <SelectTrigger id="revenue-dashboard-year" className="w-full">
                  <SelectValue placeholder="选择年份" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 6 }, (_, index) => initialFinancialMonth.year + 1 - index).map((year) => (
                    <SelectItem key={year} value={String(year)}>{year}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0 space-y-2">
              <Label>财务月（不选月份即全年）</Label>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="财务月">
                <Button
                  type="button"
                  size="sm"
                  variant={financialMonth == null ? "default" : "outline"}
                  onClick={() => setFinancialMonth(null)}
                >
                  全年
                </Button>
                {Array.from({ length: 12 }, (_, index) => index + 1).map((month) => {
                  const window = getFinancialMonthWindow(financialYear, month);
                  return (
                    <Button
                      key={month}
                      type="button"
                      size="sm"
                      variant={financialMonth === month ? "default" : "outline"}
                      onClick={() => setFinancialMonth(month)}
                      title={`${window.start} 至 ${window.end}`}
                    >
                      {month}月
                    </Button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-foreground">
              当前选择：{financialMonth == null ? `${financialYear}全年` : `${financialYear}年第${financialMonth}财务月`}
              （{financialRange(financialYear, financialMonth).startDate} 至 {financialRange(financialYear, financialMonth).endDate}）
            </p>
            <div className="flex gap-2">
            <Button
              className="flex-1 sm:flex-none"
              onClick={applyFinancialPeriod}
              disabled={query.isFetching}
            >
              {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1 whitespace-nowrap sm:flex-none"
              onClick={handleExport}
              disabled={!permissionRows.length || query.isFetching || isExporting}
            >
              {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {isExporting ? "正在整理科目…" : "导出最明细"}
            </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {query.isLoading ? (
        <Card>
          <CardContent className="flex h-48 items-center justify-center text-muted-foreground">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在汇总权限范围内的收益数据…
          </CardContent>
        </Card>
      ) : query.isError ? (
        <Card><CardContent className="py-10 text-center text-sm text-red-600">{queryError}</CardContent></Card>
      ) : (
        <>
          {query.data?.accounting_basis !== "REALTIME" ? (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
              <div className="font-semibold">
                {query.data?.accounting_basis === "MONTH_CLOSED" ? "已采用月结含税口径" : "部分门店采用月结含税口径"}
              </div>
              <div className="mt-1 text-xs text-emerald-800">
                {(query.data?.month_closes || []).map((close) =>
                  `${close.store_name || close.store_code} ${close.period_month}：NC6051含税 ${detailMoney(close.nc_control_amount)}，税 ${detailMoney(close.accrued_tax_amount)}，月结调整（不含税） ${detailMoney(close.close_adjustment_amount - close.accrued_tax_amount)}`
                ).join("；")}
              </div>
              <div className="mt-1 text-xs text-emerald-800">
                月结调整（不含税）仅汇总待人工处理的非税差额；已自动核对、纯税和已完成分类的明细不再进入调整，计提税按NC6051明细单独汇总。
              </div>
              {latestClosedPeriodLabel ? (
                <div className="mt-1 text-xs font-medium text-emerald-900">
                  税仅累计已确认月结月份，当前截至{latestClosedPeriodLabel}月结；未关账月份不计入税列。
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {pendingBindingStoreSummaries.length ? pendingBindingStoreSummaries.map((summary) => (
                  <Button
                    key={summary.store_id}
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-amber-300 bg-white text-amber-900 hover:bg-amber-50"
                    onClick={() => {
                      setPendingBindingStoreId(summary.store_id);
                      setPendingBindingOpen(true);
                    }}
                  >
                    <Link2 className="mr-2 h-4 w-4" />
                    {summary.store_name || summary.store_code || "未命名门店"} 待核对 {summary.pending_count} 条
                  </Button>
                )) : (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-amber-300 bg-white text-amber-900 hover:bg-amber-50"
                    onClick={() => {
                      setPendingBindingStoreId(null);
                      setPendingBindingOpen(true);
                    }}
                  >
                    <Link2 className="mr-2 h-4 w-4" />
                    待双向核对 {pendingBindingQuery.data?.pending_count ?? 0} 条
                  </Button>
                )}
                <span className="text-xs text-emerald-800">
                  同时列出NC有、富基无，富基有、NC无，以及双方金额不一致的项目。
                </span>
              </div>
            </div>
          ) : (
            <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-900">
              当前为实时口径：富基收费按付款日期去税展示；期间确认月结后自动切换为NC6051含计提税控制口径。
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
            <button
              className="font-medium text-slate-900 hover:text-blue-700"
              onClick={resetDrilldown}
              data-testid="revenue-breadcrumb-stores"
            >
              门店
            </button>
            {selectedStore && (
              <>
                <ChevronRight className="h-4 w-4 text-slate-400" />
                <button
                  className="font-medium text-slate-900 hover:text-blue-700"
                  onClick={backToDepartments}
                  data-testid="revenue-breadcrumb-departments"
                >
                  {selectedStore.label}
                </button>
              </>
            )}
            {selectedDepartment && (
              <>
                <ChevronRight className="h-4 w-4 text-slate-400" />
                <span className="font-medium text-slate-900">{selectedDepartment.label}</span>
              </>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-7">
            <MetricCard title="总收益" value={money(totals.total)} note={`${appliedPeriod.startDate} 至 ${appliedPeriod.endDate}`} icon={<CircleDollarSign className="h-5 w-5" />} />
            <MetricCard title="销售毛利" value={money(totals.sales)} note="销售毛利不含税" icon={<BarChart3 className="h-5 w-5" />} />
            <MetricCard title="富基收费（调整前）" value={money(totals.fee)} note={query.data?.accounting_basis === "REALTIME" ? "按付款日期，去税；剔除票减及保证金" : "月结原始收费；剔除票减及保证金"} icon={<Building2 className="h-5 w-5" />} />
            <MetricCard title="NC非富基（调整前）" value={money(totals.extra)} note="电表、物业、营运等" icon={<CircleDollarSign className="h-5 w-5" />} />
            <MetricCard title="月结调整（不含税）" value={money(totals.adjustment)} note="仅保留NC与富基的非税差异" icon={<CircleDollarSign className="h-5 w-5" />} />
            <MetricCard title="税" value={money(totals.tax)} note={latestClosedPeriodLabel ? `NC6051计提税负数，截至${latestClosedPeriodLabel}月结` : "暂无已确认月结税额"} icon={<CircleDollarSign className="h-5 w-5" />} />
            <MetricCard title="可见柜位" value={String(currentCabinetCount)} note={`当前层级 ${currentSummaries.length} 项`} icon={<Store className="h-5 w-5" />} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{currentChartTitle}</CardTitle>
              <p className="text-xs text-muted-foreground">按总收益降序展示前 10 项，单位：元。</p>
            </CardHeader>
            <CardContent>
              {chartRows.length ? (
                <div className="h-[360px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartRows} margin={{ top: 8, right: 16, left: 4, bottom: 52 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="label" angle={-28} textAnchor="end" height={78} interval={0} tick={{ fontSize: 12 }} />
                      <YAxis tickFormatter={compactMoney} tick={{ fontSize: 12 }} />
                      <Tooltip formatter={(value: number, name: string) => [money(value), name]} />
                      <Legend />
                      <Bar dataKey="sales" name="销售毛利" stackId="revenue" fill="#2563eb" />
                      <Bar dataKey="fee" name="富基收费" stackId="revenue" fill="#d97706" />
                      <Bar dataKey="extra" name="NC非富基收费" stackId="revenue" fill="#64748b" />
                      <Bar dataKey="adjustment" name="月结调整" stackId="revenue" fill="#059669" />
                      <Bar dataKey="tax" name="税" stackId="revenue" fill="#dc2626" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                  当前层级暂无收益数据
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between p-4 pb-3">
              <div>
                <CardTitle className="text-base">{currentTitle}</CardTitle>
                <p className="mt-1 text-xs text-muted-foreground">
                  {level === "groups" ? "柜位明细为当前钻取终点。" : "点击任意一行继续向下钻取。"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="whitespace-nowrap text-xs text-muted-foreground">金额单位：万元</span>
                {level === "departments" && (
                  <Button variant="ghost" size="sm" onClick={resetDrilldown}>返回门店</Button>
                )}
                {level === "groups" && (
                  <Button variant="ghost" size="sm" onClick={backToDepartments}>返回部门</Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="overflow-x-auto px-4 pb-4 pt-0">
              <Table className="table-fixed text-xs [&_td]:px-2 [&_td]:py-3 [&_th]:h-9 [&_th]:px-2 lg:text-sm">
                <colgroup>
                  <col style={{ width: level === "stores" ? "14%" : level === "departments" ? "16%" : "15%" }} />
                  {level === "stores" && <col style={{ width: "6%" }} />}
                  <col style={{ width: level === "stores" ? "6%" : level === "departments" ? "7%" : "12%" }} />
                  <col style={{ width: level === "stores" ? "9%" : "10%" }} />
                  <col style={{ width: level === "stores" ? "9%" : "10%" }} />
                  <col style={{ width: level === "stores" ? "11%" : "12%" }} />
                  <col style={{ width: level === "stores" ? "12%" : "13%" }} />
                  <col style={{ width: level === "stores" ? "7%" : "8%" }} />
                  <col style={{ width: level === "stores" ? "12%" : level === "departments" ? "13%" : "12%" }} />
                  <col style={{ width: level === "stores" ? "10%" : "8%" }} />
                  {level !== "groups" && <col style={{ width: level === "stores" ? "4%" : "3%" }} />}
                </colgroup>
                <TableHeader>
                  <TableRow className="border-b-0 bg-slate-50/70">
                    <TableHead colSpan={level === "stores" ? 3 : 2} />
                    <TableHead className="border-l text-center font-semibold text-slate-700">
                      销售收益
                    </TableHead>
                    <TableHead colSpan={5} className="border-l text-center font-semibold text-slate-700">
                      其他业务收入
                    </TableHead>
                    <TableHead className="border-l" />
                    {level !== "groups" && <TableHead />}
                  </TableRow>
                  <TableRow>
                    <TableHead>{level === "stores" ? "门店" : level === "departments" ? "部门" : "柜位"}</TableHead>
                    {level === "stores" && <TableHead className="text-right">部门数</TableHead>}
                    {level !== "groups" && <TableHead className="text-right">柜位数</TableHead>}
                    {level === "groups" && <TableHead>图上经营单元</TableHead>}
                    <TableHead className="border-l text-right whitespace-nowrap">销售毛利</TableHead>
                    <TableHead className="border-l text-right whitespace-nowrap">富基收费</TableHead>
                    <TableHead className="text-right whitespace-nowrap">NC非富基收费</TableHead>
                    <TableHead className="text-right whitespace-nowrap">月结调整（不含税）</TableHead>
                    <TableHead className="text-right whitespace-nowrap">税</TableHead>
                    <TableHead className="text-right whitespace-nowrap">其他业务收入合计</TableHead>
                    <TableHead className="border-l text-right whitespace-nowrap">总收益</TableHead>
                    {level !== "groups" && <TableHead className="w-10" />}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentSummaries.length ? currentSummaries.map((row) => (
                    <TableRow
                      key={row.key}
                      className={level === "groups" ? "" : "cursor-pointer hover:bg-slate-50"}
                      onClick={() => {
                        if (level === "stores") drillToStore(row);
                        if (level === "departments") drillToDepartment(row);
                      }}
                      data-testid={`revenue-${level}-row-${row.key}`}
                    >
                      <TableCell>
                        <div className="font-medium">{row.label}</div>
                        <div className="text-xs text-muted-foreground">{row.code || "无编码"}</div>
                      </TableCell>
                      {level === "stores" && <TableCell className="text-right">{row.department_count}</TableCell>}
                      {level !== "groups" && <TableCell className="text-right">{row.group_count}</TableCell>}
                      {level === "groups" && <TableCell>{row.unit_codes || "—"}</TableCell>}
                      <TableCell className="border-l text-right whitespace-nowrap tabular-nums">
                        {level === "groups" && row.code ? (
                          <button
                            type="button"
                            className="font-medium text-blue-700 underline-offset-4 hover:underline"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDetail(row, "gross-profit");
                            }}
                            aria-label={`查看${row.label}每日毛利明细`}
                          >
                            {tenThousandMoney(row.sales)}
                          </button>
                        ) : tenThousandMoney(row.sales)}
                      </TableCell>
                      <TableCell className="border-l text-right whitespace-nowrap tabular-nums">
                        {level === "groups" && row.code ? (
                          <button
                            type="button"
                            className="font-medium text-blue-700 underline-offset-4 hover:underline"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDetail(row, "fees");
                            }}
                            aria-label={`查看${row.label}费用明细`}
                          >
                            {tenThousandMoney(row.fee)}
                          </button>
                        ) : tenThousandMoney(row.fee)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap tabular-nums">
                        {level === "groups" && row.extra !== 0 ? (
                          <button
                            type="button"
                            className="font-medium text-blue-700 underline-offset-4 hover:underline"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDetail(row, "extras");
                            }}
                            aria-label={`查看${row.label}其他收益科目及摘要明细`}
                          >
                            {tenThousandMoney(row.extra)}
                          </button>
                        ) : tenThousandMoney(row.extra)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap tabular-nums">
                        {row.adjustment === 0 ? "—" : tenThousandMoney(row.adjustment)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap tabular-nums">
                        {row.tax == null || row.tax === 0 ? "—" : tenThousandMoney(row.tax)}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap font-medium tabular-nums">
                        {row.nc_6051_amount == null ? "—" : tenThousandMoney(otherBusinessIncomeTotal(row))}
                      </TableCell>
                      <TableCell className="border-l text-right whitespace-nowrap font-semibold tabular-nums">{tenThousandMoney(row.total)}</TableCell>
                      {level !== "groups" && (
                        <TableCell><ChevronRight className="h-4 w-4 text-slate-400" /></TableCell>
                      )}
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell
                        colSpan={level === "stores" ? 11 : level === "departments" ? 10 : 9}
                        className="h-24 text-center text-muted-foreground"
                      >
                        当前层级暂无收益数据
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Sheet
            open={pendingBindingOpen}
            onOpenChange={(open) => {
              setPendingBindingOpen(open);
              if (!open) setPendingBindingStoreId(null);
            }}
          >
            <SheetContent className="z-[70] flex w-full flex-col overflow-hidden bg-white p-0 sm:max-w-[96vw]">
              <SheetHeader className="border-b px-5 py-4 pr-12">
                <SheetTitle>
                  {selectedPendingBindingStore?.store_name || selectedPendingBindingStore?.store_code
                    ? `${selectedPendingBindingStore.store_name || selectedPendingBindingStore.store_code}月结双向核对及待人工绑定明细`
                    : "月结双向核对及待人工绑定明细"}
                </SheetTitle>
                <SheetDescription>
                  计提税不参与待核对和柜位绑定，统一保留在门店月结税额中；富基同源单、同柜组、同供应商、同费用项、同审核日期且金额一正一负的明细先内部对冲，剩余明细按同部门、同科目、同供应商汇总后再与NC匹配。富基00开头的销售行，以及37代付费用、保证金、质保金、38代扣代缴保险费不参与核对；2025年1月至2026年6月各门店物业部和营运部的NC费用按非富基收费处理，不参与匹配。每条未匹配来源明细需选择计入富基收费或NC非富基收费，再绑定柜位并确认本月对应柜组；确认后该笔非税差额从月结调整转入所选收益分类。
                </SheetDescription>
              </SheetHeader>
              <div className="flex min-h-0 flex-1 flex-col p-5">
                {pendingBindingQuery.isLoading ? (
                  <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载待绑定明细…
                  </div>
                ) : pendingBindingQuery.isError ? (
                  <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                    待绑定明细加载失败：{pendingBindingQuery.error instanceof Error ? pendingBindingQuery.error.message : "请稍后重试"}
                  </div>
                ) : displayedPendingBindingItems.length ? (
                  <div className="flex min-h-0 flex-1 flex-col gap-3">
                    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                      <div>
                        共 {displayedPendingBindingCount} 组差异、{displayedPendingBindingLineCount} 条待绑定来源明细，
                        非税差额合计 {detailMoney(displayedPendingBindingAmount)}。
                      </div>
                      <div className="mt-1 text-xs">
                        NC有、富基无 {displayedPendingBindingDirectionSummary?.NC_ONLY.count ?? 0} 条；
                        富基有、NC无 {displayedPendingBindingDirectionSummary?.FUJI_ONLY.count ?? 0} 条；
                        双方金额不一致 {displayedPendingBindingDirectionSummary?.AMOUNT_DIFFERENCE.count ?? 0} 条。
                      </div>
                      {displayedAutoMatchedCount > 0 ? (
                        <div className="mt-1 text-xs text-emerald-800">
                          系统已自动核对隐藏 {displayedAutoMatchedCount} 组富基内部对冲或供应商与金额一致的费用，
                          合计 {detailMoney(displayedAutoMatchedAmount)}；下表只展示未匹配源行和仍需处理的差额。
                        </div>
                      ) : null}
                    </div>
                    <ScrollArea
                      type="always"
                      horizontal
                      className="min-h-0 flex-1 rounded-md border bg-white"
                    >
                      <Table containerClassName="overflow-visible pb-3 pr-3">
                        <TableHeader>
                          <TableRow>
                            <TableHead className="min-w-32">门店</TableHead>
                            <TableHead className="min-w-40">部门／科目</TableHead>
                            <TableHead className="min-w-80">富基费用未匹配</TableHead>
                            <TableHead className="min-w-80">NC费用未匹配</TableHead>
                            <TableHead className="min-w-36">差异方向</TableHead>
                            <TableHead className="text-right">对比原金额</TableHead>
                            <TableHead className="text-right">NC非税目标金额</TableHead>
                            <TableHead className="text-right">待绑定非税差额</TableHead>
                            <TableHead className="min-w-64">差异说明</TableHead>
                            <TableHead className="min-w-40">本次绑定金额</TableHead>
                            <TableHead className="min-w-52">计入收益分类</TableHead>
                            <TableHead className="min-w-64">绑定柜位</TableHead>
                            <TableHead className="min-w-72">关联柜组</TableHead>
                            <TableHead className="w-24">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {displayedPendingBindingItems.map((item) => {
                            const unitOptions = (pendingBindingQuery.data?.unit_options ?? []).filter(
                              (option) => option.store_id === item.store_id,
                            );
                            const bindingLines = item.binding_lines ?? [];
                            return (
                              <TableRow key={item.id}>
                                <TableCell>
                                  <div className="font-medium">{item.store_name || item.store_code}</div>
                                  <div className="text-xs text-muted-foreground">{item.period_month}</div>
                                </TableCell>
                                <TableCell>
                                  <div>{item.department_name || item.department_code || "未归属部门"}</div>
                                  <div className="text-xs text-muted-foreground">
                                    {item.source_subject_code || "—"} {item.source_subject_name || item.fee_type_name || "未映射科目"}
                                  </div>
                                </TableCell>
                                <TableCell className="align-top">
                                  <FujiSideDetails
                                    details={item.fuji_details ?? []}
                                    count={item.fuji_detail_count ?? 0}
                                    amount={item.fuji_detail_amount ?? 0}
                                  />
                                </TableCell>
                                <TableCell className="align-top">
                                  <NcSideDetails
                                    details={item.nc_details ?? []}
                                    count={item.nc_detail_count ?? 0}
                                    amount={item.nc_detail_amount ?? 0}
                                  />
                                </TableCell>
                                <TableCell>
                                  <div className="font-medium">
                                    {item.difference_direction === "NC_ONLY"
                                      ? "NC有、富基无"
                                      : item.difference_direction === "FUJI_ONLY"
                                        ? "富基有、NC无"
                                        : item.difference_direction === "AMOUNT_DIFFERENCE"
                                          ? "双方金额不一致"
                                          : "其他差异"}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {item.adjustment_category} · {item.supplier_name || item.fee_type_name || item.target_component}
                                  </div>
                                  {item.auto_matched_count > 0 ? (
                                    <div className="mt-1 text-xs text-emerald-700">
                                      已自动核对 {item.auto_matched_count} 组／{detailMoney(item.auto_matched_amount)}
                                    </div>
                                  ) : null}
                                </TableCell>
                                <TableCell className="whitespace-nowrap text-right tabular-nums">{detailMoney(item.raw_amount)}</TableCell>
                                <TableCell className="whitespace-nowrap text-right tabular-nums">{detailMoney(item.final_amount)}</TableCell>
                                <TableCell className="whitespace-nowrap text-right font-semibold tabular-nums">{detailMoney(item.adjustment_amount)}</TableCell>
                                <TableCell className="text-xs">
                                  <div>{item.adjustment_reason || "—"}</div>
                                  <div className="mt-1 text-muted-foreground">{item.allocation_basis || "不分摊"}</div>
                                </TableCell>
                                <TableCell>
                                  <div className="divide-y">
                                    {bindingLines.map((line, lineIndex) => (
                                      <div key={line.source_line_key} className="min-h-28 py-2 first:pt-0 last:pb-0">
                                        <div className="text-xs text-muted-foreground">
                                          {line.source_type === "NC" ? "NC明细" : line.source_type === "FUJI" ? "富基明细" : "差异明细"} {lineIndex + 1}
                                        </div>
                                        <div className="mt-1 whitespace-nowrap font-semibold tabular-nums">
                                          {detailMoney(line.suggested_binding_amount)}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">按来源行逐笔绑定</div>
                                      </div>
                                    ))}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="divide-y">
                                    {bindingLines.map((line) => {
                                      const bindingKey = `${item.id}:${line.source_line_key}`;
                                      const selectedTarget = bindingTargetByLine[bindingKey];
                                      return (
                                        <div key={line.source_line_key} className="min-h-28 py-2 first:pt-0 last:pb-0">
                                          <Select
                                            value={selectedTarget || ""}
                                            onValueChange={(value: "FEE" | "EXTRA") => setBindingTargetByLine((current) => ({
                                              ...current,
                                              [bindingKey]: value,
                                            }))}
                                          >
                                            <SelectTrigger aria-label="选择计入收益分类">
                                              <SelectValue placeholder="选择收费分类" />
                                            </SelectTrigger>
                                            <SelectContent>
                                              <SelectItem value="FEE">计入富基收费</SelectItem>
                                              <SelectItem value="EXTRA">计入NC非富基收费</SelectItem>
                                            </SelectContent>
                                          </Select>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="divide-y">
                                    {bindingLines.map((line) => {
                                      const bindingKey = `${item.id}:${line.source_line_key}`;
                                      const selectedUnit = bindingUnitByLine[bindingKey] || "";
                                      return (
                                        <div key={line.source_line_key} className="min-h-28 py-2 first:pt-0 last:pb-0">
                                          <Select
                                            value={selectedUnit}
                                            onValueChange={(value) => {
                                              const selectedOption = unitOptions.find((option) => String(option.unit_id) === value);
                                              setBindingUnitByLine((current) => ({ ...current, [bindingKey]: value }));
                                              setBindingGroupByLine((current) => ({
                                                ...current,
                                                [bindingKey]: selectedOption?.group_options.length === 1
                                                  ? selectedOption.group_options[0].group_code
                                                  : "",
                                              }));
                                            }}
                                          >
                                            <SelectTrigger aria-label="选择绑定柜位">
                                              <SelectValue placeholder="选择柜位" />
                                            </SelectTrigger>
                                            <SelectContent>
                                              {unitOptions.map((option) => (
                                                <SelectItem
                                                  key={option.unit_id}
                                                  value={String(option.unit_id)}
                                                  disabled={!option.group_options.length}
                                                >
                                                  {option.unit_code}{option.floor_name ? ` · ${option.floor_name}` : ""}
                                                  {!option.group_options.length ? " · 未关联柜组" : ""}
                                                </SelectItem>
                                              ))}
                                            </SelectContent>
                                          </Select>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="divide-y">
                                    {bindingLines.map((line) => {
                                      const bindingKey = `${item.id}:${line.source_line_key}`;
                                      const selectedUnit = bindingUnitByLine[bindingKey] || "";
                                      const unitOption = unitOptions.find((option) => String(option.unit_id) === selectedUnit);
                                      const selectedGroup = bindingGroupByLine[bindingKey] || "";
                                      return (
                                        <div key={line.source_line_key} className="min-h-28 py-2 first:pt-0 last:pb-0">
                                          <Select
                                            value={selectedGroup}
                                            onValueChange={(value) => setBindingGroupByLine((current) => ({
                                              ...current,
                                              [bindingKey]: value,
                                            }))}
                                            disabled={!unitOption}
                                          >
                                            <SelectTrigger aria-label="选择关联柜组">
                                              <SelectValue placeholder={unitOption ? "选择柜组" : "先选择柜位"} />
                                            </SelectTrigger>
                                            <SelectContent>
                                              {(unitOption?.group_options ?? []).map((group) => (
                                                <SelectItem key={group.group_code} value={group.group_code}>
                                                  {group.group_code} · {group.group_name}
                                                </SelectItem>
                                              ))}
                                            </SelectContent>
                                          </Select>
                                          {unitOption && !unitOption.group_options.length ? (
                                            <div className="mt-1 text-xs text-red-600">该柜位未维护对应柜组</div>
                                          ) : null}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="divide-y">
                                    {bindingLines.map((line) => {
                                      const bindingKey = `${item.id}:${line.source_line_key}`;
                                      const selectedTarget = bindingTargetByLine[bindingKey];
                                      const selectedUnit = bindingUnitByLine[bindingKey] || "";
                                      const selectedGroup = bindingGroupByLine[bindingKey] || "";
                                      const isBinding = bindDifferenceMutation.isPending
                                        && bindDifferenceMutation.variables?.adjustmentId === item.id
                                        && bindDifferenceMutation.variables?.sourceLineKey === line.source_line_key;
                                      const validBindingAmount = Number.isFinite(line.suggested_binding_amount)
                                        && line.suggested_binding_amount !== 0;
                                      return (
                                        <div key={line.source_line_key} className="min-h-28 py-2 first:pt-0 last:pb-0">
                                          <Button
                                            type="button"
                                            size="sm"
                                            disabled={!selectedTarget || !selectedUnit || !selectedGroup || !validBindingAmount || isBinding}
                                            onClick={() => {
                                              if (!selectedTarget) return;
                                              bindDifferenceMutation.mutate({
                                                adjustmentId: item.id,
                                                targetComponent: selectedTarget,
                                                unitId: Number(selectedUnit),
                                                sourceGroupCode: selectedGroup,
                                                sourceLineKey: line.source_line_key,
                                                adjustmentAmount: line.suggested_binding_amount,
                                              });
                                            }}
                                          >
                                            {isBinding ? <Loader2 className="h-4 w-4 animate-spin" /> : "确认绑定"}
                                          </Button>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </ScrollArea>
                  </div>
                ) : (
                  <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                    当前财务期间没有NC与富基的双向待核对差异。
                  </div>
                )}
              </div>
            </SheetContent>
          </Sheet>

          <Sheet
            open={Boolean(detailSelection)}
            onOpenChange={(open) => {
              if (!open) setDetailSelection(null);
            }}
          >
            <SheetContent className="z-[60] flex w-full flex-col overflow-hidden bg-white p-0 sm:max-w-5xl">
              <SheetHeader className="border-b px-5 py-4 pr-12">
                <SheetTitle>
                  {detailSelection?.row.label}
                  {detailSelection?.mode === "gross-profit"
                    ? " · 每日毛利明细"
                    : detailSelection?.mode === "fees"
                      ? " · 费用明细"
                      : " · 其他收益科目及摘要明细"}
                </SheetTitle>
                <SheetDescription>
                  柜位 {detailSelection?.row.code || detailSelection?.row.unit_codes || "后台部门收益"} · {appliedPeriod.startDate} 至 {appliedPeriod.endDate}
                  {detailSelection?.mode === "fees"
                    ? " · 按付款日期"
                    : detailSelection?.mode === "extras"
                      ? " · 按收益确认日期"
                      : ""}
                </SheetDescription>
              </SheetHeader>
              <div className="min-h-0 flex-1 overflow-auto p-5">
                {(detailSelection?.mode === "extras" ? extraDetailQuery.isLoading : detailQuery.isLoading) ? (
                  <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载明细…
                  </div>
                ) : (detailSelection?.mode === "extras" ? extraDetailQuery.isError : detailQuery.isError) ? (
                  <div className="py-10 text-center text-sm text-red-600">
                    {detailSelection?.mode === "extras"
                      ? extraDetailQuery.error instanceof Error
                        ? extraDetailQuery.error.message
                        : "其他收益明细加载失败"
                      : detailQuery.error instanceof Error
                        ? detailQuery.error.message
                        : "明细加载失败"}
                  </div>
                ) : detailQuery.data && detailSelection?.mode === "gross-profit" ? (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">柜位表销售毛利</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailSelection.row.sales)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">每日明细合计</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailQuery.data.gross_profit.total_amount)}</div>
                      </div>
                    </div>
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>收益日期</TableHead>
                            <TableHead className="text-right">来源笔数</TableHead>
                            <TableHead className="text-right">销售毛利</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {detailQuery.data.gross_profit.items.length ? (
                            detailQuery.data.gross_profit.items.map((item) => (
                              <TableRow key={item.revenue_date}>
                                <TableCell>{item.revenue_date?.slice(0, 10)}</TableCell>
                                <TableCell className="text-right">{item.source_count}</TableCell>
                                <TableCell className="text-right font-medium tabular-nums">
                                  {money(item.gross_profit_amount)}
                                </TableCell>
                              </TableRow>
                            ))
                          ) : (
                            <TableRow>
                              <TableCell colSpan={3} className="h-24 text-center text-muted-foreground">
                                当前日期范围暂无销售毛利明细
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      每日明细与柜位表使用相同口径，包含已计入销售毛利的损失承担。
                    </p>
                  </div>
                ) : detailQuery.data && detailSelection?.mode === "fees" ? (
                  <div className="space-y-4">
                    <div className="grid gap-3 sm:grid-cols-4">
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">柜位表费用收益</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailSelection.row.fee)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">富基原金额</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailQuery.data.fees.raw_total_amount)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">月结调整</div>
                        <div className="mt-1 text-xl font-semibold">{detailMoney(detailQuery.data.fees.adjustment_amount)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">费用笔数</div>
                        <div className="mt-1 text-xl font-semibold">{detailQuery.data.fees.total_count}</div>
                      </div>
                    </div>
                    <div className="overflow-x-auto rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="whitespace-nowrap">付款日期</TableHead>
                            <TableHead className="whitespace-nowrap">付款单号</TableHead>
                            <TableHead className="whitespace-nowrap">结算单号</TableHead>
                            <TableHead className="whitespace-nowrap">合同</TableHead>
                            <TableHead className="min-w-44">费用项目</TableHead>
                            <TableHead className="whitespace-nowrap text-right">含税金额</TableHead>
                            <TableHead className="whitespace-nowrap text-right">不含税金额</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {detailQuery.data.fees.items.length ? (
                            detailQuery.data.fees.items.map((item) => (
                              <TableRow key={item.id}>
                                <TableCell className="whitespace-nowrap">{item.revenue_date?.slice(0, 10)}</TableCell>
                                <TableCell className="whitespace-nowrap font-medium">{item.payment_no || "—"}</TableCell>
                                <TableCell className="whitespace-nowrap font-medium">{item.settlement_no || "—"}</TableCell>
                                <TableCell>
                                  <div className="whitespace-nowrap">{item.contract_code || "—"}</div>
                                  <div className="text-xs text-muted-foreground">{item.contract_name || ""}</div>
                                </TableCell>
                                <TableCell>
                                  <div>{item.fee_type_name || "未命名费用"}</div>
                                  <div className="text-xs text-muted-foreground">{item.fee_type_code || "—"}</div>
                                </TableCell>
                                <TableCell className="whitespace-nowrap text-right tabular-nums">
                                  {money(item.tax_included_amount)}
                                </TableCell>
                                <TableCell className="whitespace-nowrap text-right font-medium tabular-nums">
                                  {money(item.tax_excluded_amount)}
                                </TableCell>
                              </TableRow>
                            ))
                          ) : (
                            <TableRow>
                              <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                                当前付款日期范围暂无费用明细
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    {detailQuery.data.fees.is_truncated ? (
                      <p className="text-xs text-amber-700">
                        共 {detailQuery.data.fees.total_count} 条，当前显示前 {detailQuery.data.fees.returned_count} 条。
                      </p>
                    ) : null}
                    {detailQuery.data.fees.month_close_adjustments.length ? (
                      <div className="space-y-2">
                        <div>
                          <h3 className="text-sm font-semibold">月结含税调整明细</h3>
                          <p className="text-xs text-muted-foreground">保留富基原金额，按NC部门＋6051科目把计提税和调平差异分配到柜位。</p>
                        </div>
                        <div className="overflow-x-auto rounded-md border">
                          <Table>
                            <TableHeader><TableRow>
                              <TableHead>调整类别</TableHead><TableHead>NC科目</TableHead><TableHead>收费项目</TableHead>
                              <TableHead className="text-right">原金额</TableHead><TableHead className="text-right">计提税</TableHead>
                              <TableHead className="text-right">月结调整</TableHead><TableHead className="text-right">调平后</TableHead>
                            </TableRow></TableHeader>
                            <TableBody>{detailQuery.data.fees.month_close_adjustments.map((item) => (
                              <TableRow key={item.id}>
                                <TableCell>{item.adjustment_category}</TableCell>
                                <TableCell><div>{item.subject_name || "—"}</div><div className="text-xs text-muted-foreground">{item.subject_code || "—"}</div></TableCell>
                                <TableCell><div>{item.fee_type_name || "—"}</div><div className="text-xs text-muted-foreground">{item.fee_type_code || "—"}</div></TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.raw_amount)}</TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.accrued_tax_amount)}</TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.adjustment_amount)}</TableCell>
                                <TableCell className="text-right font-medium tabular-nums">{detailMoney(item.final_amount)}</TableCell>
                              </TableRow>
                            ))}</TableBody>
                          </Table>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : extraDetailQuery.data && detailSelection?.mode === "extras" ? (
                  <div className="space-y-5">
                    <div className="grid gap-3 sm:grid-cols-4">
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">柜位表其他收益</div>
                        <div className="mt-1 text-xl font-semibold">{detailMoney(detailSelection.row.extra)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">NC原金额</div>
                        <div className="mt-1 text-xl font-semibold">{detailMoney(extraDetailQuery.data.raw_total_amount)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">计提税/月结调整</div>
                        <div className="mt-1 text-xl font-semibold">{detailMoney(extraDetailQuery.data.adjustment_amount)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">NC 明细笔数</div>
                        <div className="mt-1 text-xl font-semibold">{extraDetailQuery.data.total_count}</div>
                      </div>
                    </div>

                    {extraDetailQuery.data.month_close_adjustments.length ? (
                      <div className="space-y-2">
                        <div>
                          <h3 className="text-sm font-semibold">NC非富基月结调整</h3>
                          <p className="text-xs text-muted-foreground">计提税按NC部门＋6051科目分配到对应柜位或后台部门。</p>
                        </div>
                        <div className="overflow-x-auto rounded-md border">
                          <Table>
                            <TableHeader><TableRow>
                              <TableHead>调整类别</TableHead><TableHead>NC科目</TableHead>
                              <TableHead className="text-right">原金额</TableHead><TableHead className="text-right">计提税</TableHead>
                              <TableHead className="text-right">月结调整</TableHead><TableHead className="text-right">调平后</TableHead>
                            </TableRow></TableHeader>
                            <TableBody>{extraDetailQuery.data.month_close_adjustments.map((item) => (
                              <TableRow key={item.id}>
                                <TableCell>{item.adjustment_category}</TableCell>
                                <TableCell><div>{item.subject_name || "—"}</div><div className="text-xs text-muted-foreground">{item.subject_code || "—"}</div></TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.raw_amount)}</TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.accrued_tax_amount)}</TableCell>
                                <TableCell className="text-right tabular-nums">{detailMoney(item.adjustment_amount)}</TableCell>
                                <TableCell className="text-right font-medium tabular-nums">{detailMoney(item.final_amount)}</TableCell>
                              </TableRow>
                            ))}</TableBody>
                          </Table>
                        </div>
                      </div>
                    ) : null}

                    <div className="space-y-2">
                      <div>
                        <h3 className="text-sm font-semibold">科目明细</h3>
                        <p className="text-xs text-muted-foreground">按 NC 6051 科目汇总，科目名称取 NC 科目档案。</p>
                      </div>
                      <div className="overflow-x-auto rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="whitespace-nowrap">科目编码</TableHead>
                              <TableHead className="min-w-40">科目名称</TableHead>
                              <TableHead className="whitespace-nowrap text-right">明细笔数</TableHead>
                              <TableHead className="whitespace-nowrap text-right">科目金额</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {extraDetailQuery.data.subjects.length ? (
                              extraDetailQuery.data.subjects.map((subject) => (
                                <TableRow key={`${subject.subject_code}-${subject.subject_name}`}>
                                  <TableCell className="whitespace-nowrap font-medium">{subject.subject_code}</TableCell>
                                  <TableCell>{subject.subject_name}</TableCell>
                                  <TableCell className="text-right">{subject.detail_count}</TableCell>
                                  <TableCell className="whitespace-nowrap text-right font-medium tabular-nums">
                                    {detailMoney(subject.amount)}
                                  </TableCell>
                                </TableRow>
                              ))
                            ) : (
                              <TableRow>
                                <TableCell colSpan={4} className="h-20 text-center text-muted-foreground">
                                  当前日期范围暂无科目明细
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div>
                        <h3 className="text-sm font-semibold">摘要明细</h3>
                        <p className="text-xs text-muted-foreground">保留 NC 凭证、来源部门、摘要和柜位归属，金额按贷方减借方。</p>
                      </div>
                      <div className="overflow-x-auto rounded-md border">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead className="whitespace-nowrap">确认日期</TableHead>
                              <TableHead className="min-w-40">科目</TableHead>
                              <TableHead className="min-w-72">摘要</TableHead>
                              <TableHead className="min-w-40">来源部门</TableHead>
                              <TableHead className="whitespace-nowrap">NC凭证</TableHead>
                              <TableHead className="min-w-36">柜位归属</TableHead>
                              <TableHead className="whitespace-nowrap text-right">金额</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {extraDetailQuery.data.items.length ? (
                              extraDetailQuery.data.items.map((item) => (
                                <TableRow key={item.id}>
                                  <TableCell className="whitespace-nowrap">{item.revenue_date?.slice(0, 10)}</TableCell>
                                  <TableCell>
                                    <div className="font-medium">{item.subject_name || item.extra_type || "未命名科目"}</div>
                                    <div className="text-xs text-muted-foreground">{item.subject_code || "未编码"}</div>
                                  </TableCell>
                                  <TableCell className="max-w-md whitespace-normal break-words">{item.explanation || "—"}</TableCell>
                                  <TableCell>
                                    <div>{item.department_name || "—"}</div>
                                    <div className="text-xs text-muted-foreground">{item.department_code || "—"}</div>
                                  </TableCell>
                                  <TableCell className="whitespace-nowrap font-medium">{item.voucher_no || "—"}</TableCell>
                                  <TableCell>
                                    <div>{item.source_group_name || item.unit_code || "后台部门收益"}</div>
                                    <div className="text-xs text-muted-foreground">
                                      {item.source_group_code || item.match_method || "—"}
                                    </div>
                                  </TableCell>
                                  <TableCell className="whitespace-nowrap text-right font-medium tabular-nums">
                                    {detailMoney(item.amount)}
                                  </TableCell>
                                </TableRow>
                              ))
                            ) : (
                              <TableRow>
                                <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                                  当前日期范围暂无摘要明细
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                    {extraDetailQuery.data.is_truncated ? (
                      <p className="text-xs text-amber-700">
                        共 {extraDetailQuery.data.total_count} 条，当前显示前 {extraDetailQuery.data.returned_count} 条。
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </SheetContent>
          </Sheet>
        </>
      )}
    </div>
  );
}
