import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Building2, ChevronRight, CircleDollarSign, Download, Loader2, Search, Store } from "lucide-react";
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
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { apiGet } from "@/lib/api";
import {
  exportRevenueDashboardExcel,
  type RevenueDashboardFeeBreakdown,
} from "@/lib/revenue-dashboard-export";

type RevenueDashboardItem = {
  store_id: number;
  store_code?: string | null;
  store_name?: string | null;
  department_code?: string | null;
  department_name: string;
  group_code?: string | null;
  group_name: string;
  unit_codes?: string | null;
  unit_count: number;
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
    extra: "revenue_date";
  };
  fee_scope_note: string;
  items: RevenueDashboardItem[];
};

type SummaryRow = {
  key: string;
  label: string;
  code?: string | null;
  department_count: number;
  group_count: number;
  unit_codes?: string | null;
  sales: number;
  fee: number;
  extra: number;
  total: number;
};

type DrillLevel = "stores" | "departments" | "groups";
type DetailMode = "gross-profit" | "fees";

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
    total_amount: number;
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

const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const monthStart = () => {
  const now = new Date();
  return isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
};

const money = (value: number) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(value || 0);

const compactMoney = (value: number) => {
  const absolute = Math.abs(value);
  if (absolute >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (absolute >= 10000) return `${(value / 10000).toFixed(1)}万`;
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value);
};

const departmentKey = (row: RevenueDashboardItem) =>
  row.department_code || `name:${row.department_name}`;

const groupKey = (row: RevenueDashboardItem) =>
  row.group_code || `unit:${row.unit_codes || row.group_name}`;

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
      department_count: 0,
      group_count: 0,
      sales: 0,
      fee: 0,
      extra: 0,
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
    target.sales += row.sales_gross_profit_amount;
    target.fee += row.fee_amount;
    target.extra += row.extra_amount;
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
  const [startDate, setStartDate] = useState(monthStart);
  const [endDate, setEndDate] = useState(() => isoDate(new Date()));
  const [appliedRange, setAppliedRange] = useState({ startDate, endDate });
  const [level, setLevel] = useState<DrillLevel>("stores");
  const [selectedStoreKey, setSelectedStoreKey] = useState<string | null>(null);
  const [selectedDepartmentKey, setSelectedDepartmentKey] = useState<string | null>(null);
  const [detailSelection, setDetailSelection] = useState<{ row: SummaryRow; mode: DetailMode } | null>(null);

  const query = useQuery({
    queryKey: ["revenue-dashboard", appliedRange.startDate, appliedRange.endDate],
    queryFn: () =>
      apiGet<RevenueDashboardResponse>(
        `/api/revenue-map/dashboard?start_date=${appliedRange.startDate}&end_date=${appliedRange.endDate}`,
      ),
    enabled: Boolean(appliedRange.startDate && appliedRange.endDate),
  });

  const detailQuery = useQuery({
    queryKey: [
      "revenue-dashboard-group-detail",
      selectedStoreKey,
      detailSelection?.row.code,
      detailSelection?.mode,
      appliedRange.startDate,
      appliedRange.endDate,
    ],
    queryFn: () => {
      const groupCode = detailSelection?.row.code;
      if (!selectedStoreKey || !groupCode) throw new Error("缺少门店或柜位编码");
      const params = new URLSearchParams({
        store_id: selectedStoreKey,
        start_date: appliedRange.startDate,
        end_date: appliedRange.endDate,
        detail_type: detailSelection?.mode || "all",
      });
      return apiGet<RevenueDashboardGroupDetail>(
        `/api/revenue-map/dashboard/groups/${encodeURIComponent(groupCode)}/details?${params.toString()}`,
      );
    },
    enabled: Boolean(selectedStoreKey && detailSelection?.row.code),
  });

  const permissionRows = query.data?.items ?? [];
  const storeSummaries = useMemo(
    () =>
      aggregateRows(
        permissionRows,
        (row) => String(row.store_id),
        (row) => row.store_name || row.store_code || String(row.store_id),
        (row) => row.store_code,
      ),
    [permissionRows],
  );

  const selectedStore = storeSummaries.find((row) => row.key === selectedStoreKey) ?? null;
  const storeRows = useMemo(
    () => permissionRows.filter((row) => selectedStoreKey == null || String(row.store_id) === selectedStoreKey),
    [permissionRows, selectedStoreKey],
  );
  const departmentSummaries = useMemo(
    () =>
      aggregateRows(
        storeRows,
        departmentKey,
        (row) => row.department_name,
        (row) => row.department_code,
      ),
    [storeRows],
  );

  const selectedDepartment =
    departmentSummaries.find((row) => row.key === selectedDepartmentKey) ?? null;
  const departmentRows = useMemo(
    () => storeRows.filter((row) => selectedDepartmentKey == null || departmentKey(row) === selectedDepartmentKey),
    [selectedDepartmentKey, storeRows],
  );
  const groupSummaries = useMemo(
    () =>
      aggregateRows(
        departmentRows,
        groupKey,
        (row) => row.group_name || row.group_code || "未归属柜位",
        (row) => row.group_code,
      ),
    [departmentRows],
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
      currentRows.reduce(
        (sum, row) => ({
          total: sum.total + row.total_amount,
          sales: sum.sales + row.sales_gross_profit_amount,
          fee: sum.fee + row.fee_amount,
          extra: sum.extra + row.extra_amount,
        }),
        { total: 0, sales: 0, fee: 0, extra: 0 },
      ),
    [currentRows],
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

  const applyDateRange = () => {
    if (!startDate || !endDate || endDate < startDate) return;
    resetDrilldown();
    setAppliedRange({ startDate, endDate });
  };

  const openDetail = (row: SummaryRow, mode: DetailMode) => {
    if (!selectedStoreKey || !row.code) return;
    setDetailSelection({ row, mode });
  };

  const handleExport = () => {
    if (!permissionRows.length) {
      toast({ title: "暂无数据可导出", variant: "destructive" });
      return;
    }
    try {
      exportRevenueDashboardExcel(
        permissionRows,
        appliedRange.startDate,
        appliedRange.endDate,
      );
      toast({
        title: "收益明细已导出",
        description: "已按门店、部门、柜组展开各项去税收费列。",
      });
    } catch (error) {
      console.error("导出收益看板柜组明细失败", error);
      toast({
        title: "导出失败",
        description: "Excel 文件生成失败，请稍后重试。",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="container mx-auto space-y-5 p-4" data-testid="revenue-dashboard-page">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">收益看板</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            从门店汇总逐级钻取到部门、柜位；数据范围以当前账号权限为准。收费按付款日期统计，仅包含已关联付款记录的数据。
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          口径：销售毛利（不含税）＋费用收益（不含税）＋其他收益
        </div>
      </div>

      <Card>
        <CardContent className="grid gap-4 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
          <div className="space-y-2">
            <Label htmlFor="revenue-dashboard-start">开始日期</Label>
            <Input
              id="revenue-dashboard-start"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="revenue-dashboard-end">结束日期</Label>
            <Input
              id="revenue-dashboard-end"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </div>
          <div className="flex items-end gap-2">
            <Button
              className="flex-1 sm:flex-none"
              onClick={applyDateRange}
              disabled={!startDate || !endDate || endDate < startDate || query.isFetching}
            >
              {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-1 whitespace-nowrap sm:flex-none"
              onClick={handleExport}
              disabled={!permissionRows.length || query.isFetching}
            >
              <Download className="mr-2 h-4 w-4" />
              导出最明细
            </Button>
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

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard title="总收益" value={money(totals.total)} note={`${appliedRange.startDate} 至 ${appliedRange.endDate}`} icon={<CircleDollarSign className="h-5 w-5" />} />
            <MetricCard title="销售毛利" value={money(totals.sales)} note="销售毛利不含税" icon={<BarChart3 className="h-5 w-5" />} />
            <MetricCard title="费用收益" value={money(totals.fee)} note="按付款日期，不含税" icon={<Building2 className="h-5 w-5" />} />
            <MetricCard title="其他收益" value={money(totals.extra)} note="已确认的其他收益" icon={<CircleDollarSign className="h-5 w-5" />} />
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
                      <Bar dataKey="fee" name="费用收益" stackId="revenue" fill="#d97706" />
                      <Bar dataKey="extra" name="其他收益" stackId="revenue" fill="#64748b" />
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
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">{currentTitle}</CardTitle>
                <p className="mt-1 text-xs text-muted-foreground">
                  {level === "groups" ? "柜位明细为当前钻取终点。" : "点击任意一行继续向下钻取。"}
                </p>
              </div>
              {level === "departments" && (
                <Button variant="ghost" size="sm" onClick={resetDrilldown}>返回门店</Button>
              )}
              {level === "groups" && (
                <Button variant="ghost" size="sm" onClick={backToDepartments}>返回部门</Button>
              )}
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{level === "stores" ? "门店" : level === "departments" ? "部门" : "柜位"}</TableHead>
                    {level === "stores" && <TableHead className="text-right">部门数</TableHead>}
                    {level !== "groups" && <TableHead className="text-right">柜位数</TableHead>}
                    {level === "groups" && <TableHead>图上经营单元</TableHead>}
                    <TableHead className="text-right">销售毛利</TableHead>
                    <TableHead className="text-right">费用收益</TableHead>
                    <TableHead className="text-right">其他收益</TableHead>
                    <TableHead className="text-right">总收益</TableHead>
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
                      <TableCell className="text-right tabular-nums">
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
                            {money(row.sales)}
                          </button>
                        ) : money(row.sales)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
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
                            {money(row.fee)}
                          </button>
                        ) : money(row.fee)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{money(row.extra)}</TableCell>
                      <TableCell className="text-right font-semibold tabular-nums">{money(row.total)}</TableCell>
                      {level !== "groups" && (
                        <TableCell><ChevronRight className="h-4 w-4 text-slate-400" /></TableCell>
                      )}
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell
                        colSpan={level === "stores" ? 8 : level === "departments" ? 7 : 6}
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
            open={Boolean(detailSelection)}
            onOpenChange={(open) => {
              if (!open) setDetailSelection(null);
            }}
          >
            <SheetContent className="z-[60] flex w-full flex-col overflow-hidden bg-white p-0 sm:max-w-5xl">
              <SheetHeader className="border-b px-5 py-4 pr-12">
                <SheetTitle>
                  {detailSelection?.row.label}
                  {detailSelection?.mode === "gross-profit" ? " · 每日毛利明细" : " · 费用明细"}
                </SheetTitle>
                <SheetDescription>
                  柜位 {detailSelection?.row.code || "—"} · {appliedRange.startDate} 至 {appliedRange.endDate}
                  {detailSelection?.mode === "fees" ? " · 按付款日期" : ""}
                </SheetDescription>
              </SheetHeader>
              <div className="min-h-0 flex-1 overflow-auto p-5">
                {detailQuery.isLoading ? (
                  <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载明细…
                  </div>
                ) : detailQuery.isError ? (
                  <div className="py-10 text-center text-sm text-red-600">
                    {detailQuery.error instanceof Error ? detailQuery.error.message : "明细加载失败"}
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
                    <div className="grid gap-3 sm:grid-cols-3">
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">柜位表费用收益</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailSelection.row.fee)}</div>
                      </div>
                      <div className="rounded-md border bg-slate-50 p-4">
                        <div className="text-xs text-muted-foreground">费用明细合计</div>
                        <div className="mt-1 text-xl font-semibold">{money(detailQuery.data.fees.total_amount)}</div>
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
