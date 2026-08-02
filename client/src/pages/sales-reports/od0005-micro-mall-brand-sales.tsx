import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  buildOd0005Params,
  formatOd0005Number,
  OD0005_ALL_DEPARTMENTS,
  type Od0005Response,
  type Od0005Row,
} from "@/lib/od0005-micro-mall";
import { contentDispositionFilename, scheduleObjectUrlRevoke } from "@/lib/od0002-report";


type StoreOption = { store_id: string | number; store_code: string; store_name: string };
type DepartmentOption = { department_code: string; department_name: string; label: string };
type Filters = { startDate: string; endDate: string; storeId: string; departmentId: string };

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

export default function Od0005MicroMallBrandSalesPage() {
  const { selectedStoreId } = useStore();
  const defaultDate = useMemo(() => yesterday(), []);
  const [draft, setDraft] = useState<Filters>({
    startDate: defaultDate,
    endDate: defaultDate,
    storeId: "",
    departmentId: OD0005_ALL_DEPARTMENTS,
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

  const departmentsQuery = useQuery<DepartmentOption[]>({
    queryKey: ["/api/sales/reports/od0005/departments", draft.storeId],
    queryFn: () => apiGet(
      `/api/sales/reports/od0005/departments?store_id=${encodeURIComponent(draft.storeId)}`,
    ),
    enabled: Boolean(draft.storeId),
  });
  const queryString = useMemo(
    () => submitted ? buildOd0005Params(submitted).toString() : "",
    [submitted],
  );
  const reportQuery = useQuery<Od0005Response>({
    queryKey: ["/api/sales/reports/od0005", queryString],
    queryFn: () => apiGet(`/api/sales/reports/od0005?${queryString}`),
    enabled: Boolean(queryString),
    staleTime: 0,
  });

  const submit = () => {
    if (!draft.storeId || !draft.startDate || !draft.endDate || draft.startDate > draft.endDate) return;
    setSubmitted({ ...draft });
    setExportError(null);
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
  return (
    <div className="space-y-5 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">OD0005 微商城品牌销售统计</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          按微商城专用收银员识别交易，按门店、部门和柜组汇总销售、毛利及 YZQ／其他支付／NZD；金额单位：元。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
            <div className="space-y-2">
              <Label htmlFor="od0005-department">部门</Label>
              <Select value={draft.departmentId} onValueChange={(departmentId) => setDraft((current) => ({ ...current, departmentId }))} disabled={!draft.storeId}>
                <SelectTrigger id="od0005-department"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={OD0005_ALL_DEPARTMENTS}>全部部门</SelectItem>
                  {departmentsQuery.data?.map((department) => <SelectItem key={department.department_code} value={department.department_code}>{department.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={submit} disabled={!draft.storeId || draft.startDate > draft.endDate || reportQuery.isFetching}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}查询
            </Button>
            <Button variant="outline" onClick={exportReport} disabled={!report || exporting}>
              {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}导出 Excel
            </Button>
            {exportError && <span className="text-sm text-red-600">{exportError}</span>}
          </div>
        </CardContent>
      </Card>

      {report && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["柜组数", String(report.rows.length)],
              ["销售收入", `¥${formatOd0005Number(report.totals.sales_revenue, "amount")}`],
              ["毛利", `¥${formatOd0005Number(report.totals.gross_profit, "amount")}`],
              ["毛利率", formatOd0005Number(report.totals.gross_margin, "rate")],
            ].map(([label, value]) => (
              <Card key={label}><CardContent className="p-4"><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 text-xl font-semibold tabular-nums">{value}</div></CardContent></Card>
            ))}
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{report.store_code} {report.store_name} · {report.start_date} 至 {report.end_date}</CardTitle>
              <p className="text-xs text-muted-foreground">微商城收银员：{report.cashier_code}；{report.scope_description ?? "按本人业务范围查询"}</p>
            </CardHeader>
            <CardContent>
              <div className="max-h-[66vh] overflow-auto rounded-md border">
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
              </div>
            </CardContent>
          </Card>
        </>
      )}
      {reportQuery.isError && <Card><CardContent className="p-6 text-sm text-red-600">查询失败：{reportQuery.error instanceof Error ? reportQuery.error.message : "请稍后重试"}</CardContent></Card>}
    </div>
  );
}
