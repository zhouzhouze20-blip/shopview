import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import {
  InventoryFilterAutocomplete,
  type InventoryFilterField,
  type InventoryFilterOption,
} from "@/components/inventory-filter-autocomplete";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, apiRequest } from "@/lib/api";
import { contentDispositionFilename, scheduleObjectUrlRevoke } from "@/lib/hdyy01-report";


const VISIBLE_ROW_LIMIT = 5000;

type InventoryFilters = {
  supplier: string;
  group: string;
  goods_code: string;
  goods_name: string;
  barcode: string;
};

type InventoryDateFilters = {
  start_date: string;
  end_date: string;
};

type InventoryRow = {
  inventory_date?: string;
  store_display: string;
  floor_display: string;
  area_display: string;
  goods_code: string;
  barcode: string;
  brand_display: string;
  goods_name: string;
  specification: string | null;
  supplier_display: string;
  operation_method: string;
  group_display: string;
  subinventory_display: string;
  category_display: string;
  sample_label: string;
  selling_price: number | null;
  average_purchase_price_tax_included: number | null;
  inventory_quantity: number;
  retail_amount: number | null;
  inventory_purchase_amount_tax_excluded: number;
  inventory_purchase_amount_tax_included: number;
};

type InventorySummary = {
  total_count: number;
  inventory_quantity: number;
  retail_amount: number;
  inventory_purchase_amount_tax_excluded: number;
  inventory_purchase_amount_tax_included: number;
};

type InventoryResponse = {
  rows: InventoryRow[];
  summary: InventorySummary;
  limit: number;
  offset: number;
  source_note: string;
};

type InventoryColumn = {
  key: keyof InventoryRow;
  label: string;
  kind?: "money" | "precise" | "quantity";
  className?: string;
};

const REALTIME_COLUMNS: readonly InventoryColumn[] = [
  { key: "store_display", label: "门店", className: "min-w-40" },
  { key: "floor_display", label: "楼层", className: "min-w-40" },
  { key: "area_display", label: "库区", className: "min-w-48" },
  { key: "goods_code", label: "商品代码", className: "min-w-28" },
  { key: "barcode", label: "商品条码", className: "min-w-40" },
  { key: "brand_display", label: "品牌", className: "min-w-44" },
  { key: "goods_name", label: "商品名称", className: "min-w-56" },
  { key: "specification", label: "规格", className: "min-w-28" },
  { key: "supplier_display", label: "供应商", className: "min-w-72" },
  { key: "operation_method", label: "经营方式", className: "min-w-24" },
  { key: "group_display", label: "柜组", className: "min-w-56" },
  { key: "subinventory_display", label: "子库存", className: "min-w-24" },
  { key: "category_display", label: "商品类别", className: "min-w-32" },
  { key: "sample_label", label: "样品?", className: "min-w-20" },
  { key: "selling_price", label: "售价", kind: "money", className: "min-w-24 text-right" },
  {
    key: "average_purchase_price_tax_included",
    label: "平均进价(含税)",
    kind: "precise",
    className: "min-w-36 text-right",
  },
  { key: "inventory_quantity", label: "库存数量", kind: "quantity", className: "min-w-28 text-right" },
  { key: "retail_amount", label: "零售金额", kind: "money", className: "min-w-28 text-right" },
  {
    key: "inventory_purchase_amount_tax_excluded",
    label: "库存不含税进价金额",
    kind: "precise",
    className: "min-w-44 text-right",
  },
  {
    key: "inventory_purchase_amount_tax_included",
    label: "库存含税进价金额",
    kind: "precise",
    className: "min-w-44 text-right",
  },
];

const HISTORICAL_COLUMNS: readonly InventoryColumn[] = [
  { key: "inventory_date", label: "日期", className: "min-w-28" },
  { key: "area_display", label: "库区", className: "min-w-48" },
  { key: "supplier_display", label: "供应商", className: "min-w-72" },
  { key: "store_display", label: "门店", className: "min-w-40" },
  { key: "group_display", label: "柜组", className: "min-w-56" },
  { key: "subinventory_display", label: "子库存", className: "min-w-24" },
  { key: "operation_method", label: "经营方式", className: "min-w-24" },
  { key: "goods_code", label: "商品编码", className: "min-w-28" },
  { key: "barcode", label: "商品条码", className: "min-w-40" },
  { key: "goods_name", label: "商品名称", className: "min-w-56" },
  { key: "specification", label: "规格型号", className: "min-w-28" },
  { key: "brand_display", label: "品牌", className: "min-w-44" },
  { key: "category_display", label: "商品类别", className: "min-w-32" },
  { key: "sample_label", label: "样品?", className: "min-w-20" },
  { key: "selling_price", label: "售价", kind: "money", className: "min-w-24 text-right" },
  { key: "inventory_quantity", label: "库存数量", kind: "quantity", className: "min-w-28 text-right" },
  {
    key: "inventory_purchase_amount_tax_included",
    label: "库存含税进价金额",
    kind: "precise",
    className: "min-w-44 text-right",
  },
  {
    key: "inventory_purchase_amount_tax_excluded",
    label: "库存不含税进价金额",
    kind: "precise",
    className: "min-w-44 text-right",
  },
  { key: "retail_amount", label: "库存售价金额", kind: "money", className: "min-w-32 text-right" },
];

const emptyFilters = (): InventoryFilters => ({
  supplier: "",
  group: "",
  goods_code: "",
  goods_name: "",
  barcode: "",
});

const localDateString = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const defaultHistoricalDates = (): InventoryDateFilters => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const value = localDateString(yesterday);
  return { start_date: value, end_date: value };
};

const FILTER_FIELDS: readonly {
  key: InventoryFilterField;
  label: string;
  placeholder: string;
  inputMode?: "numeric";
}[] = [
  { key: "supplier", label: "供应商", placeholder: "输入编码或名称" },
  { key: "group", label: "柜组", placeholder: "输入编码或名称" },
  { key: "goods_code", label: "商品代码", placeholder: "输入部分编码" },
  { key: "goods_name", label: "商品名称", placeholder: "输入名称关键字" },
  { key: "barcode", label: "商品条码", placeholder: "输入部分条码", inputMode: "numeric" },
];

const buildQuery = (
  filters: InventoryFilters,
  includePaging = true,
  dates?: InventoryDateFilters,
) => {
  const query = new URLSearchParams();
  if (dates) {
    query.set("start_date", dates.start_date);
    query.set("end_date", dates.end_date);
  }
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

const formatNumber = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
};

const renderValue = (row: InventoryRow, column: InventoryColumn) => {
  const value = row[column.key];
  if (column.kind === "money") return formatNumber(value as number | null, 2);
  if (column.kind === "precise" || column.kind === "quantity") return formatNumber(value as number | null, 4);
  return String(value ?? "").trim() || "—";
};

type InventoryReportMode = "realtime" | "historical";

function InventoryHeading({ mode }: { mode: InventoryReportMode }) {
  if (mode === "historical") {
    return <h1 className="text-2xl font-semibold text-slate-900">历史库存明细报表</h1>;
  }
  return <h1 className="text-2xl font-semibold text-slate-900">实时库存查询</h1>;
}

function InventoryDetailReport({ mode }: { mode: InventoryReportMode }) {
  const isHistorical = mode === "historical";
  const reportEndpoint = isHistorical
    ? "/api/sales/reports/historical-inventory-detail"
    : "/api/sales/reports/inventory-detail";
  const optionsEndpoint = `${reportEndpoint}/options`;
  const columns = isHistorical ? HISTORICAL_COLUMNS : REALTIME_COLUMNS;
  const [draft, setDraft] = useState<InventoryFilters>(() => emptyFilters());
  const [draftDisplay, setDraftDisplay] = useState<InventoryFilters>(() => emptyFilters());
  const [submitted, setSubmitted] = useState<InventoryFilters>(() => emptyFilters());
  const [draftDates, setDraftDates] = useState<InventoryDateFilters>(() => defaultHistoricalDates());
  const [submittedDates, setSubmittedDates] = useState<InventoryDateFilters>(() => defaultHistoricalDates());
  const [hasSearched, setHasSearched] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const queryString = useMemo(
    () => buildQuery(submitted, true, isHistorical ? submittedDates : undefined),
    [isHistorical, submitted, submittedDates],
  );
  const reportQuery = useQuery<InventoryResponse>({
    queryKey: [reportEndpoint, queryString],
    queryFn: () => apiGet(`${reportEndpoint}?${queryString}`),
    enabled: hasSearched,
  });

  const updateDraftInput = (key: InventoryFilterField, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setDraftDisplay((current) => ({ ...current, [key]: value }));
  };

  const selectDraftOption = (key: InventoryFilterField, option: InventoryFilterOption) => {
    setDraft((current) => ({ ...current, [key]: option.value }));
    setDraftDisplay((current) => ({ ...current, [key]: option.label }));
  };

  const submit = () => {
    if (isHistorical && (!draftDates.start_date || !draftDates.end_date)) {
      setExportError("请选择库存开始日期和结束日期");
      return;
    }
    if (isHistorical && draftDates.start_date > draftDates.end_date) {
      setExportError("库存开始日期不能晚于结束日期");
      return;
    }
    const isSameQuery = hasSearched
      && JSON.stringify(draft) === JSON.stringify(submitted)
      && (!isHistorical || JSON.stringify(draftDates) === JSON.stringify(submittedDates));
    setSubmitted({ ...draft });
    setSubmittedDates({ ...draftDates });
    setHasSearched(true);
    setExportError(null);
    if (isSameQuery) {
      void reportQuery.refetch();
    }
  };

  const reset = () => {
    const cleared = emptyFilters();
    setDraft(cleared);
    setDraftDisplay(cleared);
    setSubmitted(cleared);
    const defaultDates = defaultHistoricalDates();
    setDraftDates(defaultDates);
    setSubmittedDates(defaultDates);
    setHasSearched(false);
    setExportError(null);
  };

  const exportReport = async () => {
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const exportQuery = buildQuery(submitted, false, isHistorical ? submittedDates : undefined);
      const response = await apiRequest(`${reportEndpoint}/export?${exportQuery}`);
      const blob = await response.blob();
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? (isHistorical ? "历史库存明细报表.xlsx" : "实时库存查询.xlsx");
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

  const response = hasSearched ? reportQuery.data : undefined;
  const rows = response?.rows ?? [];
  const summary = response?.summary;
  const totalCount = Number(summary?.total_count || 0);
  const quantityColumnIndex = columns.findIndex((column) => column.key === "inventory_quantity");
  const summaryColumns = quantityColumnIndex >= 0 ? columns.slice(quantityColumnIndex) : [];

  return (
    <div className="space-y-6 p-6">
      <div>
        <div>
          <InventoryHeading mode={mode} />
          <p className="mt-1 text-sm text-muted-foreground">
            {isHistorical
              ? "对应原 ERP 历史库存 SQL，按库存日期和当前账号的数据范围查询历史快照。"
              : "对应原 ERP 库存 SQL；原表“楼层/库区”按柜组的上两级管理架构展示。"}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">查询条件</CardTitle>
          <CardDescription>
            {isHistorical
              ? "先选择库存日期，再输入部分编码或名称；日期起止均包含在查询范围内。"
              : "输入部分编码或名称，从账号数据范围内的匹配项中选择；仅查询库存数量大于 0 的商品。"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isHistorical && (
            <div className="grid gap-4 sm:grid-cols-2 lg:max-w-xl">
              <div className="space-y-2">
                <Label htmlFor="historical-inventory-start-date">库存开始日期</Label>
                <Input
                  id="historical-inventory-start-date"
                  type="date"
                  value={draftDates.start_date}
                  onChange={(event) => setDraftDates((current) => ({ ...current, start_date: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="historical-inventory-end-date">库存结束日期</Label>
                <Input
                  id="historical-inventory-end-date"
                  type="date"
                  value={draftDates.end_date}
                  onChange={(event) => setDraftDates((current) => ({ ...current, end_date: event.target.value }))}
                />
              </div>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {FILTER_FIELDS.map((filter) => (
              <InventoryFilterAutocomplete
                key={filter.key}
                field={filter.key}
                label={filter.label}
                placeholder={filter.placeholder}
                inputMode={filter.inputMode}
                displayValue={draftDisplay[filter.key]}
                filterValue={draft[filter.key]}
                onInputChange={(value) => updateDraftInput(filter.key, value)}
                onSelect={(option) => selectDraftOption(filter.key, option)}
                optionsEndpoint={optionsEndpoint}
                dates={isHistorical ? draftDates : undefined}
              />
            ))}
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={reset}>重置</Button>
            <Button onClick={submit} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={exportReport} disabled={exporting || reportQuery.isFetching || !response}>
              {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {exporting ? "导出中…" : "导出 Excel"}
            </Button>
          </div>
          {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">库存明细</CardTitle>
          <CardDescription>{response?.source_note || "按当前账号的数据范围查询库存。"}</CardDescription>
        </CardHeader>
        <CardContent>
          {!hasSearched ? (
            <div className="py-16 text-center text-sm text-muted-foreground">请输入查询条件并点击“查询”。</div>
          ) : reportQuery.isLoading ? (
            <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询库存…
            </div>
          ) : reportQuery.error ? (
            <div role="alert" className="py-16 text-center text-sm text-red-600">库存报表加载失败，请检查权限或数据源。</div>
          ) : rows.length === 0 ? (
            <div className="py-16 text-center text-sm text-muted-foreground">当前条件下没有库存明细。</div>
          ) : (
            <>
              <div className="max-h-[72vh] overflow-auto overscroll-contain rounded-md border">
                <table className="w-full min-w-[3300px] caption-bottom text-sm">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 top-0 z-40 min-w-16 bg-white !h-10 !px-3 !py-2 text-center">行号</TableHead>
                      {columns.map((column) => (
                        <TableHead
                          key={column.key}
                          className={`sticky top-0 z-30 bg-white !h-10 !px-3 !py-2 ${column.className ?? ""}`}
                        >
                          {column.label}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row, index) => (
                      <TableRow key={`${row.inventory_date ?? "current"}-${row.group_display}-${row.goods_code}-${row.subinventory_display}-${index}`}>
                        <TableCell className="sticky left-0 z-10 bg-white !px-3 !py-1.5 text-center tabular-nums">{index + 1}</TableCell>
                        {columns.map((column) => (
                          <TableCell key={column.key} className={`!px-3 !py-1.5 ${column.className ?? ""}`}>
                            {renderValue(row, column)}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                  {summary && (
                    <TableFooter>
                      <TableRow className="bg-slate-100 hover:bg-slate-100">
                        <TableCell colSpan={quantityColumnIndex + 1} className="!px-3 !py-2 font-semibold">
                          合计（共 {totalCount.toLocaleString("zh-CN")} 行）
                        </TableCell>
                        {summaryColumns.map((column) => (
                          <TableCell key={column.key} className="!px-3 !py-2 text-right font-semibold tabular-nums">
                            {formatNumber(
                              summary[column.key as keyof InventorySummary] as number,
                              column.kind === "money" ? 2 : 4,
                            )}
                          </TableCell>
                        ))}
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

export function HistoricalInventoryDetailReportPage() {
  return <InventoryDetailReport mode="historical" />;
}

export default function InventoryDetailReportPage() {
  return <InventoryDetailReport mode="realtime" />;
}
