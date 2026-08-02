import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  contentDispositionFilename,
  normalizeOd0002StoreOptions,
  scheduleObjectUrlRevoke,
} from "@/lib/od0002-report";
import {
  buildSettledGrossProfitParams,
  formatSettledMoney,
  formatSettledQuantity,
  paginateSettledRows,
  settledGrossProfitMessage,
  SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS,
  SETTLED_GROSS_PROFIT_ALL_STORES,
  type SettledGrossProfitResponse,
  type SettledGrossProfitRow,
} from "@/lib/settled-gross-profit-report";

type Filters = { start: string; end: string; storeId: string; departmentId: string };
type AuthorizedStore = { store_id: string | number; store_code: string; store_name: string };
type AuthorizedDepartment = { store_code: string; department_code: string; department_name: string };

function localIsoDate(date: Date): string {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function defaultFilters(): Filters {
  const end = new Date();
  end.setDate(end.getDate() - 1);
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return {
    start: localIsoDate(start),
    end: localIsoDate(end),
    storeId: SETTLED_GROSS_PROFIT_ALL_STORES,
    departmentId: SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS,
  };
}

function CodeName({ code, name, brackets = false }: { code?: string | null; name?: string | null; brackets?: boolean }) {
  if (!code && !name) return <>—</>;
  return (
    <div className="min-w-[9rem] whitespace-nowrap">
      <div className="font-medium">{name || "未匹配"}</div>
      <div className="text-xs text-muted-foreground">
        {code ? (brackets ? `[${code}]` : code) : "—"}
      </div>
    </div>
  );
}

const money = (row: SettledGrossProfitRow, key: keyof SettledGrossProfitRow) =>
  formatSettledMoney(row[key] as number | null);

export default function SettledGrossProfitRankingPage() {
  const { selectedStoreId } = useStore();
  const initial = useMemo(() => defaultFilters(), []);
  const [draft, setDraft] = useState<Filters>(initial);
  const [submitted, setSubmitted] = useState<Filters | null>(null);
  const [draftDirty, setDraftDirty] = useState(false);
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/settled-gross-profit/stores"],
    queryFn: () => apiGet("/api/sales/reports/settled-gross-profit/stores"),
  });
  const globalStoreCode = selectedStoreId === null
    ? null
    : storesQuery.data?.find((store) => String(store.store_id) === String(selectedStoreId))?.store_code ?? null;

  useEffect(() => {
    if (draftDirty) return;
    setDraft((current) => ({
      ...current,
      storeId: globalStoreCode ?? SETTLED_GROSS_PROFIT_ALL_STORES,
      departmentId: SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS,
    }));
  }, [globalStoreCode, draftDirty]);

  const departmentStoreParam = draft.storeId === SETTLED_GROSS_PROFIT_ALL_STORES
    ? ""
    : `?store_id=${encodeURIComponent(draft.storeId)}`;
  const departmentsQuery = useQuery<AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/settled-gross-profit/departments", draft.storeId],
    queryFn: () => apiGet(`/api/sales/reports/settled-gross-profit/departments${departmentStoreParam}`),
  });

  const queryString = submitted
    ? buildSettledGrossProfitParams(
        submitted.start,
        submitted.end,
        submitted.storeId,
        submitted.departmentId,
      ).toString()
    : "";
  const reportQuery = useQuery<SettledGrossProfitResponse>({
    queryKey: ["/api/sales/reports/settled-gross-profit", submitted],
    queryFn: () => apiGet(`/api/sales/reports/settled-gross-profit?${queryString}`),
    enabled: Boolean(submitted && submitted.start && submitted.end && submitted.start <= submitted.end),
  });

  const rows = reportQuery.data?.rows ?? [];
  const pagedRows = paginateSettledRows(rows, page);
  const pages = Math.max(1, Math.ceil(rows.length / 50));
  const message = settledGrossProfitMessage({
    isLoading: Boolean(submitted) && reportQuery.isLoading,
    error: submitted ? reportQuery.error : null,
    hasData: Boolean(reportQuery.data),
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
    setDraftDirty(false);
    setPage(1);
    setExportError(null);
  };

  const exportReport = async () => {
    if (!submitted) return;
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/settled-gross-profit/export?${queryString}`);
      if (!response.ok) throw new Error(`导出失败（${response.status}）`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `结算后销售毛利排行表_${submitted.start}_${submitted.end}.xlsx`;
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

  const quality = reportQuery.data?.quality;
  const totals = reportQuery.data?.totals;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">结算后销售毛利排行表</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          按核算日期统计，读取柜位数据库同步表；金额单位：元。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="settled-profit-start">开始日期</Label>
              <Input id="settled-profit-start" type="date" value={draft.start} onChange={(event) => updateDraft({ start: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settled-profit-end">结束日期</Label>
              <Input id="settled-profit-end" type="date" value={draft.end} onChange={(event) => updateDraft({ end: event.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settled-profit-store">门店</Label>
              <Select
                value={draft.storeId}
                onValueChange={(storeId) => updateDraft({
                  storeId,
                  departmentId: SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS,
                })}
                disabled={storesQuery.isLoading}
              >
                <SelectTrigger id="settled-profit-store"><SelectValue placeholder="权限内全部门店" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={SETTLED_GROSS_PROFIT_ALL_STORES}>权限内全部门店</SelectItem>
                  {storeOptions.map((store) => <SelectItem key={store.value} value={store.value}>{store.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="settled-profit-department">部门</Label>
              <Select value={draft.departmentId} onValueChange={(departmentId) => updateDraft({ departmentId })} disabled={departmentsQuery.isLoading}>
                <SelectTrigger id="settled-profit-department"><SelectValue placeholder="全部部门" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={SETTLED_GROSS_PROFIT_ALL_DEPARTMENTS}>全部部门</SelectItem>
                  {(departmentsQuery.data ?? []).map((department) => (
                    <SelectItem key={`${department.store_code}-${department.department_code}`} value={department.department_code}>
                      {draft.storeId === SETTLED_GROSS_PROFIT_ALL_STORES ? `${department.store_code} · ` : ""}
                      {department.department_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button onClick={submit} disabled={reportQuery.isFetching || draft.start > draft.end}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={exportReport} disabled={exporting || !reportQuery.data}>
              {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {exporting ? "导出中…" : "导出 Excel"}
            </Button>
          </div>
          {draft.start > draft.end && <p className="text-sm text-red-600">结束日期不能早于开始日期</p>}
          {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        </CardContent>
      </Card>

      {quality && (
        <Card className={quality.unresolved_contract_group_count ? "border-amber-300 bg-amber-50/40" : ""}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              {quality.unresolved_contract_group_count > 0 && <AlertTriangle className="h-4 w-4 text-amber-600" />}
              数据质量提示
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
            <div>报表行数：<strong>{quality.row_count}</strong></div>
            <div>未匹配合同：<strong>{quality.unresolved_contract_group_count}</strong></div>
            <div>未匹配合同销售：<strong>{formatSettledMoney(quality.unresolved_contract_sales)}</strong></div>
            <div>供应商名称缺失：<strong>{quality.missing_supplier_name_count}</strong></div>
            <div>区域名称缺失：<strong>{quality.missing_area_name_count}</strong></div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-6">
          {message ? (
            <div className="py-12 text-center text-sm text-muted-foreground">{message}</div>
          ) : submitted && reportQuery.data ? (
            <>
              <div className="overflow-x-auto rounded-md border">
                <Table className="min-w-[2600px]">
                  <TableHeader>
                    <TableRow>
                      {[
                        "门店", "部门", "柜组", "供应商", "楼层", "营业面积", "经营方式", "区域", "合同号",
                        "销售数量", "销售收入", "不含税销售", "前台毛利", "不含税毛利调整", "保底调整",
                        "含税销售保底成本", "原扣率毛利", "家电返利", "合同到期日期", "合同毛利",
                      ].map((label) => <TableHead key={label} className="whitespace-nowrap">{label}</TableHead>)}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pagedRows.map((row, index) => (
                      <TableRow key={`${row.store_code}-${row.group_code}-${row.supplier_code}-${row.contract_code ?? "none"}-${index}`} className={!row.contract_code ? "bg-amber-50" : ""}>
                        <TableCell className="py-2"><CodeName code={row.store_code} name={row.store_name} /></TableCell>
                        <TableCell className="py-2"><CodeName code={row.department_code} name={row.department_name} /></TableCell>
                        <TableCell className="py-2"><CodeName code={row.group_code} name={row.group_name} /></TableCell>
                        <TableCell className="py-2"><CodeName code={row.supplier_code} name={row.supplier_name} brackets /></TableCell>
                        <TableCell className="py-2 whitespace-nowrap">{row.floor_name || "—"}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(row.business_area)}</TableCell>
                        <TableCell className="py-2 whitespace-nowrap">{row.operation_mode_name}</TableCell>
                        <TableCell className="py-2"><CodeName code={row.area_code} name={row.area_name} /></TableCell>
                        <TableCell className="py-2 whitespace-nowrap">{row.contract_code || "未匹配"}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledQuantity(row.sales_qty)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "sales_revenue")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "tax_excluded_sales")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "front_profit")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "tax_excluded_profit_adjustment")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "floor_adjustment")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "sales_floor_cost")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "original_rate_profit")}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "appliance_rebate")}</TableCell>
                        <TableCell className="py-2 whitespace-nowrap">{row.contract_end_date || "—"}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{money(row, "contract_profit")}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  {totals && (
                    <TableFooter>
                      <TableRow>
                        <TableCell colSpan={9} className="py-2 font-semibold">合计</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledQuantity(totals.sales_qty)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.sales_revenue)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.tax_excluded_sales)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.front_profit)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.tax_excluded_profit_adjustment)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.floor_adjustment)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.sales_floor_cost)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.original_rate_profit)}</TableCell>
                        <TableCell className="py-2 text-right tabular-nums">{formatSettledMoney(totals.appliance_rebate)}</TableCell>
                        <TableCell className="py-2">—</TableCell>
                        <TableCell className="py-2">—</TableCell>
                      </TableRow>
                    </TableFooter>
                  )}
                </Table>
              </div>
              {pages > 1 && (
                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">共 {rows.length} 行，第 {page}/{pages} 页</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}>上一页</Button>
                    <Button variant="outline" size="sm" onClick={() => setPage((value) => Math.min(pages, value + 1))} disabled={page >= pages}>下一页</Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="py-12 text-center text-sm text-muted-foreground">请选择条件后查询</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
