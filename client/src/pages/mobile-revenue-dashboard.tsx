import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BarChart3,
  Building2,
  CalendarDays,
  ChevronRight,
  CircleDollarSign,
  Home,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Store,
} from "lucide-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import { apiGet } from "@/lib/api";
import {
  buildMobileRevenueDatePresets,
  type MobileRevenueDatePreset,
} from "@/lib/mobile-revenue-date-presets";
import { canAccessModule } from "@/lib/module-permissions";

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
};

type RevenueDashboardResponse = {
  start_date: string;
  end_date: string;
  permission_scoped: boolean;
  grain: string;
  items: RevenueDashboardItem[];
};

type RevenueSummaryRow = {
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

type RevenueDashboardGroupDetail = {
  gross_profit: {
    total_amount: number;
    items: Array<{
      revenue_date: string;
      gross_profit_amount: number;
      source_count: number;
    }>;
  };
  fees: {
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
      tax_excluded_amount: number;
    }>;
  };
};

type DrillLevel = "stores" | "departments" | "groups";
type DetailMode = "gross-profit" | "fees";

const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const todayString = () => isoDate(new Date());

const money = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

const departmentKey = (row: RevenueDashboardItem) =>
  row.department_code || `name:${row.department_name}`;

const groupKey = (row: RevenueDashboardItem) =>
  row.group_code || `unit:${row.unit_codes || row.group_name}`;

const aggregateRows = (
  rows: RevenueDashboardItem[],
  keyOf: (row: RevenueDashboardItem) => string,
  labelOf: (row: RevenueDashboardItem) => string,
  codeOf: (row: RevenueDashboardItem) => string | null | undefined,
): RevenueSummaryRow[] => {
  const buckets = new Map<
    string,
    RevenueSummaryRow & { departments: Set<string>; groups: Set<string>; units: Set<string> }
  >();
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
    target.sales += Number(row.sales_gross_profit_amount || 0);
    target.fee += Number(row.fee_amount || 0);
    target.extra += Number(row.extra_amount || 0);
    target.total += Number(row.total_amount || 0);
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

function RevenueBreakdown({
  sales,
  fee,
  extra,
}: {
  sales: number;
  fee: number;
  extra: number;
}) {
  return (
    <div className="grid grid-cols-3 gap-1.5 text-center">
      <div className="rounded-xl bg-blue-50 px-1.5 py-2">
        <div className="text-[9px] text-blue-500">销售毛利</div>
        <div className="mt-0.5 truncate text-[11px] font-semibold tabular-nums text-blue-950">{money(sales)}</div>
      </div>
      <div className="rounded-xl bg-amber-50 px-1.5 py-2">
        <div className="text-[9px] text-amber-600">费用收益</div>
        <div className="mt-0.5 truncate text-[11px] font-semibold tabular-nums text-amber-950">{money(fee)}</div>
      </div>
      <div className="rounded-xl bg-slate-100 px-1.5 py-2">
        <div className="text-[9px] text-slate-500">其他收益</div>
        <div className="mt-0.5 truncate text-[11px] font-semibold tabular-nums text-slate-900">{money(extra)}</div>
      </div>
    </div>
  );
}

export default function MobileRevenueDashboardPage() {
  const { menuUser } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-revenue-dashboard");
  const today = todayString();
  const datePresets = buildMobileRevenueDatePresets(today);
  const defaultPreset = datePresets[0];
  const [draftStartDate, setDraftStartDate] = useState(defaultPreset.start);
  const [draftEndDate, setDraftEndDate] = useState(defaultPreset.end);
  const [appliedRange, setAppliedRange] = useState({
    start: defaultPreset.start,
    end: defaultPreset.end,
  });
  const [activeDateLabel, setActiveDateLabel] = useState<MobileRevenueDatePreset["label"] | "自定义">(
    defaultPreset.label,
  );
  const [dateFiltersOpen, setDateFiltersOpen] = useState(false);
  const [dateError, setDateError] = useState("");
  const [level, setLevel] = useState<DrillLevel>("stores");
  const [selectedStoreKey, setSelectedStoreKey] = useState<string | null>(null);
  const [selectedDepartmentKey, setSelectedDepartmentKey] = useState<string | null>(null);
  const [detailSelection, setDetailSelection] = useState<{
    row: RevenueSummaryRow;
    mode: DetailMode;
  } | null>(null);

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-revenue-dashboard",
    moduleName: "手机端收益看板",
    clientType: "mobile",
    enabled: hasAccess,
    initialQueryConditions: {
      query_type: "revenue",
      start_date: appliedRange.start,
      end_date: appliedRange.end,
      query_level: "stores",
    },
  });

  const query = useQuery({
    queryKey: ["mobile-revenue-dashboard", appliedRange.start, appliedRange.end],
    queryFn: () =>
      apiGet<RevenueDashboardResponse>(
        `/api/revenue-map/dashboard?start_date=${appliedRange.start}&end_date=${appliedRange.end}`,
      ),
    enabled: hasAccess,
  });

  const detailQuery = useQuery({
    queryKey: [
      "mobile-revenue-dashboard-detail",
      selectedStoreKey,
      detailSelection?.row.code,
      detailSelection?.mode,
      appliedRange.start,
      appliedRange.end,
    ],
    queryFn: () => {
      const groupCode = detailSelection?.row.code;
      if (!selectedStoreKey || !groupCode) throw new Error("缺少门店或柜位编码");
      const params = new URLSearchParams({
        store_id: selectedStoreKey,
        start_date: appliedRange.start,
        end_date: appliedRange.end,
        detail_type: detailSelection?.mode || "all",
      });
      return apiGet<RevenueDashboardGroupDetail>(
        `/api/revenue-map/dashboard/groups/${encodeURIComponent(groupCode)}/details?${params.toString()}`,
      );
    },
    enabled: hasAccess && Boolean(selectedStoreKey && detailSelection?.row.code),
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
    () =>
      storeRows.filter(
        (row) => selectedDepartmentKey == null || departmentKey(row) === selectedDepartmentKey,
      ),
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
  const totals = useMemo(
    () =>
      currentRows.reduce(
        (sum, row) => ({
          total: sum.total + Number(row.total_amount || 0),
          sales: sum.sales + Number(row.sales_gross_profit_amount || 0),
          fee: sum.fee + Number(row.fee_amount || 0),
          extra: sum.extra + Number(row.extra_amount || 0),
        }),
        { total: 0, sales: 0, fee: 0, extra: 0 },
      ),
    [currentRows],
  );
  const currentCabinetCount = new Set(currentRows.map(groupKey)).size;

  const resetDrilldown = () => {
    setDetailSelection(null);
    setLevel("stores");
    setSelectedStoreKey(null);
    setSelectedDepartmentKey(null);
  };

  const backOneLevel = () => {
    setDetailSelection(null);
    if (level === "groups") {
      setSelectedDepartmentKey(null);
      setLevel("departments");
      return;
    }
    if (level === "departments") {
      resetDrilldown();
      return;
    }
    setLocation("/mobile");
  };

  const applyDateRange = (
    start = draftStartDate,
    end = draftEndDate,
    label: MobileRevenueDatePreset["label"] | "自定义" = "自定义",
  ) => {
    if (!start || !end || end < start) {
      setDateError("结束日期不能早于开始日期");
      return;
    }
    setDateError("");
    setDraftStartDate(start);
    setDraftEndDate(end);
    setAppliedRange({ start, end });
    setActiveDateLabel(label);
    resetDrilldown();
    setDateFiltersOpen(false);
    recordQuery({
      query_type: "revenue",
      start_date: start,
      end_date: end,
      query_level: "stores",
    });
  };

  const levelTitle =
    level === "stores" ? "门店收益" : level === "departments" ? "部门收益" : "柜位收益";
  const contextTitle =
    level === "stores"
      ? "全部可见范围"
      : level === "departments"
        ? selectedStore?.label || "已选门店"
        : selectedDepartment?.label || "已选部门";

  if (!hasAccess) {
    return (
      <main className="min-h-[100dvh] bg-slate-50 p-5">
        <Card className="mx-auto mt-16 max-w-md rounded-3xl">
          <CardContent className="p-6 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <h1 className="mt-4 text-lg font-semibold">暂无手机端收益看板权限</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              请联系管理员同时开通“手机端收益看板”和“查看收益看板”权限。
            </p>
            <Button variant="outline" className="mt-5" onClick={() => setLocation("/mobile")}>
              <Home className="mr-2 h-4 w-4" />返回首页
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1.25rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-amber-950 px-3 pb-3 pt-[max(.65rem,env(safe-area-inset-top))] text-white shadow-md">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 rounded-full text-white hover:bg-white/10 hover:text-white"
              onClick={backOneLevel}
              aria-label={level === "stores" ? "返回移动工作台" : "返回上一级"}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="min-w-0">
              <div className="text-[9px] font-medium tracking-[0.14em] text-amber-200">SHOPVIEW</div>
              <h1 className="truncate text-base font-semibold">收益看板</h1>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-full text-white hover:bg-white/10 hover:text-white"
            onClick={() => {
              recordQuery({
                query_type: "revenue",
                start_date: appliedRange.start,
                end_date: appliedRange.end,
                query_level: level,
                store_name: selectedStore?.label,
                department_name: selectedDepartment?.label,
              });
              void query.refetch();
            }}
            aria-label="刷新收益数据"
          >
            <RefreshCw className={`h-4 w-4 ${query.isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
        <button
          type="button"
          className="mt-3 flex w-full items-center justify-between rounded-xl bg-white/10 px-3 py-2 text-left"
          onClick={() => setDateFiltersOpen((open) => !open)}
        >
          <div>
            <div className="text-[10px] text-amber-100">{activeDateLabel} · {contextTitle}</div>
            <div className="mt-0.5 text-xs font-medium">{appliedRange.start} 至 {appliedRange.end}</div>
          </div>
          <CalendarDays className="h-4 w-4 text-amber-200" />
        </button>
      </header>

      <div className="mx-auto max-w-xl space-y-3 px-3 pt-3">
        {dateFiltersOpen ? (
          <Card className="rounded-2xl border-0 shadow-sm">
            <CardContent className="space-y-3 p-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="mobile-revenue-start" className="text-[10px] text-slate-500">开始日期</Label>
                  <Input id="mobile-revenue-start" type="date" className="h-9 px-2 text-xs" value={draftStartDate} onChange={(event) => setDraftStartDate(event.target.value)} />
                </div>
                <div>
                  <Label htmlFor="mobile-revenue-end" className="text-[10px] text-slate-500">结束日期</Label>
                  <Input id="mobile-revenue-end" type="date" className="h-9 px-2 text-xs" value={draftEndDate} onChange={(event) => setDraftEndDate(event.target.value)} />
                </div>
              </div>
              {dateError ? <div className="text-xs text-red-600">{dateError}</div> : null}
              <div className="flex gap-2 overflow-x-auto">
                {datePresets.map((preset) => (
                  <Button
                    key={preset.label}
                    type="button"
                    variant={activeDateLabel === preset.label ? "default" : "outline"}
                    size="sm"
                    className="h-8 shrink-0 rounded-full text-xs"
                    onClick={() => applyDateRange(preset.start, preset.end, preset.label)}
                  >
                    {preset.label}
                  </Button>
                ))}
                <Button type="button" size="sm" className="ml-auto h-8 shrink-0 rounded-full text-xs" onClick={() => applyDateRange()}>
                  <Search className="mr-1 h-3.5 w-3.5" />查询
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card className="overflow-hidden rounded-3xl border-0 bg-gradient-to-br from-amber-600 to-orange-700 text-white shadow-md">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-amber-100">总收益（不含税口径）</div>
                <div className="mt-1 text-3xl font-bold tracking-tight tabular-nums">
                  {query.isError ? "—" : money(totals.total)}
                </div>
              </div>
              <div className="rounded-2xl bg-white/15 p-2.5">
                <CircleDollarSign className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 border-t border-white/15 pt-3 text-center">
              <div>
                <div className="text-[10px] text-amber-100">销售毛利</div>
                <div className="mt-0.5 truncate text-xs font-semibold tabular-nums">{query.isError ? "—" : money(totals.sales)}</div>
              </div>
              <div>
                <div className="text-[10px] text-amber-100">费用收益</div>
                <div className="mt-0.5 truncate text-xs font-semibold tabular-nums">{query.isError ? "—" : money(totals.fee)}</div>
              </div>
              <div>
                <div className="text-[10px] text-amber-100">其他收益</div>
                <div className="mt-0.5 truncate text-xs font-semibold tabular-nums">{query.isError ? "—" : money(totals.extra)}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-2 gap-2">
          <Card className="rounded-2xl border-0 shadow-sm">
            <CardContent className="flex items-center gap-3 p-3">
              <div className="rounded-xl bg-blue-50 p-2 text-blue-700"><Store className="h-4 w-4" /></div>
              <div>
                <div className="text-[10px] text-slate-400">可见柜位</div>
                <div className="text-lg font-semibold tabular-nums">{query.isError ? "—" : currentCabinetCount}</div>
              </div>
            </CardContent>
          </Card>
          <Card className="rounded-2xl border-0 shadow-sm">
            <CardContent className="flex items-center gap-3 p-3">
              <div className="rounded-xl bg-amber-50 p-2 text-amber-700"><Building2 className="h-4 w-4" /></div>
              <div>
                <div className="text-[10px] text-slate-400">{levelTitle}</div>
                <div className="text-lg font-semibold tabular-nums">{query.isError ? "—" : currentSummaries.length}</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <section className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <div>
              <h2 className="text-sm font-semibold">{levelTitle}</h2>
              <div className="text-[10px] text-slate-400">按总收益从高到低排列</div>
            </div>
            {level !== "stores" ? (
              <Button variant="ghost" size="sm" className="h-8 px-2 text-xs" onClick={resetDrilldown}>
                <Home className="mr-1 h-3.5 w-3.5" />门店
              </Button>
            ) : null}
          </div>

          {query.isLoading ? (
            <Card className="rounded-2xl border-0 shadow-sm">
              <CardContent className="flex h-36 items-center justify-center text-sm text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在汇总权限范围内的收益…
              </CardContent>
            </Card>
          ) : query.isError ? (
            <Card className="rounded-2xl border-0 shadow-sm">
              <CardContent className="py-10 text-center text-sm text-red-600">
                {query.error instanceof Error ? query.error.message : "收益看板加载失败"}
              </CardContent>
            </Card>
          ) : currentSummaries.length ? (
            currentSummaries.map((row) => (
              <Card key={row.key} className="overflow-hidden rounded-2xl border-0 shadow-sm">
                <CardContent className="p-0">
                  {level === "groups" ? (
                    <div className="p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{row.label}</div>
                          <div className="mt-0.5 truncate text-[10px] text-slate-400">
                            {row.code || "无编码"}{row.unit_codes ? ` · 经营单元 ${row.unit_codes}` : ""}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-[9px] text-slate-400">总收益</div>
                          <div className="text-sm font-bold tabular-nums text-amber-700">{money(row.total)}</div>
                        </div>
                      </div>
                      <div className="mt-3"><RevenueBreakdown sales={row.sales} fee={row.fee} extra={row.extra} /></div>
                      {row.code ? (
                        <div className="mt-3 grid grid-cols-2 gap-2">
                          <Button variant="outline" size="sm" className="h-8 rounded-xl text-xs" onClick={() => {
                            recordQuery({
                              query_type: "revenue",
                              start_date: appliedRange.start,
                              end_date: appliedRange.end,
                              query_level: "detail",
                              store_name: selectedStore?.label,
                              department_name: selectedDepartment?.label,
                              group_code: row.code,
                              group_name: row.label,
                              detail_type: "销售毛利",
                            });
                            setDetailSelection({ row, mode: "gross-profit" });
                          }}>
                            <BarChart3 className="mr-1 h-3.5 w-3.5" />毛利明细
                          </Button>
                          <Button variant="outline" size="sm" className="h-8 rounded-xl text-xs" onClick={() => {
                            recordQuery({
                              query_type: "revenue",
                              start_date: appliedRange.start,
                              end_date: appliedRange.end,
                              query_level: "detail",
                              store_name: selectedStore?.label,
                              department_name: selectedDepartment?.label,
                              group_code: row.code,
                              group_name: row.label,
                              detail_type: "费用",
                            });
                            setDetailSelection({ row, mode: "fees" });
                          }}>
                            <CircleDollarSign className="mr-1 h-3.5 w-3.5" />费用明细
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="w-full p-3 text-left transition active:bg-slate-50"
                      onClick={() => {
                        if (level === "stores") {
                          recordQuery({
                            query_type: "revenue",
                            start_date: appliedRange.start,
                            end_date: appliedRange.end,
                            query_level: "departments",
                            store_code: row.code,
                            store_name: row.label,
                          });
                          setSelectedStoreKey(row.key);
                          setSelectedDepartmentKey(null);
                          setLevel("departments");
                        } else {
                          recordQuery({
                            query_type: "revenue",
                            start_date: appliedRange.start,
                            end_date: appliedRange.end,
                            query_level: "groups",
                            store_name: selectedStore?.label,
                            department_code: row.code,
                            department_name: row.label,
                          });
                          setSelectedDepartmentKey(row.key);
                          setLevel("groups");
                        }
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{row.label}</div>
                          <div className="mt-0.5 text-[10px] text-slate-400">
                            {row.code || "无编码"} · {level === "stores" ? `${row.department_count} 个部门` : `${row.group_count} 个柜位`}
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <div className="text-right">
                            <div className="text-[9px] text-slate-400">总收益</div>
                            <div className="text-sm font-bold tabular-nums text-amber-700">{money(row.total)}</div>
                          </div>
                          <ChevronRight className="h-4 w-4 text-slate-300" />
                        </div>
                      </div>
                      <div className="mt-3"><RevenueBreakdown sales={row.sales} fee={row.fee} extra={row.extra} /></div>
                    </button>
                  )}
                </CardContent>
              </Card>
            ))
          ) : (
            <Card className="rounded-2xl border-0 shadow-sm">
              <CardContent className="py-10 text-center text-sm text-slate-500">当前层级暂无收益数据</CardContent>
            </Card>
          )}
        </section>

        <div className="flex items-center justify-center gap-2 py-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4" /> 数据范围与电脑端收益看板一致
        </div>
      </div>

      <Sheet open={Boolean(detailSelection)} onOpenChange={(open) => !open && setDetailSelection(null)}>
        <SheetContent side="bottom" className="z-[60] h-[88dvh] rounded-t-3xl bg-white p-0">
          <SheetHeader className="border-b px-5 py-4 pr-12 text-left">
            <SheetTitle>
              {detailSelection?.row.label}
              {detailSelection?.mode === "gross-profit" ? " · 每日毛利" : " · 费用明细"}
            </SheetTitle>
            <SheetDescription>
              柜位 {detailSelection?.row.code || "—"} · {appliedRange.start} 至 {appliedRange.end}
            </SheetDescription>
          </SheetHeader>
          <div className="h-[calc(88dvh-5.5rem)] overflow-y-auto p-4">
            {detailQuery.isLoading ? (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载明细…
              </div>
            ) : detailQuery.isError ? (
              <div className="py-10 text-center text-sm text-red-600">
                {detailQuery.error instanceof Error ? detailQuery.error.message : "明细加载失败"}
              </div>
            ) : detailQuery.data && detailSelection?.mode === "gross-profit" ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-2xl bg-blue-50 p-3">
                    <div className="text-[10px] text-blue-500">柜位汇总</div>
                    <div className="mt-1 text-base font-semibold text-blue-950">{money(detailSelection.row.sales)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-100 p-3">
                    <div className="text-[10px] text-slate-500">每日明细合计</div>
                    <div className="mt-1 text-base font-semibold">{money(detailQuery.data.gross_profit.total_amount)}</div>
                  </div>
                </div>
                {detailQuery.data.gross_profit.items.length ? (
                  detailQuery.data.gross_profit.items.map((item) => (
                    <Card key={item.revenue_date} className="rounded-2xl shadow-none">
                      <CardContent className="flex items-center justify-between p-3">
                        <div>
                          <div className="text-sm font-medium">{item.revenue_date?.slice(0, 10)}</div>
                          <div className="mt-0.5 text-[10px] text-slate-400">{item.source_count} 笔来源</div>
                        </div>
                        <div className="font-semibold tabular-nums text-blue-800">{money(item.gross_profit_amount)}</div>
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <div className="py-10 text-center text-sm text-slate-500">当前日期范围暂无销售毛利明细</div>
                )}
              </div>
            ) : detailQuery.data && detailSelection?.mode === "fees" ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-2xl bg-amber-50 p-2">
                    <div className="text-[9px] text-amber-600">柜位汇总</div>
                    <div className="mt-1 truncate text-xs font-semibold">{money(detailSelection.row.fee)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-100 p-2">
                    <div className="text-[9px] text-slate-500">明细合计</div>
                    <div className="mt-1 truncate text-xs font-semibold">{money(detailQuery.data.fees.total_amount)}</div>
                  </div>
                  <div className="rounded-2xl bg-slate-100 p-2">
                    <div className="text-[9px] text-slate-500">费用笔数</div>
                    <div className="mt-1 text-xs font-semibold">{detailQuery.data.fees.total_count}</div>
                  </div>
                </div>
                {detailQuery.data.fees.items.length ? (
                  detailQuery.data.fees.items.map((item) => (
                    <Card key={item.id} className="rounded-2xl shadow-none">
                      <CardContent className="space-y-2 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold">{item.fee_type_name || "未命名费用"}</div>
                            <div className="mt-0.5 text-[10px] text-slate-400">{item.revenue_date?.slice(0, 10)} · {item.fee_type_code || "—"}</div>
                          </div>
                          <div className="shrink-0 text-right">
                            <div className="text-[9px] text-slate-400">不含税</div>
                            <div className="text-sm font-semibold tabular-nums text-amber-700">{money(item.tax_excluded_amount)}</div>
                          </div>
                        </div>
                        <div className="rounded-xl bg-slate-50 px-3 py-2 text-[11px] leading-5 text-slate-600">
                          <div>付款单号：{item.payment_no || "—"}</div>
                          <div>结算单号：{item.settlement_no || "—"}</div>
                          <div>合同：{item.contract_code || "—"} {item.contract_name || ""}</div>
                          <div>含税金额：{money(item.tax_included_amount)}</div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                ) : (
                  <div className="py-10 text-center text-sm text-slate-500">当前日期范围暂无费用明细</div>
                )}
                {detailQuery.data.fees.is_truncated ? (
                  <div className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    共 {detailQuery.data.fees.total_count} 条，当前显示前 {detailQuery.data.fees.returned_count} 条。
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </main>
  );
}
