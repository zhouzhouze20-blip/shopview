import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ChevronLeft, ChevronRight, Download, Loader2, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/contexts/StoreContext";
import { useToast } from "@/hooks/use-toast";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  buildDailyFollowupParams,
  DAILY_FOLLOWUP_ALL_DEPARTMENTS,
  DAILY_FOLLOWUP_ALL_STORES,
  financialMonthForDate,
  financialMonthLabel,
  formatDailyDate,
  formatDailyMoneyWan,
  formatDailyPercent,
  formatDailyPercentagePointChange,
  type DailyFollowupDimension,
  type DailyFollowupMetric,
  type DailyFollowupResponse,
  type DailyFollowupRow,
} from "@/lib/daily-followup-report";

type Filters = {
  financialMonth: string;
  storeId: string;
  departmentId: string;
  dimension: Exclude<DailyFollowupDimension, "special_sales">;
};

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

type MetricView = "sales" | "profit";

const GROUP_PAGE_SIZE = 25;

function filterReportRows(
  report: DailyFollowupResponse | undefined,
  keyword: string,
): DailyFollowupRow[] {
  const normalizedKeyword = keyword.trim().toLocaleLowerCase("zh-CN");
  if (!normalizedKeyword || report?.dimension !== "groups") {
    return report?.rows ?? [];
  }
  return report.rows.filter((row) =>
    [
      row.store_code,
      row.store_name,
      row.department_code,
      row.department_name,
      row.dimension_code,
      row.dimension_name,
    ].some((value) => value?.toLocaleLowerCase("zh-CN").includes(normalizedKeyword)),
  );
}

function initialFilters(): Filters {
  return {
    financialMonth: financialMonthForDate(new Date()),
    storeId: DAILY_FOLLOWUP_ALL_STORES,
    departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
    dimension: "departments",
  };
}

function yoyTone(value: number | null): string {
  if (value === null || value === 0) return "text-muted-foreground";
  return value > 0 ? "text-red-600" : "text-emerald-600";
}

function metricValue(metric: DailyFollowupMetric, view: MetricView): number {
  return view === "sales" ? metric.sales_current : metric.profit_current;
}

function metricYoy(metric: DailyFollowupMetric, view: MetricView): number | null {
  return view === "sales" ? metric.sales_yoy : metric.profit_yoy;
}

function MetricCard({
  label,
  value,
  helper,
  helperClassName,
}: {
  label: string;
  value: string;
  helper: string;
  helperClassName?: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="text-sm text-muted-foreground">{label}</div>
        <div className="mt-2 text-2xl font-semibold tracking-tight">{value}</div>
        <div className={cn("mt-1 text-xs text-muted-foreground", helperClassName)}>{helper}</div>
      </CardContent>
    </Card>
  );
}

function MatrixCell({ metric, view }: { metric: DailyFollowupMetric; view: MetricView }) {
  const yoy = metricYoy(metric, view);
  return (
    <div className="min-w-[5.5rem] text-right tabular-nums">
      <div className="font-medium">{formatDailyMoneyWan(metricValue(metric, view))}</div>
      <div className={cn("text-[11px]", yoyTone(yoy))}>同 {formatDailyPercent(yoy)}</div>
    </div>
  );
}

export default function DailyFollowupReportPage() {
  const { selectedStoreId } = useStore();
  const { toast } = useToast();
  const initial = useMemo(() => initialFilters(), []);
  const [draft, setDraft] = useState<Filters>(initial);
  const [submitted, setSubmitted] = useState<Filters>(initial);
  const [draftDirty, setDraftDirty] = useState(false);
  const [metricView, setMetricView] = useState<MetricView>("sales");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/daily-followup/stores"],
    queryFn: () => apiGet("/api/sales/reports/daily-followup/stores"),
  });
  const globalStoreCode = selectedStoreId === null
    ? null
    : storesQuery.data?.find((store) => String(store.store_id) === String(selectedStoreId))?.store_code ?? null;

  useEffect(() => {
    if (!draftDirty && globalStoreCode) {
      setDraft((current) => ({
        ...current,
        storeId: globalStoreCode,
        departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
      }));
      setSubmitted((current) => ({
        ...current,
        storeId: globalStoreCode,
        departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
      }));
    }
  }, [draftDirty, globalStoreCode]);

  const departmentStoreParam = draft.storeId === DAILY_FOLLOWUP_ALL_STORES
    ? ""
    : `?store_id=${encodeURIComponent(draft.storeId)}`;
  const departmentsQuery = useQuery<AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/daily-followup/departments", draft.storeId],
    queryFn: () => apiGet(`/api/sales/reports/daily-followup/departments${departmentStoreParam}`),
  });

  const queryString = useMemo(
    () => buildDailyFollowupParams(submitted).toString(),
    [submitted],
  );
  const reportQuery = useQuery<DailyFollowupResponse>({
    queryKey: ["/api/sales/reports/daily-followup", submitted],
    queryFn: () => apiGet(`/api/sales/reports/daily-followup?${queryString}`),
    enabled: Boolean(submitted.financialMonth),
  });

  const report = reportQuery.data;
  const filteredRows = useMemo(
    () => filterReportRows(report, keyword),
    [keyword, report],
  );
  const pages = submitted.dimension === "groups"
    ? Math.max(1, Math.ceil(filteredRows.length / GROUP_PAGE_SIZE))
    : 1;
  const visibleRows = submitted.dimension === "groups"
    ? filteredRows.slice((page - 1) * GROUP_PAGE_SIZE, page * GROUP_PAGE_SIZE)
    : filteredRows;

  useEffect(() => {
    setPage(1);
  }, [keyword, submitted.dimension, submitted.financialMonth, submitted.storeId, submitted.departmentId]);

  const submit = () => {
    setSubmitted(draft);
    setPage(1);
  };

  const changeDimension = (
    dimension: Exclude<DailyFollowupDimension, "special_sales">,
  ) => {
    const next = { ...draft, dimension };
    setDraft(next);
    setSubmitted(next);
    setPage(1);
  };

  const changeStore = (storeId: string) => {
    setDraft((current) => ({
      ...current,
      storeId,
      departmentId: DAILY_FOLLOWUP_ALL_DEPARTMENTS,
    }));
    setDraftDirty(true);
  };

  const exportExcel = async () => {
    if (!report || filteredRows.length === 0) return;
    setExporting(true);
    try {
      const reportUrl = (dimension: DailyFollowupDimension) => {
        const params = buildDailyFollowupParams({
          ...submitted,
          dimension,
        }).toString();
        return `/api/sales/reports/daily-followup?${params}`;
      };
      const [departmentReport, groupReport, specialSaleReport] = await Promise.all([
        apiGet<DailyFollowupResponse>(reportUrl("departments")),
        apiGet<DailyFollowupResponse>(reportUrl("groups")),
        apiGet<DailyFollowupResponse>(reportUrl("special_sales")),
      ]);
      const activeReport = submitted.dimension === "departments"
        ? departmentReport
        : groupReport;
      const companionReport = submitted.dimension === "departments"
        ? groupReport
        : departmentReport;
      const activeRows = filterReportRows(
        activeReport,
        submitted.dimension === "groups" ? keyword : "",
      );
      const companionRows = filterReportRows(
        companionReport,
        submitted.dimension === "departments" ? "" : keyword,
      );
      const { exportDailyFollowupExcel } = await import("@/lib/export-daily-followup-excel");
      const filename = exportDailyFollowupExcel(activeReport, {
        rows: activeRows,
        companionReport,
        companionRows,
        specialSaleReport,
        specialSaleRows: specialSaleReport.rows,
      });
      toast({
        title: "已导出 Excel",
        description: filename,
      });
    } catch (error) {
      console.error("导出OD0001销售逐日跟进表失败", error);
      toast({
        variant: "destructive",
        title: "导出失败",
        description: "Excel 文件生成失败，请稍后重试。",
      });
    } finally {
      setExporting(false);
    }
  };

  const totals = report?.totals;
  const cumulativeDates = report?.cumulative_dates ?? report?.dates;
  const errorMessage = reportQuery.error instanceof Error
    ? (/403|无权限/.test(reportQuery.error.message) ? "当前账号无权查看此报表" : "报表加载失败，请稍后重试")
    : null;

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <CalendarDays className="h-6 w-6 text-blue-600" />
            OD0001 销售逐日跟进表
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            按财务月查看部门与柜组的每日销售、毛利和同期变化，数据自动按当前账号业务范围过滤。
          </p>
        </div>
        {report?.scope_description && (
          <Badge variant="outline" className="max-w-full whitespace-normal px-3 py-1.5 text-left font-normal">
            {report.scope_description}
          </Badge>
        )}
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">查询条件</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(160px,0.7fr)_minmax(180px,1fr)_minmax(180px,1fr)_auto] lg:items-end">
          <div className="space-y-2">
            <Label htmlFor="daily-followup-month">财务月</Label>
            <Input
              id="daily-followup-month"
              type="month"
              value={draft.financialMonth}
              onChange={(event) => {
                setDraft((current) => ({ ...current, financialMonth: event.target.value }));
                setDraftDirty(true);
              }}
            />
            {draft.financialMonth && (
              <div className="text-xs text-muted-foreground">{financialMonthLabel(draft.financialMonth)}</div>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="daily-followup-store">门店</Label>
            <Select value={draft.storeId} onValueChange={changeStore} disabled={storesQuery.isLoading}>
              <SelectTrigger id="daily-followup-store"><SelectValue placeholder="权限内全部门店" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={DAILY_FOLLOWUP_ALL_STORES}>权限内全部门店</SelectItem>
                {(storesQuery.data ?? []).map((store) => (
                  <SelectItem key={String(store.store_id)} value={store.store_code}>
                    {store.store_name || store.store_code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="daily-followup-department">部门</Label>
            <Select
              value={draft.departmentId}
              onValueChange={(departmentId) => {
                setDraft((current) => ({ ...current, departmentId }));
                setDraftDirty(true);
              }}
              disabled={departmentsQuery.isLoading}
            >
              <SelectTrigger id="daily-followup-department"><SelectValue placeholder="全部部门" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={DAILY_FOLLOWUP_ALL_DEPARTMENTS}>全部部门</SelectItem>
                {(departmentsQuery.data ?? []).map((department) => (
                  <SelectItem
                    key={`${department.store_code}-${department.department_code}`}
                    value={department.department_code}
                  >
                    {draft.storeId === DAILY_FOLLOWUP_ALL_STORES ? `${department.store_code} · ` : ""}
                    {department.department_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={submit} disabled={!draft.financialMonth || reportQuery.isFetching}>
              {reportQuery.isFetching
                ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button
              variant="outline"
              onClick={exportExcel}
              disabled={exporting || reportQuery.isFetching || !report || filteredRows.length === 0}
            >
              {exporting
                ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                : <Download className="mr-2 h-4 w-4" />}
              {exporting ? "导出中…" : "导出 Excel"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {totals && cumulativeDates && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
          <MetricCard
            label="本期销售（万元）"
            value={formatDailyMoneyWan(totals.sales_current)}
            helper={`同期 ${formatDailyMoneyWan(totals.sales_prior)} 万元`}
          />
          <MetricCard
            label="销售同比"
            value={formatDailyPercent(totals.sales_yoy)}
            helper={`${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}`}
            helperClassName={yoyTone(totals.sales_yoy)}
          />
          <MetricCard
            label="本期毛利（万元）"
            value={formatDailyMoneyWan(totals.profit_current)}
            helper={`同期 ${formatDailyMoneyWan(totals.profit_prior)} 万元`}
          />
          <MetricCard
            label="本期毛利率"
            value={formatDailyPercent(totals.margin_current)}
            helper="本期毛利 ÷ 本期销售"
          />
          <MetricCard
            label="同期毛利率"
            value={formatDailyPercent(totals.margin_prior)}
            helper="同期毛利 ÷ 同期销售"
          />
          <MetricCard
            label="毛利率同比"
            value={formatDailyPercentagePointChange(totals.margin_change)}
            helper="本期毛利率－同期毛利率"
            helperClassName={yoyTone(totals.margin_change)}
          />
        </div>
      )}

      <Card>
        <CardHeader className="gap-4 pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-base">逐日明细</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <Tabs value={metricView} onValueChange={(value) => setMetricView(value as MetricView)}>
                <TabsList>
                  <TabsTrigger value="sales">销售收入</TabsTrigger>
                  <TabsTrigger value="profit">毛利</TabsTrigger>
                </TabsList>
              </Tabs>
              <Tabs
                value={submitted.dimension}
                onValueChange={(value) => changeDimension(
                  value as Exclude<DailyFollowupDimension, "special_sales">,
                )}
              >
                <TabsList>
                  <TabsTrigger value="departments">部门逐日</TabsTrigger>
                  <TabsTrigger value="groups">柜组逐日</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
            <span>
              {cumulativeDates
                ? `金额单位：万元；累计本期 ${cumulativeDates.start_date} 至 ${cumulativeDates.end_date}，同期 ${cumulativeDates.prior_start_date} 至 ${cumulativeDates.prior_end_date}。`
                : "金额单位：万元；单元格下方“同”表示同期同比。"}
            </span>
            {submitted.dimension === "groups" && (
              <Input
                className="h-8 w-full sm:w-64"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="搜索门店、部门或柜组"
              />
            )}
          </div>
        </CardHeader>
        <CardContent>
          {reportQuery.isLoading ? (
            <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在加载财务月数据…
            </div>
          ) : errorMessage ? (
            <div role="alert" className="py-20 text-center text-sm text-red-600">{errorMessage}</div>
          ) : !report || visibleRows.length === 0 ? (
            <div className="py-20 text-center text-sm text-muted-foreground">当前筛选范围暂无销售数据</div>
          ) : submitted.dimension === "departments" ? (
            <div className="max-h-[62vh] overflow-auto rounded-md border">
              <Table>
                <TableHeader className="sticky top-0 z-20 bg-background">
                  <TableRow>
                    <TableHead className="sticky left-0 z-30 min-w-[7rem] bg-background">月日</TableHead>
                    {visibleRows.map((row) => (
                      <TableHead key={`${row.store_code}-${row.dimension_code}`} className="min-w-[7.5rem] text-right">
                        <div className="whitespace-nowrap">{row.dimension_name || "未匹配"}</div>
                        {submitted.storeId === DAILY_FOLLOWUP_ALL_STORES && (
                          <div className="text-[11px] font-normal text-muted-foreground">{row.store_code}</div>
                        )}
                      </TableHead>
                    ))}
                    <TableHead className="min-w-[7.5rem] text-right">合计</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.days.map((day, dayIndex) => (
                    <TableRow key={day.date}>
                      <TableCell className="sticky left-0 z-10 bg-background font-medium">
                        <div>{formatDailyDate(day.date)}</div>
                        <div className="text-[11px] font-normal text-muted-foreground">同期 {formatDailyDate(day.prior_date)}</div>
                      </TableCell>
                      {visibleRows.map((row) => (
                        <TableCell key={`${row.store_code}-${row.dimension_code}-${day.date}`}>
                          <MatrixCell metric={row.daily[dayIndex]} view={metricView} />
                        </TableCell>
                      ))}
                      <TableCell className="bg-slate-50/70">
                        <MatrixCell metric={report.daily_totals[dayIndex]} view={metricView} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                <TableFooter>
                  <TableRow>
                    <TableCell className="sticky left-0 z-10 bg-muted font-semibold">本期累计</TableCell>
                    {visibleRows.map((row) => (
                      <TableCell key={`total-${row.store_code}-${row.dimension_code}`}>
                        <MatrixCell metric={row.totals} view={metricView} />
                      </TableCell>
                    ))}
                    <TableCell><MatrixCell metric={report.totals} view={metricView} /></TableCell>
                  </TableRow>
                </TableFooter>
              </Table>
            </div>
          ) : (
            <>
              <div className="max-h-[62vh] overflow-auto rounded-md border">
                <Table>
                  <TableHeader className="sticky top-0 z-20 bg-background">
                    <TableRow>
                      <TableHead className="sticky left-0 z-30 min-w-[8rem] bg-background">部门</TableHead>
                      <TableHead className="sticky left-[8rem] z-30 min-w-[13rem] bg-background">柜组</TableHead>
                      {report.days.map((day) => (
                        <TableHead key={day.date} className="min-w-[6.25rem] text-right">{formatDailyDate(day.date)}</TableHead>
                      ))}
                      <TableHead className="min-w-[7rem] text-right">合计</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleRows.map((row: DailyFollowupRow) => (
                      <TableRow key={`${row.store_code}-${row.dimension_code}`}>
                        <TableCell className="sticky left-0 z-10 bg-background">
                          <div className="max-w-[8rem] truncate font-medium" title={row.department_name || undefined}>
                            {row.department_name || "未匹配"}
                          </div>
                          <div className="text-[11px] text-muted-foreground">{row.store_code}</div>
                        </TableCell>
                        <TableCell className="sticky left-[8rem] z-10 bg-background">
                          <div className="max-w-[13rem] truncate font-medium" title={row.dimension_name || undefined}>
                            {row.dimension_name || "未匹配"}
                          </div>
                          <div className="text-[11px] text-muted-foreground">{row.dimension_code || "—"}</div>
                        </TableCell>
                        {row.daily.map((metric) => (
                          <TableCell key={`${row.dimension_code}-${metric.date}`}>
                            <MatrixCell metric={metric} view={metricView} />
                          </TableCell>
                        ))}
                        <TableCell className="bg-slate-50/70">
                          <MatrixCell metric={row.totals} view={metricView} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                <span>共 {filteredRows.length} 个柜组</span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span>{page} / {pages}</span>
                  <Button variant="outline" size="sm" onClick={() => setPage((value) => Math.min(pages, value + 1))} disabled={page >= pages}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
