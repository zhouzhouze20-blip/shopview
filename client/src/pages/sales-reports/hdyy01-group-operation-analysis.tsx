import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  buildHdyy01Params,
  changeHdyy01Store,
  contentDispositionFilename,
  formatHdyy01Area,
  formatHdyy01CodeName,
  formatHdyy01Count,
  formatHdyy01Money,
  formatHdyy01Quantity,
  getHdyy01QueryMessage,
  HDYY01_ALL_DEPARTMENTS,
  HDYY01_ALL_STORES,
  normalizeHdyy01StoreOptions,
  paginateRows,
  scheduleObjectUrlRevoke,
  syncHdyy01DraftFromGlobalStore,
  type Hdyy01AuthorizedDepartment,
  type Hdyy01AuthorizedStore,
  type Hdyy01DraftFilters,
  type Hdyy01Response,
  type Hdyy01Row,
} from "@/lib/hdyy01-report";

const PAGE_SIZE = 50;

type Hdyy01Column = {
  label: string;
  className?: string;
  render: (row: Hdyy01Row) => ReactNode;
};

const textCell = (value: string | null | undefined) => value?.trim() || "—";

const HDYY01_COLUMNS: readonly Hdyy01Column[] = [
  {
    label: "机构",
    className: "min-w-40",
    render: (row) => formatHdyy01CodeName(row.store_code, row.store_name),
  },
  {
    label: "部门",
    className: "min-w-44",
    render: (row) => formatHdyy01CodeName(row.department_code, row.department_name),
  },
  { label: "柜组编码", className: "min-w-28", render: (row) => textCell(row.group_code) },
  { label: "柜组名称", className: "min-w-36", render: (row) => textCell(row.group_name) },
  { label: "面积", className: "min-w-24 text-right", render: (row) => formatHdyy01Area(row.area) },
  { label: "楼层", className: "min-w-20", render: (row) => textCell(row.floor_code) },
  { label: "一级编码", className: "min-w-24", render: (row) => textCell(row.level1_code) },
  { label: "一级名称", className: "min-w-28", render: (row) => textCell(row.level1_name) },
  { label: "二级编码", className: "min-w-24", render: (row) => textCell(row.level2_code) },
  { label: "二级名称", className: "min-w-28", render: (row) => textCell(row.level2_name) },
  { label: "等级", className: "min-w-20", render: (row) => textCell(row.grade_label) },
  { label: "数量", className: "min-w-24 text-right", render: (row) => formatHdyy01Quantity(row.quantity) },
  { label: "销售收入", className: "min-w-28 text-right", render: (row) => formatHdyy01Money(row.sales_amount) },
  { label: "含税销售成本", className: "min-w-32 text-right", render: (row) => formatHdyy01Money(row.tax_cost) },
  { label: "毛利", className: "min-w-28 text-right", render: (row) => formatHdyy01Money(row.profit) },
  { label: "消费次数", className: "min-w-24 text-right", render: (row) => formatHdyy01Count(row.ticket_count) },
  { label: "客单", className: "min-w-24 text-right", render: (row) => formatHdyy01Money(row.average_ticket) },
  { label: "会员销售", className: "min-w-28 text-right", render: (row) => formatHdyy01Money(row.member_sales) },
  { label: "储值卡销售", className: "min-w-28 text-right", render: (row) => formatHdyy01Money(row.stored_card_sales) },
];

function localIsoDate(date: Date): string {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function defaultFilters(): Hdyy01DraftFilters {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now);
  end.setDate(end.getDate() - 1);
  return {
    start: localIsoDate(start),
    end: localIsoDate(end),
    storeId: HDYY01_ALL_STORES,
    departmentId: HDYY01_ALL_DEPARTMENTS,
  };
}

export default function Hdyy01GroupOperationAnalysisPage() {
  const { selectedStoreId } = useStore();
  const initial = useMemo(() => defaultFilters(), []);
  const [draft, setDraft] = useState<Hdyy01DraftFilters>(initial);
  const [submitted, setSubmitted] = useState<Hdyy01DraftFilters>(initial);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [queryVersion, setQueryVersion] = useState(0);
  const [draftDirty, setDraftDirty] = useState(false);
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<Hdyy01AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/hdyy01/stores"],
    queryFn: () => apiGet("/api/sales/reports/hdyy01/stores"),
  });
  const globalStoreCode = selectedStoreId === null
    ? null
    : storesQuery.data?.find((store) => String(store.store_id) === String(selectedStoreId))?.store_code ?? null;

  useEffect(() => {
    setDraft((current) => syncHdyy01DraftFromGlobalStore(current, globalStoreCode, draftDirty));
  }, [globalStoreCode]);

  const hasSelectedStore = draft.storeId !== HDYY01_ALL_STORES;
  const departmentsQuery = useQuery<Hdyy01AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/hdyy01/departments", draft.storeId],
    queryFn: () => apiGet(
      `/api/sales/reports/hdyy01/departments?store_id=${encodeURIComponent(draft.storeId)}`,
    ),
    enabled: hasSelectedStore,
  });

  const queryString = useMemo(
    () => buildHdyy01Params(
      submitted.start,
      submitted.end,
      submitted.storeId,
      submitted.departmentId,
    ).toString(),
    [submitted],
  );
  const reportQuery = useQuery<Hdyy01Response>({
    queryKey: ["/api/sales/reports/hdyy01", queryString, queryVersion],
    queryFn: () => apiGet(`/api/sales/reports/hdyy01?${queryString}`),
    enabled: hasSubmitted
      && Boolean(submitted.start && submitted.end && submitted.start <= submitted.end),
  });

  const storeOptions = useMemo(
    () => normalizeHdyy01StoreOptions(storesQuery.data ?? []),
    [storesQuery.data],
  );
  const rows = hasSubmitted ? reportQuery.data?.rows ?? [] : [];
  const pagedRows = paginateRows(rows, page, PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const message = getHdyy01QueryMessage({
    isLoading: hasSubmitted && reportQuery.isLoading,
    error: hasSubmitted ? reportQuery.error : null,
    hasData: hasSubmitted && Boolean(reportQuery.data),
    rowCount: rows.length,
  });

  const updateDraft = (change: Partial<Hdyy01DraftFilters>) => {
    setDraft((current) => ({ ...current, ...change }));
    setDraftDirty(true);
  };

  const submit = () => {
    if (!draft.start || !draft.end || draft.start > draft.end) return;
    setSubmitted({ ...draft });
    setHasSubmitted(true);
    setQueryVersion((value) => value + 1);
    setDraftDirty(false);
    setPage(1);
    setExportError(null);
  };

  const exportReport = async () => {
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/hdyy01/export?${queryString}`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `HDYY01_柜组经营分析表_${submitted.start}_${submitted.end}.xlsx`;
      objectUrl = URL.createObjectURL(blob);
      anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "导出失败，请稍后重试");
    } finally {
      anchor?.remove();
      if (objectUrl) scheduleObjectUrlRevoke(objectUrl);
      setExporting(false);
    }
  };

  const quality = hasSubmitted ? reportQuery.data?.quality : undefined;
  const qualityItems = quality ? [
    { label: "未匹配组织柜组数", value: formatHdyy01Count(quality.unmatched_organization_group_count) },
    { label: "未匹配组织金额", value: formatHdyy01Money(quality.unmatched_organization_amount) },
    { label: "未匹配层级柜组数", value: formatHdyy01Count(quality.unmatched_hierarchy_group_count) },
    { label: "未匹配层级金额", value: formatHdyy01Money(quality.unmatched_hierarchy_amount) },
    { label: "缺失等级柜组数", value: formatHdyy01Count(quality.missing_grade_group_count) },
    { label: "缺失等级金额", value: formatHdyy01Money(quality.missing_grade_amount) },
    { label: "未匹配会员小票数", value: formatHdyy01Count(quality.unmatched_member_ticket_count) },
  ] : [];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">HDYY01柜组经营分析表</h1>
        <p className="mt-1 text-sm text-muted-foreground">金额单位：元；每页显示 50 条。</p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground">统计期间</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="hdyy01-start">开始日期</Label>
                  <Input
                    id="hdyy01-start"
                    type="date"
                    value={draft.start}
                    onChange={(event) => updateDraft({ start: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hdyy01-end">结束日期</Label>
                  <Input
                    id="hdyy01-end"
                    type="date"
                    value={draft.end}
                    onChange={(event) => updateDraft({ end: event.target.value })}
                  />
                </div>
              </div>
            </section>

            <section className="flex flex-col space-y-3">
              <h2 className="text-sm font-medium text-muted-foreground">组织范围</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="hdyy01-store">门店</Label>
                  <Select
                    value={draft.storeId}
                    onValueChange={(storeId) => {
                      setDraft((current) => changeHdyy01Store(current, storeId));
                      setDraftDirty(true);
                    }}
                    disabled={storesQuery.isLoading}
                  >
                    <SelectTrigger id="hdyy01-store">
                      <SelectValue placeholder="权限内全部门店" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={HDYY01_ALL_STORES}>权限内全部门店</SelectItem>
                      {storeOptions.map((store) => (
                        <SelectItem key={store.value} value={store.value}>{store.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hdyy01-department">部门</Label>
                  <Select
                    value={draft.departmentId}
                    onValueChange={(departmentId) => updateDraft({ departmentId })}
                    disabled={!hasSelectedStore || departmentsQuery.isLoading}
                  >
                    <SelectTrigger id="hdyy01-department">
                      <SelectValue placeholder={hasSelectedStore ? "全部部门" : "请先选择门店"} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={HDYY01_ALL_DEPARTMENTS}>全部部门</SelectItem>
                      {(departmentsQuery.data ?? [])
                        .filter((department) => department.store_code === draft.storeId)
                        .map((department) => (
                          <SelectItem
                            key={`${department.store_code}-${department.department_code}`}
                            value={department.department_code}
                          >
                            {department.department_name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="mt-auto flex flex-wrap justify-end gap-2 pt-2">
                <Button
                  onClick={submit}
                  disabled={reportQuery.isFetching || !draft.start || !draft.end || draft.start > draft.end}
                >
                  {reportQuery.isFetching
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <Search className="mr-2 h-4 w-4" />}
                  <span>查询</span>
                </Button>
                <Button
                  variant="outline"
                  onClick={exportReport}
                  disabled={exporting || !hasSubmitted || !reportQuery.data}
                >
                  {exporting
                    ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    : <Download className="mr-2 h-4 w-4" />}
                  {exporting ? "导出中…" : "导出 Excel"}
                </Button>
              </div>
            </section>
          </div>

          {draft.start > draft.end && (
            <p className="text-sm text-red-600">结束日期不能早于开始日期</p>
          )}
          {storesQuery.error && (
            <p role="alert" className="text-sm text-red-600">门店选项加载失败，请稍后重试</p>
          )}
          {hasSelectedStore && departmentsQuery.error && (
            <p role="alert" className="text-sm text-red-600">部门选项加载失败，请稍后重试</p>
          )}
          {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {!hasSubmitted ? (
            <div role="status" className="py-16 text-center text-sm text-muted-foreground">
              请设置条件后点击查询
            </div>
          ) : message ? (
            message === "无权限查看此报表" || message === "报表加载失败，请稍后重试" ? (
              <div role="alert" className="py-16 text-center text-sm text-red-600">{message}</div>
            ) : (
              <div role="status" className="py-16 text-center text-sm text-muted-foreground">{message}</div>
            )
          ) : (
            <div className="max-h-[65vh] overflow-x-auto overflow-y-auto rounded-md border">
              <Table className="min-w-[2200px]">
                <TableHeader className="sticky top-0 z-20 bg-white">
                  <TableRow>
                    {HDYY01_COLUMNS.map((column) => (
                      <TableHead key={column.label} className={column.className}>{column.label}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedRows.map((row, index) => (
                    <TableRow key={`${row.store_code ?? "unknown"}-${row.group_code ?? index}`}>
                      {HDYY01_COLUMNS.map((column) => (
                        <TableCell
                          key={column.label}
                          className={`py-2 tabular-nums ${column.className ?? ""}`}
                        >
                          {column.render(row)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
                {reportQuery.data?.total && rows.length > 0 && (
                  <TableFooter>
                    <TableRow>
                      <TableCell className="py-2 font-medium">合计</TableCell>
                      {Array.from({ length: 10 }, (_, index) => <TableCell key={index} />)}
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Quantity(reportQuery.data.total.quantity)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.sales_amount)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.tax_cost)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.profit)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Count(reportQuery.data.total.ticket_count)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.average_ticket)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.member_sales)}</TableCell>
                      <TableCell className="py-2 text-right tabular-nums">{formatHdyy01Money(reportQuery.data.total.stored_card_sales)}</TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </div>
          )}

          {rows.length > PAGE_SIZE && !message && (
            <div className="mt-4 flex items-center justify-end gap-3 text-sm">
              <span>第 {page} / {totalPages} 页，共 {rows.length} 条</span>
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                上一页
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                下一页
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {quality && (
        <Card>
          <CardHeader><CardTitle className="text-base">数据质量提示</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {qualityItems.map((item) => (
              <div key={item.label} className="rounded-md border bg-slate-50 p-3">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <div className="mt-1 font-medium tabular-nums">{item.value}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
