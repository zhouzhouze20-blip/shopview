import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, apiRequest } from "@/lib/api";
import { contentDispositionFilename, scheduleObjectUrlRevoke } from "@/lib/hdyy01-report";

const REPORT_ENDPOINT = "/api/sales/reports/inventory-movement-detail";
const VISIBLE_ROW_LIMIT = 5000;

type Filters = {
  start_date: string;
  end_date: string;
  group: string;
  supplier: string;
  goods_code: string;
  goods_name: string;
  barcode: string;
};

type MovementRow = {
  sequence: number;
  store_display: string;
  group_display: string;
  supplier_display: string;
  goods_name: string;
  goods_code: string;
  barcode: string;
  subinventory_display: string;
  accounting_date: string;
  transaction_label: string;
  purchase_price_tax_included: number;
  selling_price: number;
  operation_method: string;
  sample_label: string;
  batch_sequence: number;
  increase_quantity: number;
  increase_amount_tax_included: number;
  increase_amount_tax_excluded: number;
  decrease_quantity: number;
  decrease_amount_tax_included: number;
  decrease_amount_tax_excluded: number;
  balance_quantity: number;
  balance_cost_tax_included: number;
  balance_cost_tax_excluded: number;
  memo: string;
  specification: string | null;
  manufacturer_article_number: string | null;
};

type MovementSummary = {
  total_count: number;
  increase_quantity: number;
  increase_amount_tax_included: number;
  increase_amount_tax_excluded: number;
  decrease_quantity: number;
  decrease_amount_tax_included: number;
  decrease_amount_tax_excluded: number;
};

type MovementResponse = {
  rows: MovementRow[];
  summary: MovementSummary;
  coverage: {
    min_occurrence_date?: string | null;
    max_occurrence_date?: string | null;
    max_accounting_date?: string | null;
  };
  source_note: string;
};

type Column = {
  key: keyof MovementRow;
  label: string;
  width: string;
  digits?: number;
};

const STATIC_COLUMNS: readonly Column[] = [
  { key: "store_display", label: "门店", width: "min-w-44" },
  { key: "group_display", label: "柜组", width: "min-w-64" },
  { key: "supplier_display", label: "供应商", width: "min-w-72" },
  { key: "goods_name", label: "商品名称", width: "min-w-56" },
  { key: "goods_code", label: "商品代码", width: "min-w-28" },
  { key: "barcode", label: "商品条码", width: "min-w-40" },
  { key: "subinventory_display", label: "子库存", width: "min-w-24" },
  { key: "accounting_date", label: "记账日期", width: "min-w-28" },
  { key: "transaction_label", label: "摘要", width: "min-w-24" },
  { key: "purchase_price_tax_included", label: "含税进价", width: "min-w-28 text-right", digits: 4 },
  { key: "selling_price", label: "售价", width: "min-w-24 text-right", digits: 2 },
  { key: "operation_method", label: "经营方式", width: "min-w-24" },
  { key: "sample_label", label: "样品?", width: "min-w-20" },
  { key: "batch_sequence", label: "批次序号", width: "min-w-28 text-right", digits: 0 },
];

const INCREASE_COLUMNS: readonly Column[] = [
  { key: "increase_quantity", label: "数量", width: "min-w-24 text-right", digits: 4 },
  { key: "increase_amount_tax_included", label: "含税进价金额", width: "min-w-36 text-right", digits: 4 },
  { key: "increase_amount_tax_excluded", label: "不含税进价金额", width: "min-w-40 text-right", digits: 4 },
];

const DECREASE_COLUMNS: readonly Column[] = [
  { key: "decrease_quantity", label: "数量", width: "min-w-24 text-right", digits: 4 },
  { key: "decrease_amount_tax_included", label: "含税进价金额", width: "min-w-36 text-right", digits: 4 },
  { key: "decrease_amount_tax_excluded", label: "不含税进价金额", width: "min-w-40 text-right", digits: 4 },
];

const BALANCE_COLUMNS: readonly Column[] = [
  { key: "balance_quantity", label: "数量", width: "min-w-24 text-right", digits: 4 },
  { key: "balance_cost_tax_included", label: "含税成本金额", width: "min-w-36 text-right", digits: 4 },
  { key: "balance_cost_tax_excluded", label: "不含税成本金额", width: "min-w-40 text-right", digits: 4 },
];

const TRAILING_COLUMNS: readonly Column[] = [
  { key: "memo", label: "备注", width: "min-w-48" },
  { key: "specification", label: "规格", width: "min-w-36" },
  { key: "manufacturer_article_number", label: "厂商货号", width: "min-w-36" },
];

const localDateString = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const emptyFilters = (): Filters => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dateValue = localDateString(yesterday);
  return {
    start_date: dateValue,
    end_date: dateValue,
    group: "",
    supplier: "",
    goods_code: "",
    goods_name: "",
    barcode: "",
  };
};

const buildQuery = (filters: Filters, includePaging: boolean) => {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    const trimmed = value.trim();
    if (trimmed) query.set(key, trimmed);
  });
  if (includePaging) {
    query.set("limit", String(VISIBLE_ROW_LIMIT));
    query.set("offset", "0");
  }
  return query.toString();
};

const formatNumber = (value: unknown, digits = 4) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(numeric);
};

const renderCell = (row: MovementRow, column: Column) => {
  const value = row[column.key];
  if (column.digits !== undefined) return formatNumber(value, column.digits);
  return String(value ?? "").trim() || "—";
};

const TEXT_FILTERS: readonly { key: keyof Filters; label: string; placeholder: string }[] = [
  { key: "supplier", label: "供应商", placeholder: "编码或名称" },
  { key: "group", label: "柜组", placeholder: "编码或名称" },
  { key: "goods_code", label: "商品代码", placeholder: "部分编码" },
  { key: "goods_name", label: "商品名称", placeholder: "名称关键字" },
  { key: "barcode", label: "商品条码", placeholder: "部分条码" },
];

export default function InventoryMovementDetailReportPage() {
  const [draft, setDraft] = useState<Filters>(() => emptyFilters());
  const [submitted, setSubmitted] = useState<Filters>(() => emptyFilters());
  const [hasSearched, setHasSearched] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const queryString = useMemo(() => buildQuery(submitted, true), [submitted]);
  const reportQuery = useQuery<MovementResponse>({
    queryKey: [REPORT_ENDPOINT, queryString],
    queryFn: () => apiGet(`${REPORT_ENDPOINT}?${queryString}`),
    enabled: hasSearched,
  });

  const update = (key: keyof Filters, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = () => {
    if (!draft.start_date || !draft.end_date) {
      setMessage("请选择发生开始日期和结束日期");
      return;
    }
    if (draft.start_date > draft.end_date) {
      setMessage("发生开始日期不能晚于结束日期");
      return;
    }
    const sameQuery = hasSearched && JSON.stringify(draft) === JSON.stringify(submitted);
    setSubmitted({ ...draft });
    setHasSearched(true);
    setMessage(null);
    if (sameQuery) void reportQuery.refetch();
  };

  const reset = () => {
    const cleared = emptyFilters();
    setDraft(cleared);
    setSubmitted(cleared);
    setHasSearched(false);
    setMessage(null);
  };

  const exportReport = async () => {
    setExporting(true);
    setMessage(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`${REPORT_ENDPOINT}/export?${buildQuery(submitted, false)}`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? "商品进销存明细报表.xlsx";
      objectUrl = URL.createObjectURL(blob);
      anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导出失败，请稍后重试");
    } finally {
      anchor?.remove();
      if (objectUrl) scheduleObjectUrlRevoke(objectUrl);
      setExporting(false);
    }
  };

  const response = hasSearched ? reportQuery.data : undefined;
  const rows = response?.rows ?? [];
  const summary = response?.summary;
  const totalCount = Number(summary?.total_count || 0);
  const dataThroughDate = response?.coverage?.max_occurrence_date?.slice(0, 10) || null;
  const requestedBeyondCoverage = Boolean(dataThroughDate && submitted.end_date > dataThroughDate);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">进销存明细报表</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          按原 ERP 商品进销存明细口径展示增、减和每笔业务后的期末库存，默认查询昨天。
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">查询条件</CardTitle>
          <CardDescription>发生日期起止均包含；编码和名称支持模糊查询。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:max-w-3xl">
            <div className="space-y-2">
              <Label htmlFor="movement-start-date">发生开始日期</Label>
              <Input id="movement-start-date" type="date" value={draft.start_date} onChange={(event) => update("start_date", event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="movement-end-date">发生结束日期</Label>
              <Input id="movement-end-date" type="date" value={draft.end_date} onChange={(event) => update("end_date", event.target.value)} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {TEXT_FILTERS.map((filter) => (
              <div key={filter.key} className="space-y-2">
                <Label htmlFor={`movement-${filter.key}`}>{filter.label}</Label>
                <Input
                  id={`movement-${filter.key}`}
                  value={draft[filter.key]}
                  placeholder={filter.placeholder}
                  onChange={(event) => update(filter.key, event.target.value)}
                />
              </div>
            ))}
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={reset}>重置</Button>
            <Button onClick={submit} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={exportReport} disabled={!response || exporting || reportQuery.isFetching}>
              {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {exporting ? "导出中…" : "导出 Excel"}
            </Button>
          </div>
          {message && <p role="alert" className="text-sm text-red-600">{message}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">商品进销存明细</CardTitle>
          <CardDescription>{response?.source_note || "按当前账号的数据范围查询进销存明细。"}</CardDescription>
        </CardHeader>
        <CardContent>
          {requestedBeyondCoverage && (
            <div role="status" className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              当前本地同步数据只覆盖至 {dataThroughDate}，所选结束日期为 {submitted.end_date}；超出覆盖日期的空白不能解释为源库无业务。
            </div>
          )}
          {!hasSearched ? (
            <div className="py-16 text-center text-sm text-muted-foreground">请选择日期并点击“查询”。</div>
          ) : reportQuery.isLoading ? (
            <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询进销存明细…
            </div>
          ) : reportQuery.error ? (
            <div role="alert" className="py-16 text-center text-sm text-red-600">报表加载失败，请检查权限或数据同步状态。</div>
          ) : rows.length === 0 ? (
            <div className="py-16 text-center text-sm text-muted-foreground">当前条件下没有进销存明细。</div>
          ) : (
            <>
              <div className="max-h-[72vh] overflow-auto overscroll-contain rounded-md border">
                <table className="w-full min-w-[3900px] caption-bottom text-sm">
                  <TableHeader>
                    <TableRow>
                      <TableHead rowSpan={2} className="sticky left-0 top-0 z-50 min-w-16 bg-white text-center">行号</TableHead>
                      {STATIC_COLUMNS.map((column) => (
                        <TableHead key={column.key} rowSpan={2} className={`sticky top-0 z-40 bg-white ${column.width}`}>{column.label}</TableHead>
                      ))}
                      <TableHead colSpan={3} className="sticky top-0 z-40 bg-blue-50 text-center">增</TableHead>
                      <TableHead colSpan={3} className="sticky top-0 z-40 bg-rose-50 text-center">减</TableHead>
                      <TableHead colSpan={3} className="sticky top-0 z-40 bg-emerald-50 text-center">存</TableHead>
                      {TRAILING_COLUMNS.map((column) => (
                        <TableHead key={column.key} rowSpan={2} className={`sticky top-0 z-40 bg-white ${column.width}`}>{column.label}</TableHead>
                      ))}
                    </TableRow>
                    <TableRow>
                      {INCREASE_COLUMNS.map((column) => <TableHead key={column.key} className={`sticky top-10 z-40 bg-blue-50 ${column.width}`}>{column.label}</TableHead>)}
                      {DECREASE_COLUMNS.map((column) => <TableHead key={column.key} className={`sticky top-10 z-40 bg-rose-50 ${column.width}`}>{column.label}</TableHead>)}
                      {BALANCE_COLUMNS.map((column) => <TableHead key={column.key} className={`sticky top-10 z-40 bg-emerald-50 ${column.width}`}>{column.label}</TableHead>)}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row, index) => (
                      <TableRow key={`${row.sequence}-${index}`}>
                        <TableCell className="sticky left-0 z-10 bg-white text-center tabular-nums">{index + 1}</TableCell>
                        {STATIC_COLUMNS.map((column) => <TableCell key={column.key} className={column.width}>{renderCell(row, column)}</TableCell>)}
                        {INCREASE_COLUMNS.map((column) => <TableCell key={column.key} className={`${column.width} bg-blue-50/30 tabular-nums`}>{renderCell(row, column)}</TableCell>)}
                        {DECREASE_COLUMNS.map((column) => <TableCell key={column.key} className={`${column.width} bg-rose-50/30 tabular-nums`}>{renderCell(row, column)}</TableCell>)}
                        {BALANCE_COLUMNS.map((column) => <TableCell key={column.key} className={`${column.width} bg-emerald-50/30 tabular-nums`}>{renderCell(row, column)}</TableCell>)}
                        {TRAILING_COLUMNS.map((column) => <TableCell key={column.key} className={column.width}>{renderCell(row, column)}</TableCell>)}
                      </TableRow>
                    ))}
                  </TableBody>
                  {summary && (
                    <TableFooter>
                      <TableRow className="bg-slate-100 hover:bg-slate-100">
                        <TableCell colSpan={15} className="font-semibold">合计（共 {totalCount.toLocaleString("zh-CN")} 行）</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.increase_quantity)}</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.increase_amount_tax_included)}</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.increase_amount_tax_excluded)}</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.decrease_quantity)}</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.decrease_amount_tax_included)}</TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">{formatNumber(summary.decrease_amount_tax_excluded)}</TableCell>
                        <TableCell colSpan={6} />
                      </TableRow>
                    </TableFooter>
                  )}
                </table>
              </div>
              {totalCount > rows.length && (
                <p className="mt-3 text-sm text-amber-700">
                  结果共 {totalCount.toLocaleString("zh-CN")} 行，页面展示前 {rows.length.toLocaleString("zh-CN")} 行；完整明细请导出 Excel。
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
