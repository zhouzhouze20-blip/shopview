import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  buildOd0002Params,
  changeOd0002Store,
  contentDispositionFilename,
  formatMoneyWan,
  formatPercent,
  getOd0002QueryMessage,
  OD0002_ALL_STORES,
  OD0002_ALL_DEPARTMENTS,
  OD0002_TABS,
  paginateRows,
  previousYearDate,
  normalizeOd0002StoreOptions,
  scheduleObjectUrlRevoke,
  syncOd0002DraftFromGlobalStore,
  visibleOd0002Columns,
  type Od0002DimensionKey,
  type Od0002Metric,
  type Od0002Response,
  type Od0002Row,
} from "@/lib/od0002-report";

type Filters = { start: string; end: string; storeId: string; departmentId: string };
type AuthorizedStore = { store_id: string | number; store_code: string; store_name: string };
type AuthorizedDepartment = { store_code: string; department_code: string; department_name: string };

function localIsoDate(date: Date): string {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function defaultFilters(): Filters {
  const now = new Date();
  const end = new Date(now);
  end.setDate(end.getDate() - 1);
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return { start: localIsoDate(start), end: localIsoDate(end), storeId: OD0002_ALL_STORES, departmentId: OD0002_ALL_DEPARTMENTS };
}

function yoyColorClass(value: number | null): string {
  if (value === null || value === 0) return "";
  if (value > 0) return "text-red-600";
  if (value < 0) return "text-green-600";
  return "";
}

const metricCells = (metrics: Od0002Metric) => [
  { value: formatMoneyWan(metrics.sales_current), rawValue: metrics.sales_current, isYoy: false },
  { value: formatMoneyWan(metrics.sales_prior), rawValue: metrics.sales_prior, isYoy: false },
  { value: formatPercent(metrics.sales_yoy), rawValue: metrics.sales_yoy, isYoy: true },
  { value: formatMoneyWan(metrics.profit_current), rawValue: metrics.profit_current, isYoy: false },
  { value: formatMoneyWan(metrics.profit_prior), rawValue: metrics.profit_prior, isYoy: false },
  { value: formatPercent(metrics.profit_yoy), rawValue: metrics.profit_yoy, isYoy: true },
  { value: formatPercent(metrics.margin_current), rawValue: metrics.margin_current, isYoy: false },
  { value: formatPercent(metrics.margin_prior), rawValue: metrics.margin_prior, isYoy: false },
  { value: formatPercent(metrics.margin_change), rawValue: metrics.margin_change, isYoy: true },
];

function HierarchyValue({ name, code }: { name?: string | null; code?: string | null }) {
  if (!name && !code) return null;
  return (
    <div className="min-w-[8rem] whitespace-nowrap">
      <div className="font-medium whitespace-nowrap">{name || "未匹配"}</div>
      <div className="text-xs text-muted-foreground whitespace-nowrap">{code || "—"}</div>
    </div>
  );
}

export default function Od0002SalesGrossProfitPage() {
  const { selectedStoreId } = useStore();
  const initial = useMemo(() => defaultFilters(), []);
  const [draft, setDraft] = useState<Filters>(initial);
  const [submitted, setSubmitted] = useState<Filters>(initial);
  const [queryVersion, setQueryVersion] = useState(0);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [draftDirty, setDraftDirty] = useState(false);
  const [activeTab, setActiveTab] = useState<Od0002DimensionKey>("stores");
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/od0002/stores"],
    queryFn: () => apiGet("/api/sales/reports/od0002/stores"),
  });
  const globalStoreCode = selectedStoreId === null
    ? null
    : storesQuery.data?.find((store) => String(store.store_id) === String(selectedStoreId))?.store_code ?? null;
  const departmentStoreParam = draft.storeId === OD0002_ALL_STORES ? "" : `?store_id=${encodeURIComponent(draft.storeId)}`;
  const departmentsQuery = useQuery<AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/od0002/departments", draft.storeId],
    queryFn: () => apiGet(`/api/sales/reports/od0002/departments${departmentStoreParam}`),
  });

  useEffect(() => {
    setDraft((current) => {
      const next = syncOd0002DraftFromGlobalStore(current, globalStoreCode, draftDirty);
      return next.storeId === current.storeId ? next : { ...next, departmentId: OD0002_ALL_DEPARTMENTS };
    });
  }, [globalStoreCode]);

  const queryString = useMemo(
    () => buildOd0002Params(submitted.start, submitted.end, submitted.storeId, submitted.departmentId).toString(),
    [submitted],
  );
  const reportQuery = useQuery<Od0002Response>({
    queryKey: ["/api/sales/reports/od0002", submitted, queryVersion],
    queryFn: () => apiGet(`/api/sales/reports/od0002?${queryString}`),
    enabled: hasSubmitted && Boolean(submitted.start && submitted.end && submitted.start <= submitted.end),
  });

  const rows = hasSubmitted ? reportQuery.data?.dimensions[activeTab] ?? [] : [];
  const pagedRows = activeTab === "groups" ? paginateRows(rows, page) : rows;
  const activeTotal = hasSubmitted ? reportQuery.data?.totals[activeTab] : undefined;
  const pages = Math.max(1, Math.ceil(rows.length / 50));
  const visible = visibleOd0002Columns(activeTab, submitted.storeId);
  const message = getOd0002QueryMessage({
    isLoading: hasSubmitted && reportQuery.isLoading,
    error: hasSubmitted ? reportQuery.error : null,
    hasData: hasSubmitted && Boolean(reportQuery.data),
    rowCount: rows.length,
  });
  const storeOptions = useMemo(
    () => normalizeOd0002StoreOptions(storesQuery.data ?? []),
    [storesQuery.data],
  );

  const updateDraft = (change: Partial<Filters>) => {
    setDraft((current) => ({ ...current, ...change }));
    setDraftDirty(true);
  };

  const submit = () => {
    if (!draft.start || !draft.end || draft.start > draft.end) return;
    setSubmitted({ ...draft });
    setQueryVersion((value) => value + 1);
    setHasSubmitted(true);
    setDraftDirty(false);
    setPage(1);
    setExportError(null);
  };

  const exportReport = async () => {
    setExporting(true);
    setExportError(null);
    let url: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/od0002/export?${queryString}`);
      if (!response.ok) throw new Error(`导出失败（${response.status}）`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `OD0002_门店销售毛利汇总表_${submitted.start}_${submitted.end}.xlsx`;
      url = URL.createObjectURL(blob);
      anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "导出失败，请稍后重试");
    } finally {
      anchor?.remove();
      if (url) scheduleObjectUrlRevoke(url);
      setExporting(false);
    }
  };

  const quality = hasSubmitted ? reportQuery.data?.quality : undefined;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">OD0002 门店销售毛利汇总表</h1>
        <p className="mt-1 text-sm text-muted-foreground">金额单位：万元；同期为本期日期自动回退一年。</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground">统计期间</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="od0002-start">本期开始</Label>
                  <Input id="od0002-start" type="date" value={draft.start} onChange={(event) => updateDraft({ start: event.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="od0002-end">本期结束</Label>
                  <Input id="od0002-end" type="date" value={draft.end} onChange={(event) => updateDraft({ end: event.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="od0002-prior-start">同期开始（自动）</Label>
                  <Input id="od0002-prior-start" readOnly value={draft.start ? previousYearDate(draft.start) : ""} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="od0002-prior-end">同期结束（自动）</Label>
                  <Input id="od0002-prior-end" readOnly value={draft.end ? previousYearDate(draft.end) : ""} />
                </div>
              </div>
            </section>
            <section className="flex flex-col space-y-3">
              <h3 className="text-sm font-medium text-muted-foreground">组织范围</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="od0002-store">门店</Label>
                  <Select value={draft.storeId} onValueChange={(storeId) => { setDraft((current) => changeOd0002Store(current, storeId)); setDraftDirty(true); }} disabled={storesQuery.isLoading}>
                    <SelectTrigger id="od0002-store"><SelectValue placeholder="权限内全部门店" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={OD0002_ALL_STORES}>权限内全部门店</SelectItem>
                      {storeOptions.map((store) => <SelectItem key={store.value} value={store.value}>{store.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="od0002-department">部门</Label>
                  <Select value={draft.departmentId} onValueChange={(departmentId) => updateDraft({ departmentId })} disabled={departmentsQuery.isLoading}>
                    <SelectTrigger id="od0002-department"><SelectValue placeholder="全部部门" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={OD0002_ALL_DEPARTMENTS}>全部部门</SelectItem>
                      {(departmentsQuery.data ?? []).map((department) => (
                        <SelectItem key={`${department.store_code}-${department.department_code}`} value={department.department_code}>
                          {draft.storeId === OD0002_ALL_STORES ? `${department.store_code} · ` : ""}{department.department_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="mt-auto flex flex-wrap justify-end gap-2 pt-2">
                <Button onClick={submit} disabled={reportQuery.isFetching || draft.start > draft.end}>
                  {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}<span>查询</span>
                </Button>
                <Button variant="outline" onClick={exportReport} disabled={exporting || !hasSubmitted || !reportQuery.data}>
                  {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                  {exporting ? "导出中…" : "导出 Excel"}
                </Button>
              </div>
            </section>
          </div>
          {draft.start > draft.end && <p className="text-sm text-red-600">本期结束日期不能早于开始日期</p>}
          {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Tabs value={activeTab} onValueChange={(value) => { setActiveTab(value as Od0002DimensionKey); setPage(1); }}>
            <TabsList className="mb-4 flex h-auto flex-wrap justify-start">
              {OD0002_TABS.map((tab) => <TabsTrigger key={tab.key} value={tab.key}>{tab.label}</TabsTrigger>)}
            </TabsList>
          </Tabs>

          {!hasSubmitted ? (
            <div role="status" className="py-16 text-center text-sm text-muted-foreground">请设置条件后点击查询</div>
          ) : message ? (
            message === "无权限查看此报表" || message === "报表加载失败，请稍后重试" ? (
              <div role="alert" className="py-16 text-center text-sm text-red-600">{message}</div>
            ) : (
              <div role="status" className="py-16 text-center text-sm text-muted-foreground">{message === "暂无数据" ? "暂无数据" : message}</div>
            )
          ) : activeTab === "department_categories" ? (
            <div className="max-h-[65vh] overflow-auto rounded-md border">
              <Table>
                <TableHeader className="sticky top-0 z-20 bg-white">
                  <TableRow>
                    {submitted.storeId === OD0002_ALL_STORES && <TableHead rowSpan={2}>门店</TableHead>}
                    <TableHead rowSpan={2}>部门</TableHead>
                    <TableHead rowSpan={2}>区域</TableHead>
                    <TableHead rowSpan={2}>品类</TableHead>
                    <TableHead colSpan={3} className="text-center">销售收入</TableHead>
                    <TableHead colSpan={3} className="text-center">毛利</TableHead>
                    <TableHead colSpan={3} className="text-center">毛利率</TableHead>
                  </TableRow>
                  <TableRow>
                    {["本期", "同期", "同比", "本期", "同期", "同比", "本期", "同期", "同比"].map((label, index) => <TableHead key={`${label}-${index}`} className="text-right">{label}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedRows.map((row, index) => {
                    const isAreaSubtotal = row.row_type === "area_subtotal";
                    const isDepartmentSubtotal = row.row_type === "department_subtotal";
                    const subtotalClass = row.row_type === "category" ? "" : "bg-slate-50 font-semibold";
                    return (
                      <TableRow key={`${row.store_code ?? "all"}-${row.department_code ?? "department"}-${row.area_code ?? "area"}-${row.category_code ?? row.row_type ?? index}`} className={subtotalClass}>
                        {submitted.storeId === OD0002_ALL_STORES && (
                          <TableCell className="py-2"><HierarchyValue name={row.store_name} code={row.store_code} /></TableCell>
                        )}
                        <TableCell className="py-2">
                          <HierarchyValue
                            name={isDepartmentSubtotal ? `${row.department_name || "未匹配"}部门小计` : row.department_name}
                            code={row.department_code}
                          />
                        </TableCell>
                        <TableCell className="py-2">
                          {!isDepartmentSubtotal && (
                            <HierarchyValue
                              name={isAreaSubtotal ? `${row.area_name || "未匹配"}区域小计` : row.area_name}
                              code={row.area_code}
                            />
                          )}
                        </TableCell>
                        <TableCell className="py-2">
                          {!isAreaSubtotal && !isDepartmentSubtotal && <HierarchyValue name={row.category_name} code={row.category_code} />}
                        </TableCell>
                        {metricCells(row.metrics).map((cell, cellIndex) => <TableCell key={cellIndex} className={`py-2 text-right tabular-nums ${cell.isYoy ? yoyColorClass(cell.rawValue) : ""}`}>{cell.value}</TableCell>)}
                      </TableRow>
                    );
                  })}
                </TableBody>
                {activeTotal && rows.length > 0 && (
                  <TableFooter>
                    <TableRow>
                      {submitted.storeId === OD0002_ALL_STORES && <TableCell className="py-2" />}
                      <TableCell className="py-2">合计</TableCell>
                      <TableCell className="py-2" />
                      <TableCell className="py-2" />
                      {metricCells(activeTotal).map((cell, cellIndex) => <TableCell key={cellIndex} className={`py-2 text-right tabular-nums ${cell.isYoy ? yoyColorClass(cell.rawValue) : ""}`}>{cell.value}</TableCell>)}
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </div>
          ) : (
            <div className="max-h-[65vh] overflow-auto rounded-md border">
              <Table>
                <TableHeader className="sticky top-0 z-20 bg-white">
                  <TableRow>
                    {visible.includes("store") && <TableHead rowSpan={2}>门店</TableHead>}
                    {activeTab === "groups" && <TableHead rowSpan={2}>部门</TableHead>}
                    <TableHead rowSpan={2}>{activeTab === "groups" ? "柜组" : "维度"}</TableHead>
                    <TableHead colSpan={3} className="text-center">销售收入</TableHead>
                    <TableHead colSpan={3} className="text-center">毛利</TableHead>
                    <TableHead colSpan={3} className="text-center">毛利率</TableHead>
                  </TableRow>
                  <TableRow>
                    {["本期", "同期", "同比", "本期", "同期", "同比", "本期", "同期", "同比"].map((label, index) => <TableHead key={`${label}-${index}`} className="text-right">{label}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedRows.map((row, index) => (
                    <TableRow key={`${row.store_code ?? "all"}-${row.department_code ?? "department"}-${row.dimension_code ?? row.dimension_name ?? index}`}>
                      {visible.includes("store") && (
                        <TableCell className="py-2">
                          <HierarchyValue name={row.store_name} code={row.store_code} />
                        </TableCell>
                      )}
                      {activeTab === "groups" && (
                        <TableCell className="py-2">
                          <HierarchyValue name={row.department_name} code={row.department_code} />
                        </TableCell>
                      )}
                      <TableCell className="py-2">
                        <HierarchyValue name={row.dimension_name} code={row.dimension_code} />
                      </TableCell>
                      {metricCells(row.metrics).map((cell, cellIndex) => <TableCell key={cellIndex} className={`py-2 text-right tabular-nums ${cell.isYoy ? yoyColorClass(cell.rawValue) : ""}`}>{cell.value}</TableCell>)}
                    </TableRow>
                  ))}
                </TableBody>
                {activeTotal && rows.length > 0 && (
                  <TableFooter>
                    <TableRow>
                      {visible.includes("store") && <TableCell className="py-2" />}
                      {activeTab === "groups" && <TableCell className="py-2" />}
                      <TableCell className="py-2">合计</TableCell>
                      {metricCells(activeTotal).map((cell, cellIndex) => <TableCell key={cellIndex} className={`py-2 text-right tabular-nums ${cell.isYoy ? yoyColorClass(cell.rawValue) : ""}`}>{cell.value}</TableCell>)}
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </div>
          )}

          {activeTab === "groups" && rows.length > 50 && (
            <div className="mt-4 flex items-center justify-end gap-3 text-sm">
              <span>第 {page} / {pages} 页，共 {rows.length} 条</span>
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</Button>
              <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>下一页</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {quality && (
        <Card>
          <CardHeader><CardTitle className="text-base">数据质量提示</CardTitle></CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <p>区域/品类未匹配柜组：{quality.unmatched_area_category_group_count}</p>
            <p>楼层未匹配柜组：{quality.unmatched_floor_group_count}</p>
            <p>区域/品类未匹配本期销售：{formatMoneyWan(quality.unmatched_area_category_sales_current)} 万元</p>
            <p>楼层未匹配本期销售：{formatMoneyWan(quality.unmatched_floor_sales_current)} 万元</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
