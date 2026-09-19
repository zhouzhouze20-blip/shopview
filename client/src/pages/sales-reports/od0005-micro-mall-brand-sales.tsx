import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  buildOd0005Params,
  formatOd0005Number,
  OD0005_ALL_DEPARTMENTS,
  OD0005_SHEETS,
  type Od0005DailyRow,
  type Od0005Response,
  type Od0005Row,
  type Od0005Sheet,
} from "@/lib/od0005-micro-mall";
import { contentDispositionFilename, scheduleObjectUrlRevoke } from "@/lib/od0002-report";


type StoreOption = { store_id: string | number; store_code: string; store_name: string };
type Filters = {
  startDate: string;
  endDate: string;
  storeId: string;
  departmentId: string;
  sheet: Od0005Sheet;
};

type DepartmentRow = {
  store_code: string;
  department_code: string;
  department_name: string;
  sales_quantity: number;
  price_amount: number;
  yzq_amount: number;
  other_payment_amount: number;
  sales_before_discount: number;
  sales_revenue: number;
  gross_profit: number;
  gross_margin: number | null;
};

const COLUMNS: Array<{
  key: keyof Od0005Row;
  label: string;
  kind?: "qty" | "amount" | "rate";
  width: string;
}> = [
  { key: "store_code", label: "门店", width: "min-w-[76px]" },
  { key: "department_code", label: "部门", width: "min-w-[220px]" },
  { key: "group_code", label: "柜组", width: "min-w-[130px]" },
  { key: "group_name", label: "柜组名称", width: "min-w-[240px]" },
  { key: "sales_quantity", label: "销售数量", kind: "qty", width: "min-w-[110px]" },
  { key: "price_amount", label: "售价金额", kind: "amount", width: "min-w-[130px]" },
  { key: "sales_before_discount", label: "销售收入+总折扣(A)", kind: "amount", width: "min-w-[180px]" },
  { key: "sales_revenue", label: "销售收入", kind: "amount", width: "min-w-[130px]" },
  { key: "gross_profit", label: "毛利", kind: "amount", width: "min-w-[130px]" },
  { key: "gross_margin", label: "毛利率", kind: "rate", width: "min-w-[100px]" },
  { key: "yzq_amount", label: "YZQ", kind: "amount", width: "min-w-[120px]" },
  { key: "other_payment_amount", label: "其他支付", kind: "amount", width: "min-w-[130px]" },
  { key: "nzd_amount", label: "NZD", kind: "amount", width: "min-w-[120px]" },
];

const DEPARTMENT_COLUMNS: Array<{
  key: keyof DepartmentRow;
  label: string;
  kind?: "qty" | "amount" | "rate";
  width: string;
}> = [
  { key: "store_code", label: "门店", width: "min-w-[76px]" },
  { key: "department_code", label: "部门", width: "min-w-[240px]" },
  { key: "sales_quantity", label: "销售数量", kind: "qty", width: "min-w-[110px]" },
  { key: "price_amount", label: "应收金额", kind: "amount", width: "min-w-[130px]" },
  { key: "yzq_amount", label: "有赞卡券", kind: "amount", width: "min-w-[130px]" },
  { key: "other_payment_amount", label: "礼券", kind: "amount", width: "min-w-[130px]" },
  { key: "sales_before_discount", label: "销售收入", kind: "amount", width: "min-w-[130px]" },
  { key: "sales_revenue", label: "销售收入(内转)", kind: "amount", width: "min-w-[150px]" },
  { key: "gross_profit", label: "毛利额", kind: "amount", width: "min-w-[130px]" },
  { key: "gross_margin", label: "毛利率", kind: "rate", width: "min-w-[100px]" },
];

function yesterday(): string {
  const value = new Date();
  value.setDate(value.getDate() - 1);
  return value.toLocaleDateString("en-CA");
}

function displayValue(row: Od0005Row, column: (typeof COLUMNS)[number]): string {
  if (column.key === "department_code") {
    return [row.department_code, row.department_name].filter(Boolean).join(" ");
  }
  const value = row[column.key];
  if (column.kind) return formatOd0005Number(value as number | null, column.kind);
  return String(value ?? "");
}

function displayDepartment(row: Pick<Od0005Row, "department_code" | "department_name">): string {
  return [row.department_code, row.department_name].filter(Boolean).join(" ");
}

function departmentSummary(rows: Od0005Row[]): DepartmentRow[] {
  const grouped = new Map<string, DepartmentRow>();
  for (const source of rows) {
    const key = `${source.department_code}\u0000${source.department_name}`;
    const row = grouped.get(key) ?? {
      store_code: source.store_code,
      department_code: source.department_code,
      department_name: source.department_name,
      sales_quantity: 0,
      price_amount: 0,
      yzq_amount: 0,
      other_payment_amount: 0,
      sales_before_discount: 0,
      sales_revenue: 0,
      gross_profit: 0,
      gross_margin: null,
    };
    row.sales_quantity += source.sales_quantity;
    row.price_amount += source.price_amount;
    row.yzq_amount += source.yzq_amount;
    row.other_payment_amount += source.other_payment_amount;
    row.sales_before_discount += source.sales_before_discount;
    row.sales_revenue += source.sales_revenue;
    row.gross_profit += source.gross_profit;
    row.gross_margin = row.sales_revenue ? row.gross_profit / row.sales_revenue : null;
    grouped.set(key, row);
  }
  return [...grouped.values()];
}

function hasCurrentDailySales(row: Od0005DailyRow): boolean {
  return row.daily.some((day) => day.sales_current !== 0);
}

function shortYear(year: number): string {
  return `${String(year).slice(-2)}年`;
}

export default function Od0005MicroMallBrandSalesPage() {
  const { selectedStoreId } = useStore();
  const defaultDate = useMemo(() => yesterday(), []);
  const [draft, setDraft] = useState<Filters>({
    startDate: defaultDate,
    endDate: defaultDate,
    storeId: "",
    departmentId: OD0005_ALL_DEPARTMENTS,
    sheet: "brand",
  });
  const [submitted, setSubmitted] = useState<Filters | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<StoreOption[]>({
    queryKey: ["/api/sales/reports/od0005/stores"],
    queryFn: () => apiGet("/api/sales/reports/od0005/stores"),
  });
  useEffect(() => {
    if (draft.storeId || !storesQuery.data?.length) return;
    const globalStore = storesQuery.data.find(
      (store) => String(store.store_id) === String(selectedStoreId ?? ""),
    );
    const centerStore = storesQuery.data.find((store) => store.store_code === "601");
    setDraft((current) => ({
      ...current,
      storeId: (globalStore ?? centerStore ?? storesQuery.data![0]).store_code,
    }));
  }, [draft.storeId, selectedStoreId, storesQuery.data]);

  const queryString = useMemo(
    () => submitted ? buildOd0005Params(submitted).toString() : "",
    [submitted],
  );
  const reportQuery = useQuery<Od0005Response>({
    queryKey: ["/api/sales/reports/od0005", queryString],
    queryFn: () => apiGet(`/api/sales/reports/od0005?${queryString}`),
    enabled: Boolean(queryString),
    staleTime: 0,
    placeholderData: (previousData) => previousData,
  });

  const submit = () => {
    if (!draft.storeId || !draft.startDate || !draft.endDate || draft.startDate > draft.endDate) return;
    setSubmitted({ ...draft });
    setExportError(null);
  };

  const switchSheet = (sheet: Od0005Sheet) => {
    setDraft((current) => ({ ...current, sheet }));
    setSubmitted((current) => current ? { ...current, sheet } : current);
  };

  const exportReport = async () => {
    if (!queryString || !submitted) return;
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/od0005/export?${queryString}`);
      objectUrl = URL.createObjectURL(await response.blob());
      anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `OD0005微商城品牌销售统计_${submitted.storeId}_${submitted.startDate}_${submitted.endDate}.xlsx`;
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
  const selectedSheet = submitted?.sheet ?? draft.sheet;
  const selectedSheetLabel = OD0005_SHEETS.find((sheet) => sheet.value === selectedSheet)?.label ?? "";
  const departmentRows = useMemo(() => departmentSummary(report?.rows ?? []), [report]);
  const currentDailyRows = useMemo(
    () => (report?.daily.rows ?? []).filter(hasCurrentDailySales),
    [report],
  );
  return (
    <div className="space-y-5 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">OD0005 微商城品牌销售统计</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          按含付款方式 0581 的交易统计，按门店、部门和柜组汇总销售、毛利及 YZQ／其他支付／NZD；金额单位：元。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
            <div className="space-y-2">
              <Label htmlFor="od0005-start">开始日期</Label>
              <Input id="od0005-start" type="date" value={draft.startDate} onChange={(event) => setDraft((current) => ({ ...current, startDate: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="od0005-end">结束日期</Label>
              <Input id="od0005-end" type="date" value={draft.endDate} onChange={(event) => setDraft((current) => ({ ...current, endDate: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="od0005-store">门店</Label>
              <Select value={draft.storeId} onValueChange={(storeId) => setDraft((current) => ({ ...current, storeId, departmentId: OD0005_ALL_DEPARTMENTS }))}>
                <SelectTrigger id="od0005-store"><SelectValue placeholder="请选择门店" /></SelectTrigger>
                <SelectContent>{storesQuery.data?.map((store) => <SelectItem key={store.store_code} value={store.store_code}>{store.store_code} {store.store_name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-3 whitespace-nowrap">
              <Button onClick={submit} disabled={!draft.storeId || draft.startDate > draft.endDate || reportQuery.isFetching}>
                {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}查询
              </Button>
              <Button variant="outline" onClick={exportReport} disabled={!report || exporting}>
                {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}导出 Excel（5个表页）
              </Button>
            </div>
          </div>
          {exportError && <span className="text-sm text-red-600">{exportError}</span>}
        </CardContent>
      </Card>

      {report && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <Tabs value={selectedSheet} onValueChange={(value) => switchSheet(value as Od0005Sheet)}>
                <TabsList className="mb-2 flex h-auto flex-wrap justify-start">
                  {OD0005_SHEETS.map((sheet) => <TabsTrigger key={sheet.value} value={sheet.value}>{sheet.label}</TabsTrigger>)}
                </TabsList>
              </Tabs>
              <CardTitle className="text-base">{selectedSheetLabel} · {report.store_code} {report.store_name} · {report.start_date} 至 {report.end_date}</CardTitle>
              <p className="text-xs text-muted-foreground">
                {selectedSheet === "daily_yoy" && <>同期：{report.daily.prior_start_date} 至 {report.daily.prior_end_date}；</>}
                {selectedSheet === "brand_yoy" && <>
                  前两年：{report.brand_yoy.periods.two_year_prior.start_date} 至 {report.brand_yoy.periods.two_year_prior.end_date}；
                  上年：{report.brand_yoy.periods.prior.start_date} 至 {report.brand_yoy.periods.prior.end_date}；
                </>}
                微商城付款方式：{report.payment_code}；{report.scope_description ?? "按本人业务范围查询"}
              </p>
            </CardHeader>
            <CardContent>
              {reportQuery.isFetching && (
                <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载{selectedSheetLabel}…
                </div>
              )}
              <div className={`${reportQuery.isFetching ? "hidden" : ""} max-h-[66vh] overflow-auto rounded-md border`}>
                {selectedSheet === "brand" && (
                  <table className="border-separate border-spacing-0 text-xs">
                    <thead><tr>{COLUMNS.map((column) => <th key={column.key} className={`sticky top-0 z-10 border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold ${column.width}`}>{column.label}</th>)}</tr></thead>
                    <tbody>
                      {report.rows.map((row) => (
                        <tr key={`${row.store_code}-${row.group_code}`} className="hover:bg-slate-50">
                          {COLUMNS.map((column) => <td key={column.key} className={`border-b border-r px-2 py-1.5 ${column.kind ? "text-right tabular-nums" : column.key === "group_name" || column.key === "department_code" ? "text-left" : "text-center"}`}>{displayValue(row, column)}</td>)}
                        </tr>
                      ))}
                      {!report.rows.length && <tr><td colSpan={COLUMNS.length} className="p-10 text-center text-muted-foreground">当前条件下暂无微商城销售数据</td></tr>}
                    </tbody>
                    {!!report.rows.length && <tfoot><tr className="bg-[#d9eaf7] font-semibold">{COLUMNS.map((column, index) => <td key={column.key} className={`border-r border-t px-2 py-2 ${column.kind ? "text-right tabular-nums" : "text-center"}`}>{index === 0 ? "合计" : index < 4 ? "" : formatOd0005Number(report.totals[column.key as keyof typeof report.totals], column.kind!)}</td>)}</tr></tfoot>}
                  </table>
                )}

                {selectedSheet === "department" && (
                  <table className="border-separate border-spacing-0 text-xs">
                    <thead><tr>{DEPARTMENT_COLUMNS.map((column) => <th key={column.key} className={`sticky top-0 z-10 border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold ${column.width}`}>{column.label}</th>)}</tr></thead>
                    <tbody>
                      {departmentRows.map((row) => (
                        <tr key={`${row.store_code}-${row.department_code}`} className="hover:bg-slate-50">
                          {DEPARTMENT_COLUMNS.map((column) => {
                            const value = column.key === "department_code"
                              ? displayDepartment(row)
                              : column.kind
                                ? formatOd0005Number(row[column.key] as number | null, column.kind)
                                : String(row[column.key] ?? "");
                            return <td key={column.key} className={`border-b border-r px-2 py-1.5 ${column.kind ? "text-right tabular-nums" : column.key === "department_code" ? "text-left" : "text-center"}`}>{value}</td>;
                          })}
                        </tr>
                      ))}
                      {!departmentRows.length && <tr><td colSpan={DEPARTMENT_COLUMNS.length} className="p-10 text-center text-muted-foreground">当前条件下暂无微商城销售数据</td></tr>}
                    </tbody>
                    {!!departmentRows.length && <tfoot><tr className="bg-[#d9eaf7] font-semibold">{DEPARTMENT_COLUMNS.map((column, index) => <td key={column.key} className={`border-r border-t px-2 py-2 ${column.kind ? "text-right tabular-nums" : "text-center"}`}>{index === 0 ? "合计" : index === 1 ? "" : formatOd0005Number(report.totals[column.key as keyof typeof report.totals], column.kind!)}</td>)}</tr></tfoot>}
                  </table>
                )}

                {selectedSheet === "daily" && (
                  <table className="border-separate border-spacing-0 text-xs">
                    <thead><tr>
                      {(["门店", "部门", "柜组", "柜组名称"] as const).map((label) => <th key={label} className="sticky top-0 z-10 min-w-[130px] border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold">{label}</th>)}
                      {report.daily.days.map((day) => <th key={day.date} className="sticky top-0 z-10 min-w-[120px] border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold">{day.date}</th>)}
                    </tr></thead>
                    <tbody>
                      {currentDailyRows.map((row) => <tr key={`${row.store_code}-${row.group_code}`} className="hover:bg-slate-50">
                        <td className="border-b border-r px-2 py-1.5 text-center">{row.store_code}</td>
                        <td className="min-w-[220px] border-b border-r px-2 py-1.5">{displayDepartment(row)}</td>
                        <td className="border-b border-r px-2 py-1.5 text-center">{row.group_code}</td>
                        <td className="min-w-[220px] border-b border-r px-2 py-1.5">{row.group_name}</td>
                        {row.daily.map((day) => <td key={day.date} className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(day.sales_current, "amount")}</td>)}
                      </tr>)}
                      {!currentDailyRows.length && <tr><td colSpan={4 + report.daily.days.length} className="p-10 text-center text-muted-foreground">当前条件下暂无微商城销售数据</td></tr>}
                    </tbody>
                    {!!currentDailyRows.length && <tfoot><tr className="bg-[#d9eaf7] font-semibold"><td className="border-r border-t px-2 py-2 text-center">合计</td><td colSpan={3} className="border-r border-t" />{report.daily.totals.map((day) => <td key={day.date} className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(day.sales_current, "amount")}</td>)}</tr></tfoot>}
                  </table>
                )}

                {selectedSheet === "daily_yoy" && (
                  <table className="border-separate border-spacing-0 text-xs">
                    <thead>
                      <tr>{(["门店", "部门", "柜组", "柜组名称"] as const).map((label) => <th key={label} rowSpan={2} className="sticky top-0 z-20 min-w-[130px] border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold">{label}</th>)}{report.daily.days.map((day) => <th key={day.date} colSpan={3} className="sticky top-0 z-20 border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold">{day.date}</th>)}</tr>
                      <tr>{report.daily.days.flatMap((day) => ["本期销售", "同期销售", "同比"].map((label) => <th key={`${day.date}-${label}`} className="sticky top-[33px] z-10 min-w-[110px] border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold">{label}</th>))}</tr>
                    </thead>
                    <tbody>
                      {report.daily.rows.map((row) => <tr key={`${row.store_code}-${row.group_code}`} className="hover:bg-slate-50">
                        <td className="border-b border-r px-2 py-1.5 text-center">{row.store_code}</td>
                        <td className="min-w-[220px] border-b border-r px-2 py-1.5">{displayDepartment(row)}</td>
                        <td className="border-b border-r px-2 py-1.5 text-center">{row.group_code}</td>
                        <td className="min-w-[220px] border-b border-r px-2 py-1.5">{row.group_name}</td>
                        {row.daily.flatMap((day) => [
                          <td key={`${day.date}-current`} className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(day.sales_current, "amount")}</td>,
                          <td key={`${day.date}-prior`} className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(day.sales_prior, "amount")}</td>,
                          <td key={`${day.date}-yoy`} className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(day.sales_yoy, "rate")}</td>,
                        ])}
                      </tr>)}
                      {!report.daily.rows.length && <tr><td colSpan={4 + report.daily.days.length * 3} className="p-10 text-center text-muted-foreground">本期及同期均暂无微商城销售数据</td></tr>}
                    </tbody>
                    {!!report.daily.rows.length && <tfoot><tr className="bg-[#d9eaf7] font-semibold"><td className="border-r border-t px-2 py-2 text-center">合计</td><td colSpan={3} className="border-r border-t" />{report.daily.totals.flatMap((day) => [
                      <td key={`${day.date}-current`} className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(day.sales_current, "amount")}</td>,
                      <td key={`${day.date}-prior`} className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(day.sales_prior, "amount")}</td>,
                      <td key={`${day.date}-yoy`} className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(day.sales_yoy, "rate")}</td>,
                    ])}</tr></tfoot>}
                  </table>
                )}

                {selectedSheet === "brand_yoy" && (
                  <table className="w-full border-separate border-spacing-0 text-xs">
                    <thead><tr>
                      {[
                        "部门",
                        "品牌",
                        shortYear(report.brand_yoy.periods.two_year_prior.year),
                        shortYear(report.brand_yoy.periods.prior.year),
                        shortYear(report.brand_yoy.periods.current.year),
                        "差额",
                        "同比",
                        "原因分析",
                        "缺失商品",
                      ].map((label, index) => <th key={label} className={`sticky top-0 z-10 border-b border-r bg-[#e2f0d9] px-2 py-2 text-center font-semibold ${index < 2 ? "min-w-[220px]" : index > 6 ? "min-w-[180px]" : "min-w-[120px]"}`}>{label}</th>)}
                    </tr></thead>
                    <tbody>
                      {report.brand_yoy.rows.map((row) => <tr key={`${row.store_code}-${row.group_code}`} className="hover:bg-slate-50">
                        <td className="border-b border-r px-2 py-1.5">{displayDepartment(row)}</td>
                        <td className="border-b border-r px-2 py-1.5">{row.group_name}</td>
                        <td className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(row.sales_two_year_prior, "amount")}</td>
                        <td className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(row.sales_prior, "amount")}</td>
                        <td className="border-b border-r px-2 py-1.5 text-right tabular-nums">{formatOd0005Number(row.sales_current, "amount")}</td>
                        <td className={`border-b border-r px-2 py-1.5 text-right tabular-nums ${row.difference < 0 ? "text-red-600" : ""}`}>{formatOd0005Number(row.difference, "amount")}</td>
                        <td className={`border-b border-r px-2 py-1.5 text-right tabular-nums ${(row.yoy ?? 0) < 0 ? "text-red-600" : ""}`}>{formatOd0005Number(row.yoy, "rate")}</td>
                        <td className="border-b border-r px-2 py-1.5" />
                        <td className="border-b border-r px-2 py-1.5" />
                      </tr>)}
                      {!report.brand_yoy.rows.length && <tr><td colSpan={9} className="p-10 text-center text-muted-foreground">本期及历史同期均暂无微商城品牌销售数据</td></tr>}
                    </tbody>
                    {!!report.brand_yoy.rows.length && <tfoot><tr className="bg-[#d9eaf7] font-semibold">
                      <td className="border-r border-t px-2 py-2 text-center">合计</td><td className="border-r border-t" />
                      <td className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(report.brand_yoy.totals.sales_two_year_prior, "amount")}</td>
                      <td className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(report.brand_yoy.totals.sales_prior, "amount")}</td>
                      <td className="border-r border-t px-2 py-2 text-right tabular-nums">{formatOd0005Number(report.brand_yoy.totals.sales_current, "amount")}</td>
                      <td className={`border-r border-t px-2 py-2 text-right tabular-nums ${report.brand_yoy.totals.difference < 0 ? "text-red-600" : ""}`}>{formatOd0005Number(report.brand_yoy.totals.difference, "amount")}</td>
                      <td className={`border-r border-t px-2 py-2 text-right tabular-nums ${(report.brand_yoy.totals.yoy ?? 0) < 0 ? "text-red-600" : ""}`}>{formatOd0005Number(report.brand_yoy.totals.yoy, "rate")}</td>
                      <td className="border-r border-t" /><td className="border-r border-t" />
                    </tr></tfoot>}
                  </table>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
      {reportQuery.isError && <Card><CardContent className="p-6 text-sm text-red-600">查询失败：{reportQuery.error instanceof Error ? reportQuery.error.message : "请稍后重试"}</CardContent></Card>}
    </div>
  );
}
