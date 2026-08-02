import { Fragment, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet, Loader2, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/contexts/StoreContext";
import { useToast } from "@/hooks/use-toast";
import { apiGet } from "@/lib/api";
import {
  buildDailyFollowupParams,
  DAILY_FOLLOWUP_ALL_DEPARTMENTS,
  DAILY_FOLLOWUP_ALL_STORES,
  financialMonthForDate,
  financialMonthLabel,
  formatDailyDate,
  type DailyFollowupMetric,
  type DailyFollowupResponse,
} from "@/lib/daily-followup-report";
import {
  buildOd0003Sheets,
  OD0003_METRIC_HEADERS,
  OD0003_SHEETS,
  od0003AggregateMetrics,
  od0003MetricHeaders,
  od0003MetricValues,
  od0003WeekGroups,
  type Od0003RowKind,
  type Od0003SheetName,
} from "@/lib/od0003-report";

type AuthorizedStore = {
  store_id: string | number;
  store_code: string;
  store_name: string;
};

type AuthorizedDepartment = {
  store_code: string;
  department_code: string;
  department_name: string;
};

type Filters = {
  financialMonth: string;
  storeId: string;
  departmentId: string;
};

const PALETTE = {
  header: "#D8E4BC",
  categorySubtotal: "#CCC0DA",
  areaSubtotal: "#B7DEE8",
  departmentSubtotal: "#D8E4BC",
  grandTotal: "#8DB4E2",
} as const;
const TARGET_HEADERS = [
  "月度销售指标",
  "差额",
  "完成率",
  "月度毛利指标（含税）",
  "差额",
  "完成率",
];

function rowBackground(kind: Od0003RowKind): string {
  return kind === "categorySubtotal"
    ? PALETTE.categorySubtotal
    : kind === "areaSubtotal"
      ? PALETTE.areaSubtotal
      : kind === "departmentSubtotal"
        ? PALETTE.departmentSubtotal
        : kind === "grandTotal"
          ? PALETTE.grandTotal
          : "#FFFFFF";
}

function metricText(value: number | "", offset: number): string {
  if (value === "") return "—";
  if (offset >= 3 && ![4, 5, 6].includes(offset)) {
    return `${(value * 100).toFixed(2)}%`;
  }
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function metricTone(metric: DailyFollowupMetric, offset: number): string {
  const values = od0003MetricValues(metric);
  const value = values[offset];
  return typeof value === "number" && value < 0 ? "text-red-600" : "";
}

export default function Od0003CenterSalesFollowupPage() {
  const { selectedStoreId } = useStore();
  const { toast } = useToast();
  const initialMonth = useMemo(() => financialMonthForDate(new Date()), []);
  const [draft, setDraft] = useState<Filters>({
    financialMonth: initialMonth,
    storeId: "",
    departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
  });
  const [submitted, setSubmitted] = useState<Filters | null>(null);
  const [activeSheet, setActiveSheet] = useState<Od0003SheetName>("品牌销售");
  const [exporting, setExporting] = useState(false);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/od0003/stores"],
    queryFn: () => apiGet("/api/sales/reports/od0003/stores"),
  });
  const globalStoreCode = selectedStoreId === null
    ? null
    : storesQuery.data?.find((store) => String(store.store_id) === String(selectedStoreId))?.store_code ?? null;

  useEffect(() => {
    if (!draft.storeId && storesQuery.data) {
      setDraft((current) => ({
        ...current,
        storeId: globalStoreCode || DAILY_FOLLOWUP_ALL_STORES,
        departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
      }));
    }
  }, [draft.storeId, globalStoreCode, storesQuery.data]);

  const departmentStoreParam = draft.storeId === DAILY_FOLLOWUP_ALL_STORES
    ? ""
    : `?store_id=${encodeURIComponent(draft.storeId)}`;
  const departmentsQuery = useQuery<AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/od0003/departments", draft.storeId],
    queryFn: () => apiGet(`/api/sales/reports/od0003/departments${departmentStoreParam}`),
    enabled: Boolean(draft.storeId),
  });

  const queryString = useMemo(() => {
    if (!submitted) return "";
    return buildDailyFollowupParams({
      financialMonth: submitted.financialMonth,
      dimension: "groups",
      storeId: submitted.storeId,
      departmentId: submitted.departmentId,
    }).toString();
  }, [submitted]);
  const reportQuery = useQuery<DailyFollowupResponse>({
    queryKey: ["/api/sales/reports/od0003", submitted],
    queryFn: () => apiGet(`/api/sales/reports/od0003?${queryString}`),
    enabled: Boolean(submitted?.financialMonth),
  });
  const sheets = useMemo(
    () => reportQuery.data ? buildOd0003Sheets(reportQuery.data) : [],
    [reportQuery.data],
  );
  const sheet = sheets.find((item) => item.name === activeSheet);
  const metricHeaders = reportQuery.data
    ? od0003MetricHeaders(reportQuery.data.financial_month)
    : [...OD0003_METRIC_HEADERS];
  const weekGroups = reportQuery.data ? od0003WeekGroups(reportQuery.data.days) : [];
  const periodLabels = reportQuery.data
    ? [
        "1-12月",
        `${Number(reportQuery.data.financial_month.slice(5, 7))}月`,
        ...reportQuery.data.days.map((day) => formatDailyDate(day.date)),
        ...weekGroups.map((group) => group.label),
      ]
    : [];

  const runQuery = () => {
    if (!draft.financialMonth || !draft.storeId) {
      toast({ variant: "destructive", title: "请选择财务月" });
      return;
    }
    setSubmitted(draft);
  };

  const exportExcel = async () => {
    if (!reportQuery.data) return;
    setExporting(true);
    try {
      const { downloadOd0003Workbook } = await import("@/lib/export-od0003-excel");
      downloadOd0003Workbook(reportQuery.data);
      toast({ title: "OD0003 已导出", description: "颜色、页签和多级表头已按原表生成。" });
    } catch (error) {
      console.error("导出OD0003失败", error);
      toast({ variant: "destructive", title: "导出失败", description: "Excel 文件生成失败，请稍后重试。" });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <FileSpreadsheet className="h-6 w-6 text-emerald-700" />
            OD0003 中心销售跟进表
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            按门店或部门查看品牌、区域、类别的财务月销售、毛利和每日同期变化。
          </p>
        </div>
        {reportQuery.data?.scope_description && (
          <Badge variant="outline" className="max-w-full whitespace-normal px-3 py-1.5 font-normal">
            {reportQuery.data.scope_description}
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(170px,.7fr)_minmax(190px,1fr)_minmax(220px,1fr)_auto] lg:items-end">
          <div className="space-y-2">
            <Label htmlFor="od0003-month">财务月</Label>
            <Input
              id="od0003-month"
              type="month"
              value={draft.financialMonth}
              onChange={(event) => setDraft((current) => ({ ...current, financialMonth: event.target.value }))}
            />
            <div className="text-xs text-muted-foreground">{financialMonthLabel(draft.financialMonth)}</div>
          </div>
          <div className="space-y-2">
            <Label>门店</Label>
            <Select
              value={draft.storeId}
              onValueChange={(storeId) => setDraft((current) => ({
                ...current,
                storeId,
                departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
              }))}
            >
              <SelectTrigger><SelectValue placeholder="请选择门店" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={DAILY_FOLLOWUP_ALL_STORES}>全部门店</SelectItem>
                {(storesQuery.data ?? []).map((store) => (
                  <SelectItem key={String(store.store_id)} value={store.store_code}>
                    {store.store_name || store.store_code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>部门</Label>
            <Select
              value={draft.departmentId}
              onValueChange={(departmentId) => setDraft((current) => ({ ...current, departmentId }))}
              disabled={!draft.storeId || departmentsQuery.isLoading}
            >
              <SelectTrigger><SelectValue placeholder="全部门" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={DAILY_FOLLOWUP_ALL_DEPARTMENTS}>全部门</SelectItem>
                {(departmentsQuery.data ?? []).map((department) => (
                  <SelectItem
                    key={`${department.store_code}-${department.department_code}`}
                    value={department.department_code}
                  >
                    {draft.storeId === DAILY_FOLLOWUP_ALL_STORES
                      ? `${department.store_code} · `
                      : ""}
                    {department.department_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <Button onClick={runQuery} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching
                ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={exportExcel} disabled={!reportQuery.data || exporting}>
              {exporting
                ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                : <Download className="mr-2 h-4 w-4" />}
              导出 Excel
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="gap-3 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-base">报表预览</CardTitle>
            <span className="text-xs text-muted-foreground">金额单位：万元；红色表示负数</span>
          </div>
          <Tabs value={activeSheet} onValueChange={(value) => setActiveSheet(value as Od0003SheetName)}>
            <TabsList className="h-auto flex-wrap justify-start">
              {OD0003_SHEETS.map((name) => <TabsTrigger key={name} value={name}>{name}</TabsTrigger>)}
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          {reportQuery.isLoading || reportQuery.isFetching ? (
            <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在生成中心销售跟进表…
            </div>
          ) : reportQuery.error ? (
            <div role="alert" className="py-20 text-center text-sm text-red-600">报表加载失败，请检查权限或稍后重试</div>
          ) : !sheet ? (
            <div className="py-20 text-center text-sm text-muted-foreground">请选择门店、中心和财务月后查询</div>
          ) : (
            <div className="max-h-[68vh] overflow-auto rounded-md border border-black">
              <table className="border-collapse text-[11px]">
                <thead className="sticky top-0 z-20">
                  <tr>
                    {sheet.dimensionHeaders.map((header) => (
                      <th
                        key={header}
                        rowSpan={2}
                        className="min-w-[82px] border border-black px-2 py-2 text-center font-semibold"
                        style={{ backgroundColor: PALETTE.header }}
                      >
                        {header}
                      </th>
                    ))}
                    {periodLabels.map((label, periodIndex) => (
                      <Fragment key={label}>
                        <th colSpan={4} className="border border-black px-2 py-2 text-center" style={{ backgroundColor: PALETTE.header }}>
                          {label}销售额
                        </th>
                        <th colSpan={4} className="border border-black px-2 py-2 text-center" style={{ backgroundColor: PALETTE.header }}>
                          {label}毛利额
                        </th>
                        <th colSpan={3} className="border border-black px-2 py-2 text-center" style={{ backgroundColor: PALETTE.header }}>
                          {label}毛利率
                        </th>
                        {periodIndex === 0 && sheet.name === "部门销售" && TARGET_HEADERS.map((header, targetIndex) => (
                          <th
                            key={`${header}-${targetIndex}`}
                            rowSpan={2}
                            className="min-w-[82px] whitespace-pre-line border border-black px-2 py-2 text-center"
                            style={{ backgroundColor: PALETTE.header }}
                          >
                            {header}
                          </th>
                        ))}
                      </Fragment>
                    ))}
                  </tr>
                  <tr>
                    {periodLabels.flatMap((label, group) =>
                      metricHeaders.map((header, index) => (
                        <th
                          key={`${label}-${group}-${header}-${index}`}
                          className="min-w-[76px] border border-black px-1.5 py-2 text-center font-semibold"
                          style={{ backgroundColor: PALETTE.header }}
                        >
                          {header}
                        </th>
                      )))}
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.map((row) => {
                    const weekMetrics = weekGroups.map((group) =>
                      od0003AggregateMetrics(group.dayIndexes.map((index) => row.daily[index])));
                    const periodMetrics = [
                      row.ytdTotals,
                      row.totals,
                      ...row.daily,
                      ...weekMetrics,
                    ];
                    return (
                      <tr key={row.key} className={row.kind === "detail" ? "" : "font-semibold"}>
                        {row.labels.map((label, index) => (
                          <td
                            key={`${row.key}-label-${index}`}
                            className="border border-black px-2 py-2 text-center"
                            style={{ backgroundColor: rowBackground(row.kind) }}
                          >
                            {label}
                          </td>
                        ))}
                        {periodMetrics.flatMap((metricValue, groupIndex) => [
                          ...od0003MetricValues(metricValue).map((value, offset) => (
                            <td
                              key={`${row.key}-${groupIndex}-${offset}`}
                              className={`border border-black px-1.5 py-2 text-right tabular-nums ${metricTone(metricValue, offset)}`}
                              style={{ backgroundColor: rowBackground(row.kind) }}
                            >
                              {metricText(value, offset)}
                            </td>
                          )),
                          ...(groupIndex === 0 && sheet.name === "部门销售"
                            ? TARGET_HEADERS.map((_, targetIndex) => (
                                <td
                                  key={`${row.key}-target-${targetIndex}`}
                                  className="border border-black px-1.5 py-2 text-right"
                                  style={{ backgroundColor: rowBackground(row.kind) }}
                                />
                              ))
                            : []),
                        ])}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
