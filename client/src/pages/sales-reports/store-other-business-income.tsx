import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import { contentDispositionFilename, scheduleObjectUrlRevoke } from "@/lib/od0002-report";
import {
  STORE_OTHER_INCOME_ALL_STORES,
  buildStoreOtherIncomeParams,
  formatIncomeRate,
  formatIncomeWan,
  storeOtherIncomeRowClass,
  type StoreOtherIncomeReport,
  type StoreOtherIncomeRow,
} from "@/lib/store-other-business-income";
import { cn } from "@/lib/utils";


type AuthorizedStore = {
  store_id: string | number;
  store_code: string;
  store_name: string;
};

type Filters = {
  financialYear: number;
  endPeriod: number;
  storeId: string;
};

function defaultPeriod(): Pick<Filters, "financialYear" | "endPeriod"> {
  const today = new Date();
  if (today.getMonth() === 0) {
    return { financialYear: today.getFullYear() - 1, endPeriod: 12 };
  }
  return { financialYear: today.getFullYear(), endPeriod: today.getMonth() };
}

function rowGroup(row: StoreOtherIncomeRow, dimension: "store" | "department"): string {
  return dimension === "store" ? row.store_name : row.department_name || row.department_code || "—";
}

function IncomeTable({
  report,
  dimension,
}: {
  report: StoreOtherIncomeReport;
  dimension: "store" | "department";
}) {
  const rows = dimension === "store" ? report.store_rows : report.department_rows;
  const dimensionLabel = dimension === "store" ? "门店" : "部门";

  if (!rows.length) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        当前筛选范围内暂无其他业务收入
      </div>
    );
  }

  return (
    <div className="max-h-[68vh] overflow-auto rounded-md border bg-white">
      <table className="border-separate border-spacing-0 text-xs">
        <thead>
          <tr>
            {[dimensionLabel, "类别", "费用"].map((label, index) => (
              <th
                key={label}
                rowSpan={2}
                className="sticky top-0 z-40 border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center font-semibold"
                style={{
                  left: index === 0 ? 0 : index === 1 ? (dimension === "store" ? 120 : 190) : (dimension === "store" ? 250 : 320),
                  minWidth: index === 0 ? (dimension === "store" ? 120 : 190) : index === 1 ? 130 : 150,
                }}
              >
                {label}
              </th>
            ))}
            {report.periods.map((period) => (
              <th
                key={period}
                colSpan={2}
                className="sticky top-0 z-30 border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center font-semibold"
              >
                {String(period).padStart(2, "0")}
              </th>
            ))}
            <th colSpan={4} className="sticky top-0 z-30 border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center font-semibold">
              合计
            </th>
          </tr>
          <tr>
            {report.periods.flatMap((period) => [
              <th key={`${period}-current`} className="sticky top-[33px] z-30 min-w-[105px] border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center">本期</th>,
              <th key={`${period}-prior`} className="sticky top-[33px] z-30 min-w-[105px] border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center">同期</th>,
            ])}
            {[
              ["current", "本期"],
              ["prior", "同期"],
              ["difference", "同比差异（值）"],
              ["rate", "同比比率（%）"],
            ].map(([key, label]) => (
              <th key={key} className="sticky top-[33px] z-30 min-w-[112px] border-b border-r border-slate-400 bg-slate-100 px-2 py-2 text-center">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const group = rowGroup(row, dimension);
            const previous = index > 0 ? rows[index - 1] : null;
            const previousGroup = previous ? rowGroup(previous, dimension) : null;
            const showGroup = row.row_type === "grand_total" || group !== previousGroup;
            const showCategory = row.row_type !== "detail"
              || group !== previousGroup
              || previous?.category !== row.category;
            const stickyBackground = row.row_type === "grand_total"
              ? "bg-blue-100"
              : row.row_type === "category_total"
                ? "bg-slate-100"
                : "bg-white";
            return (
              <tr key={`${dimension}-${row.store_code}-${row.department_code || "store"}-${row.category}-${row.fee_name}-${index}`} className={storeOtherIncomeRowClass(row.row_type)}>
                <td
                  className={cn("sticky left-0 z-20 border-b border-r border-slate-300 px-2 py-1.5", stickyBackground)}
                  style={{ minWidth: dimension === "store" ? 120 : 190 }}
                >
                  {showGroup ? group : ""}
                </td>
                <td
                  className={cn("sticky z-20 border-b border-r border-slate-300 px-2 py-1.5", stickyBackground)}
                  style={{ left: dimension === "store" ? 120 : 190, minWidth: 130 }}
                >
                  {showCategory ? row.category : ""}
                </td>
                <td
                  className={cn("sticky z-20 border-b border-r border-slate-300 px-2 py-1.5", stickyBackground)}
                  style={{ left: dimension === "store" ? 250 : 320, minWidth: 150 }}
                >
                  {row.fee_name}
                </td>
                {report.periods.flatMap((period) => {
                  const comparison = row.months[String(period)];
                  return [
                    <td key={`${period}-current`} className="min-w-[105px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums">{formatIncomeWan(comparison.current)}</td>,
                    <td key={`${period}-prior`} className="min-w-[105px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums">{formatIncomeWan(comparison.prior)}</td>,
                  ];
                })}
                <td className="min-w-[112px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums">{formatIncomeWan(row.total.current)}</td>
                <td className="min-w-[112px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums">{formatIncomeWan(row.total.prior)}</td>
                <td className={cn("min-w-[112px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums", row.total.difference < 0 && "text-red-600")}>{formatIncomeWan(row.total.difference)}</td>
                <td className={cn("min-w-[112px] border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums", (row.total.rate ?? 0) < 0 && "text-red-600")}>{formatIncomeRate(row.total.rate)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function StoreOtherBusinessIncomePage() {
  const defaults = useMemo(defaultPeriod, []);
  const { selectedStoreId } = useStore();
  const [draft, setDraft] = useState<Filters>({ ...defaults, storeId: STORE_OTHER_INCOME_ALL_STORES });
  const [submitted, setSubmitted] = useState<Filters>({ ...defaults, storeId: STORE_OTHER_INCOME_ALL_STORES });
  const [dimension, setDimension] = useState<"store" | "department">("store");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/store-other-business-income/stores"],
    queryFn: () => apiGet("/api/sales/reports/store-other-business-income/stores"),
  });
  useEffect(() => {
    if (!selectedStoreId || !storesQuery.data?.length) return;
    const selected = storesQuery.data.find((store) => String(store.store_id) === String(selectedStoreId));
    if (!selected) return;
    setDraft((current) => ({ ...current, storeId: selected.store_code }));
  }, [selectedStoreId, storesQuery.data]);

  const queryString = useMemo(
    () => buildStoreOtherIncomeParams(submitted).toString(),
    [submitted],
  );
  const reportQuery = useQuery<StoreOtherIncomeReport>({
    queryKey: ["/api/sales/reports/store-other-business-income", queryString],
    queryFn: () => apiGet(`/api/sales/reports/store-other-business-income?${queryString}`),
  });

  const exportReport = async () => {
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/store-other-business-income/export?${queryString}`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `门店其他业务收入_${submitted.financialYear}年01-${String(submitted.endPeriod).padStart(2, "0")}期.xlsx`;
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

  const report = reportQuery.data;
  return (
    <div className="space-y-5 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">门店其他业务收入</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          对比本年与上年同期的其他业务收入，金额单位为万元；科目按财务凭证明细归集，排除集团数字化/信息部门，并保留当前账号的门店、部门数据权限。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>会计年度</Label>
              <Select value={String(draft.financialYear)} onValueChange={(value) => setDraft((current) => ({ ...current, financialYear: Number(value) }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 6 }, (_, index) => defaults.financialYear - index).map((year) => (
                    <SelectItem key={year} value={String(year)}>{year}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>门店</Label>
              <Select value={draft.storeId} onValueChange={(storeId) => setDraft((current) => ({ ...current, storeId }))} disabled={storesQuery.isLoading}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={STORE_OTHER_INCOME_ALL_STORES}>全部授权门店</SelectItem>
                  {(storesQuery.data ?? []).map((store) => (
                    <SelectItem key={store.store_code} value={store.store_code}>{store.store_code} · {store.store_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={() => { setSubmitted({ ...draft }); setExportError(null); }} disabled={reportQuery.isFetching}>
                {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                查询
              </Button>
              <Button variant="outline" onClick={exportReport} disabled={!report || exporting}>
                {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                导出Excel
              </Button>
            </div>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            当前口径：{submitted.financialYear}年 01–{String(submitted.endPeriod).padStart(2, "0")}期，对比 {submitted.financialYear - 1} 年同期。
          </div>
          {exportError ? <div className="mt-3 text-sm text-red-600">{exportError}</div> : null}
        </CardContent>
      </Card>

      {reportQuery.isLoading ? (
        <div className="flex min-h-60 items-center justify-center text-sm text-muted-foreground"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载财务报表…</div>
      ) : reportQuery.error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">报表加载失败，请检查数据权限或稍后重试。</div>
      ) : report ? (
        <Card>
          <CardHeader className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle className="text-base">收入明细</CardTitle>
              <div className="text-xs text-muted-foreground">
                {report.quality.store_count} 家门店 · {report.quality.department_count} 个部门 · {report.scope_description}
              </div>
            </div>
            <Tabs value={dimension} onValueChange={(value) => setDimension(value as "store" | "department") }>
              <TabsList>
                <TabsTrigger value="store">门店口径</TabsTrigger>
                <TabsTrigger value="department">部门口径</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent><IncomeTable report={report} dimension={dimension} /></CardContent>
        </Card>
      ) : null}
    </div>
  );
}
