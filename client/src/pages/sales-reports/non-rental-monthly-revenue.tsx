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
import {
  NON_RENTAL_ALL_DEPARTMENTS,
  NON_RENTAL_MONTHLY_METRICS,
  buildNonRentalMonthlyRevenueParams,
  financialMonthPeriodLabel,
  formatNonRentalMetric,
  rowTone,
  type NonRentalMonthlyRevenueResponse,
  type NonRentalMonthlyRevenueRow,
} from "@/lib/non-rental-monthly-revenue";
import {
  contentDispositionFilename,
  scheduleObjectUrlRevoke,
} from "@/lib/od0002-report";
import { cn } from "@/lib/utils";


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
  financialYear: number;
  storeId: string;
  departmentId: string;
};

const REGULAR_DIMENSIONS = [
  { key: "big_category", label: "大类", width: 110 },
  { key: "department_name", label: "部门", width: 140 },
  { key: "floor_name", label: "楼层", width: 80 },
  { key: "area_name", label: "区域名", width: 120 },
  { key: "category_name", label: "类别名", width: 140 },
  { key: "group_name", label: "品牌厅", width: 220 },
] as const;

const SPECIAL_DIMENSIONS = [
  ...REGULAR_DIMENSIONS.slice(0, 5),
  { key: "brand_name", label: "品牌", width: 200 },
  REGULAR_DIMENSIONS[5],
] as const;

function currentFinancialYear(): number {
  return new Date().getFullYear();
}

function summaryValue(
  report: NonRentalMonthlyRevenueResponse | undefined,
  key: "tax_included_sales" | "gross_profit" | "fee" | "contribution" | "concession_loss",
): string {
  if (!report) return "—";
  return formatNonRentalMetric(report.grand_total.annual, key, "amount");
}

function RevenueTable({
  report,
  rows,
  section,
}: {
  report: NonRentalMonthlyRevenueResponse;
  rows: NonRentalMonthlyRevenueRow[];
  section: "regular" | "special";
}) {
  const blocks = [
    { key: "annual", label: `${report.financial_year}年小计`, period: report.dates },
    ...report.periods.map((period) => ({
      key: String(period.month),
      label: period.label,
      period: { start_date: period.start_date, end_date: period.end_date },
    })),
  ];
  const dimensions = section === "special" ? SPECIAL_DIMENSIONS : REGULAR_DIMENSIONS;
  const stickyOffsets = dimensions.map((_, index) =>
    dimensions.slice(0, index).reduce((sum, item) => sum + item.width, 0),
  );

  if (!rows.length) {
    return (
      <div className="flex min-h-48 items-center justify-center text-sm text-muted-foreground">
        {section === "special" ? "本年度暂无特卖数据" : "本年度暂无普通品牌数据"}
      </div>
    );
  }

  return (
    <div className="max-h-[68vh] overflow-auto rounded-md border bg-white">
      <table className="border-separate border-spacing-0 text-xs">
        <thead>
          <tr>
            {dimensions.map((dimension, index) => (
              <th
                key={dimension.key}
                rowSpan={2}
                className="sticky top-0 z-40 border-b border-r border-slate-500 bg-[#c6e0b4] px-2 py-2 text-center font-semibold text-slate-900"
                style={{
                  left: stickyOffsets[index],
                  minWidth: dimension.width,
                  width: dimension.width,
                }}
              >
                {dimension.label}
              </th>
            ))}
            {blocks.map((block) => (
              <th
                key={block.key}
                colSpan={NON_RENTAL_MONTHLY_METRICS.length}
                className="sticky top-0 z-30 h-10 border-b border-r border-slate-500 bg-[#c6e0b4] px-2 text-center font-semibold text-slate-900"
                title={`${block.period.start_date} 至 ${block.period.end_date}`}
              >
                {block.label}
              </th>
            ))}
          </tr>
          <tr>
            {blocks.flatMap((block) =>
              NON_RENTAL_MONTHLY_METRICS.map((metric) => (
                <th
                  key={`${block.key}-${metric.key}`}
                  className={cn(
                    "sticky top-10 z-30 min-w-[94px] border-b border-r border-slate-500 bg-[#c6e0b4] px-2 py-2 text-center font-semibold text-slate-900",
                    metric.key === "contribution" && "bg-[#9dc3e6]",
                  )}
                >
                  {metric.label}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const total = row.row_type !== "brand";
            return (
              <tr key={row.row_key} className={rowTone(row.row_type)}>
                {dimensions.map((dimension, index) => (
                  <td
                    key={dimension.key}
                    className={cn(
                      "sticky z-20 border-b border-r border-slate-300 px-2 py-1.5 text-center",
                      total ? "bg-[#b4c6e7]" : "bg-white",
                      (dimension.key === "group_name" || dimension.key === "brand_name")
                        && !total
                        && "text-left",
                    )}
                    style={{
                      left: stickyOffsets[index],
                      minWidth: dimension.width,
                      width: dimension.width,
                    }}
                  >
                    {row[dimension.key] || (total && dimension.key === "group_name" ? row.group_name : "")}
                  </td>
                ))}
                {blocks.flatMap((block) => {
                  const metrics = block.key === "annual"
                    ? row.annual
                    : row.months[block.key];
                  return NON_RENTAL_MONTHLY_METRICS.map((metric) => {
                    const raw = metrics?.[metric.key];
                    const negativeLoss = (
                      metric.key === "concession_loss"
                      || metric.key === "concession_loss_rate"
                    ) && typeof raw === "number" && raw < 0;
                    return (
                      <td
                        key={`${block.key}-${metric.key}`}
                        className={cn(
                          "border-b border-r border-slate-300 px-2 py-1.5 text-right tabular-nums",
                          total && "bg-[#b4c6e7] font-semibold",
                          metric.key === "contribution" && !total && "bg-[#dbeaf7]",
                          negativeLoss && "text-red-600",
                        )}
                      >
                        {metrics ? formatNonRentalMetric(metrics, metric.key, metric.kind) : "—"}
                      </td>
                    );
                  });
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function NonRentalMonthlyRevenuePage() {
  const { selectedStoreId } = useStore();
  const [draft, setDraft] = useState<Filters>({
    financialYear: currentFinancialYear(),
    storeId: "",
    departmentId: NON_RENTAL_ALL_DEPARTMENTS,
  });
  const [submitted, setSubmitted] = useState<Filters | null>(null);
  const [activeSection, setActiveSection] = useState<"regular" | "special">("regular");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const storesQuery = useQuery<AuthorizedStore[]>({
    queryKey: ["/api/sales/reports/non-rental-monthly-revenue/stores"],
    queryFn: () => apiGet("/api/sales/reports/non-rental-monthly-revenue/stores"),
  });
  const departmentSuffix = draft.storeId
    ? `?store_id=${encodeURIComponent(draft.storeId)}`
    : "";
  const departmentsQuery = useQuery<AuthorizedDepartment[]>({
    queryKey: ["/api/sales/reports/non-rental-monthly-revenue/departments", draft.storeId],
    queryFn: () => apiGet(`/api/sales/reports/non-rental-monthly-revenue/departments${departmentSuffix}`),
    enabled: Boolean(draft.storeId),
  });

  useEffect(() => {
    if (draft.storeId || !storesQuery.data?.length) return;
    const globalStore = storesQuery.data.find(
      (store) => String(store.store_id) === String(selectedStoreId),
    );
    const buildingStore = storesQuery.data.find((store) => store.store_code === "602");
    const firstStore = globalStore ?? buildingStore ?? storesQuery.data[0];
    setDraft((current) => ({ ...current, storeId: firstStore.store_code }));
  }, [draft.storeId, selectedStoreId, storesQuery.data]);

  const queryString = useMemo(
    () => submitted
      ? buildNonRentalMonthlyRevenueParams(submitted).toString()
      : "",
    [submitted],
  );
  const reportQuery = useQuery<NonRentalMonthlyRevenueResponse>({
    queryKey: ["/api/sales/reports/non-rental-monthly-revenue", queryString],
    queryFn: () => apiGet(`/api/sales/reports/non-rental-monthly-revenue?${queryString}`),
    enabled: Boolean(submitted && queryString),
  });

  const submit = () => {
    if (!draft.storeId) return;
    setSubmitted({ ...draft });
    setExportError(null);
  };

  const exportReport = async () => {
    if (!submitted || !queryString) return;
    setExporting(true);
    setExportError(null);
    let url: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(
        `/api/sales/reports/non-rental-monthly-revenue/export?${queryString}`,
      );
      if (!response.ok) throw new Error(`导出失败（${response.status}）`);
      const blob = await response.blob();
      const storeName = storesQuery.data?.find(
        (store) => store.store_code === submitted.storeId,
      )?.store_name ?? submitted.storeId;
      const filename = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `${storeName}非租赁品牌月度收益_${submitted.financialYear}年.xlsx`;
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

  const report = reportQuery.data;
  const activeRows = activeSection === "regular"
    ? report?.regular_rows ?? []
    : report?.special_rows ?? [];

  return (
    <div className="space-y-5 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">非租赁品牌月度收益表</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          金额单位：万元；财务年为1月1日至12月31日，12月财务月为11月29日至12月31日。收费按费用发生月顺延一个报表月；第一版不含买单额，贡献值＝毛利额＋收费；特卖单独按品牌展示。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label>财务年度</Label>
              <Select
                value={String(draft.financialYear)}
                onValueChange={(value) => setDraft((current) => ({
                  ...current,
                  financialYear: Number(value),
                }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 6 }, (_, index) => currentFinancialYear() - index).map((year) => (
                    <SelectItem key={year} value={String(year)}>{year}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>门店</Label>
              <Select
                value={draft.storeId}
                onValueChange={(storeId) => setDraft((current) => ({
                  ...current,
                  storeId,
                  departmentId: NON_RENTAL_ALL_DEPARTMENTS,
                }))}
                disabled={storesQuery.isLoading}
              >
                <SelectTrigger><SelectValue placeholder="请选择门店" /></SelectTrigger>
                <SelectContent>
                  {(storesQuery.data ?? []).map((store) => (
                    <SelectItem key={store.store_code} value={store.store_code}>
                      {store.store_code} · {store.store_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>部门</Label>
              <Select
                value={draft.departmentId}
                onValueChange={(departmentId) => setDraft((current) => ({
                  ...current,
                  departmentId,
                }))}
                disabled={!draft.storeId || departmentsQuery.isLoading}
              >
                <SelectTrigger><SelectValue placeholder="全部部门" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NON_RENTAL_ALL_DEPARTMENTS}>全部部门</SelectItem>
                  {(departmentsQuery.data ?? []).map((department) => (
                    <SelectItem key={department.department_code} value={department.department_code}>
                      {department.department_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={submit} disabled={!draft.storeId || reportQuery.isFetching}>
                {reportQuery.isFetching
                  ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  : <Search className="mr-2 h-4 w-4" />}
                查询
              </Button>
              <Button
                variant="outline"
                onClick={exportReport}
                disabled={!report || exporting}
              >
                {exporting
                  ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  : <Download className="mr-2 h-4 w-4" />}
                导出Excel
              </Button>
            </div>
          </div>
          {submitted ? (
            <div className="mt-3 text-xs text-muted-foreground">
              年度期间：{submitted.financialYear}-01-01 至 {submitted.financialYear}-12-31；
              1月：{financialMonthPeriodLabel(submitted.financialYear, 1)}；
              12月：{financialMonthPeriodLabel(submitted.financialYear, 12)}
            </div>
          ) : null}
          {exportError ? <div className="mt-3 text-sm text-red-600">{exportError}</div> : null}
        </CardContent>
      </Card>

      {reportQuery.isLoading ? (
        <div className="flex min-h-60 items-center justify-center text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载年度报表…
        </div>
      ) : reportQuery.error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          报表加载失败，请检查权限或稍后重试。
        </div>
      ) : report ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ["含税销售", summaryValue(report, "tax_included_sales")],
              ["毛利额", summaryValue(report, "gross_profit")],
              ["收费", summaryValue(report, "fee")],
              ["贡献值", summaryValue(report, "contribution")],
              ["让利损失额", summaryValue(report, "concession_loss")],
            ].map(([label, value]) => (
              <Card key={label}>
                <CardContent className="p-4">
                  <div className="text-xs text-muted-foreground">{label}（万元）</div>
                  <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <CardTitle className="text-base">年度明细</CardTitle>
                <div className="text-xs text-muted-foreground">
                  普通品牌 {report.quality.regular_brand_count} 个 · 特卖品牌 {report.quality.special_brand_count} 个
                  {report.quality.latest_sales_date ? ` · 销售数据至 ${report.quality.latest_sales_date}` : ""}
                </div>
              </div>
              <Tabs value={activeSection} onValueChange={(value) => setActiveSection(value as "regular" | "special")}>
                <TabsList>
                  <TabsTrigger value="regular">普通品牌</TabsTrigger>
                  <TabsTrigger value="special">特卖（单独）</TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent>
              <RevenueTable report={report} rows={activeRows} section={activeSection} />
              {report.quality.missing_area_category_count > 0 ? (
                <div className="mt-3 text-xs text-amber-700">
                  有 {report.quality.missing_area_category_count} 个品牌缺少区域或类别映射，请在主数据中补充。
                </div>
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="flex min-h-56 items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
          请选择年度和门店后查询。
        </div>
      )}
    </div>
  );
}
