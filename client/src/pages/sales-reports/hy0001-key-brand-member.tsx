import { useEffect, useMemo, useState } from "react";
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
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useStore } from "@/contexts/StoreContext";
import { apiGet, apiRequest } from "@/lib/api";
import {
  buildHy0001Params,
  contentDispositionFilename,
  defaultHy0001DateRange,
  formatHy0001Count,
  formatHy0001Money,
  formatHy0001Yoy,
  HY0001_ALL_DEPARTMENTS,
  hy0001Level,
  hy0001YoyClass,
  type Hy0001Department,
  type Hy0001Response,
  type Hy0001Store,
} from "@/lib/hy0001-report";


type Submitted = {
  startDate: string;
  endDate: string;
  storeCode: string;
  departmentCode: string;
  queryString: string;
};


export default function Hy0001KeyBrandMemberPage() {
  const { selectedStoreId } = useStore();
  const initialDates = useMemo(() => defaultHy0001DateRange(), []);
  const [startDate, setStartDate] = useState(initialDates.start);
  const [endDate, setEndDate] = useState(initialDates.end);
  const [storeCode, setStoreCode] = useState("");
  const [departmentCode, setDepartmentCode] = useState(HY0001_ALL_DEPARTMENTS);
  const [submitted, setSubmitted] = useState<Submitted | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [storeTouched, setStoreTouched] = useState(false);

  const storesQuery = useQuery<Hy0001Store[]>({
    queryKey: ["/api/sales/reports/hy0001/stores"],
    queryFn: () => apiGet("/api/sales/reports/hy0001/stores"),
  });

  useEffect(() => {
    if (storeTouched || !storesQuery.data?.length) return;
    const globalStore = storesQuery.data.find(
      (store) => String(store.store_id) === String(selectedStoreId ?? ""),
    );
    setStoreCode(globalStore?.store_code ?? storesQuery.data[0].store_code);
  }, [selectedStoreId, storeTouched, storesQuery.data]);

  const departmentsQuery = useQuery<Hy0001Department[]>({
    queryKey: ["/api/sales/reports/hy0001/departments", storeCode],
    queryFn: () => apiGet(
      `/api/sales/reports/hy0001/departments?store_id=${encodeURIComponent(storeCode)}`,
    ),
    enabled: Boolean(storeCode),
  });

  const reportQuery = useQuery<Hy0001Response>({
    queryKey: ["/api/sales/reports/hy0001", submitted?.queryString ?? ""],
    queryFn: () => apiGet(`/api/sales/reports/hy0001?${submitted?.queryString ?? ""}`),
    enabled: Boolean(submitted),
    staleTime: 0,
  });

  const selectedStore = useMemo(
    () => storesQuery.data?.find((store) => store.store_code === storeCode),
    [storeCode, storesQuery.data],
  );

  const submit = () => {
    if (!startDate || !endDate || startDate > endDate || !storeCode) return;
    const queryString = buildHy0001Params(
      startDate,
      endDate,
      storeCode,
      departmentCode,
    ).toString();
    setSubmitted({ startDate, endDate, storeCode, departmentCode, queryString });
    setExportError(null);
  };

  const exportReport = async () => {
    if (!submitted) return;
    setExporting(true);
    setExportError(null);
    let objectUrl: string | null = null;
    let anchor: HTMLAnchorElement | null = null;
    try {
      const response = await apiRequest(`/api/sales/reports/hy0001/export?${submitted.queryString}`);
      const blob = await response.blob();
      objectUrl = URL.createObjectURL(blob);
      anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = contentDispositionFilename(response.headers.get("Content-Disposition"))
        ?? `HY0001重点品牌会员消费情况_${submitted.storeCode}_${submitted.startDate}_${submitted.endDate}.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "导出失败，请稍后重试");
    } finally {
      anchor?.remove();
      if (objectUrl) {
        const urlToRevoke = objectUrl;
        window.setTimeout(() => URL.revokeObjectURL(urlToRevoke), 30_000);
      }
      setExporting(false);
    }
  };

  const report = submitted ? reportQuery.data : undefined;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">HY0001 重点品牌会员消费情况</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          按重点品牌和会员等级对比所选期间与上年对应日期；销售金额单位：元。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="hy0001-start-date">开始日期</Label>
              <Input
                id="hy0001-start-date"
                type="date"
                value={startDate}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hy0001-end-date">结束日期</Label>
              <Input
                id="hy0001-end-date"
                type="date"
                value={endDate}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hy0001-store">门店</Label>
              <Select
                value={storeCode}
                onValueChange={(value) => {
                  setStoreTouched(true);
                  setStoreCode(value);
                  setDepartmentCode(HY0001_ALL_DEPARTMENTS);
                }}
                disabled={storesQuery.isLoading}
              >
                <SelectTrigger id="hy0001-store"><SelectValue placeholder="请选择门店" /></SelectTrigger>
                <SelectContent>
                  {(storesQuery.data ?? []).map((store) => (
                    <SelectItem key={store.store_code} value={store.store_code}>
                      {store.store_name}（{store.store_code}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="hy0001-department">部门</Label>
              <Select
                value={departmentCode}
                onValueChange={setDepartmentCode}
                disabled={!storeCode || departmentsQuery.isLoading}
              >
                <SelectTrigger id="hy0001-department"><SelectValue placeholder="全部部门" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={HY0001_ALL_DEPARTMENTS}>全部部门</SelectItem>
                  {(departmentsQuery.data ?? []).map((department) => (
                    <SelectItem key={department.department_code} value={department.department_code}>
                      {department.department_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              onClick={submit}
              disabled={!startDate || !endDate || startDate > endDate || !storeCode || reportQuery.isFetching}
            >
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={exportReport} disabled={!report || exporting || reportQuery.isFetching}>
              {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {exporting ? "导出中…" : "导出 Excel"}
            </Button>
          </div>
          {startDate > endDate && (
            <p role="alert" className="text-sm text-red-600">结束日期不能早于开始日期</p>
          )}
          {storesQuery.error && <p role="alert" className="text-sm text-red-600">门店选项加载失败</p>}
          {departmentsQuery.error && <p role="alert" className="text-sm text-red-600">部门选项加载失败</p>}
          {exportError && <p role="alert" className="text-sm text-red-600">{exportError}</p>}
        </CardContent>
      </Card>

      {report && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="pt-5"><div className="text-sm text-muted-foreground">重点品牌</div><div className="mt-1 text-2xl font-semibold">{report.quality.key_brand_count}</div></CardContent></Card>
          <Card><CardContent className="pt-5"><div className="text-sm text-muted-foreground">未维护品类主管</div><div className="mt-1 text-2xl font-semibold text-amber-700">{report.quality.unassigned_manager_count}</div></CardContent></Card>
          <Card><CardContent className="pt-5"><div className="text-sm text-muted-foreground">本期无会员销售品牌</div><div className="mt-1 text-2xl font-semibold">{report.quality.no_current_member_sales_count}</div></CardContent></Card>
        </div>
      )}

      <Card>
        <CardContent className="pt-6">
          {!submitted ? (
            <div className="py-16 text-center text-sm text-muted-foreground">请选择门店和日期范围后查询</div>
          ) : reportQuery.isFetching ? (
            <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />加载报表…</div>
          ) : reportQuery.error ? (
            <div role="alert" className="py-16 text-center text-sm text-red-600">报表加载失败，请检查权限或稍后重试</div>
          ) : !report?.rows.length ? (
            <div className="py-16 text-center text-sm text-muted-foreground">当前范围没有已标记的重点品牌</div>
          ) : (
            <div className="max-h-[68vh] overflow-auto rounded-md border">
              <Table className="min-w-[2600px] text-xs">
                <TableHeader className="sticky top-0 z-20 bg-white">
                  <TableRow>
                    <TableHead rowSpan={3} className="sticky left-0 z-30 min-w-28 bg-white align-middle">品类主管</TableHead>
                    <TableHead rowSpan={3} className="sticky left-28 z-30 min-w-56 bg-white align-middle">重点品牌</TableHead>
                    <TableHead colSpan={12} className="text-center text-red-700">销售（元）</TableHead>
                    <TableHead colSpan={12} className="text-center text-emerald-700">消费人数</TableHead>
                  </TableRow>
                  <TableRow>
                    {report.levels.concat(report.levels).map((level, index) => (
                      <TableHead key={`${index}-${level.level_code}`} colSpan={3} className="text-center">{level.level_label}</TableHead>
                    ))}
                  </TableRow>
                  <TableRow>
                    {Array.from({ length: 8 }).flatMap((_, index) => [
                      <TableHead key={`${index}-current`} className="text-right">本期</TableHead>,
                      <TableHead key={`${index}-prior`} className="text-right">同期</TableHead>,
                      <TableHead key={`${index}-yoy`} className="text-right">同比</TableHead>,
                    ])}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.rows.map((row) => (
                    <TableRow key={`${row.store_code}-${row.group_code}`}>
                      <TableCell className="sticky left-0 z-10 bg-white font-medium">{row.manager_name}</TableCell>
                      <TableCell className="sticky left-28 z-10 bg-white">
                        <div className="font-medium">{row.group_name}</div>
                        <div className="text-[11px] text-muted-foreground">{row.group_code} · {row.department_name || "未匹配部门"}</div>
                      </TableCell>
                      {report.levels.map((definition) => {
                        const level = hy0001Level(row, definition.level_code);
                        return [
                          <TableCell key={`${definition.level_code}-cs`} className="text-right tabular-nums">{formatHy0001Money(level?.current_sales)}</TableCell>,
                          <TableCell key={`${definition.level_code}-ps`} className="text-right tabular-nums text-slate-500">{formatHy0001Money(level?.prior_sales)}</TableCell>,
                          <TableCell key={`${definition.level_code}-sy`} className={`text-right tabular-nums ${hy0001YoyClass(level?.sales_yoy)}`}>{formatHy0001Yoy(level?.sales_yoy)}</TableCell>,
                        ];
                      })}
                      {report.levels.map((definition) => {
                        const level = hy0001Level(row, definition.level_code);
                        return [
                          <TableCell key={`${definition.level_code}-cb`} className="text-right tabular-nums">{formatHy0001Count(level?.current_buyers)}</TableCell>,
                          <TableCell key={`${definition.level_code}-pb`} className="text-right tabular-nums text-slate-500">{formatHy0001Count(level?.prior_buyers)}</TableCell>,
                          <TableCell key={`${definition.level_code}-by`} className={`text-right tabular-nums ${hy0001YoyClass(level?.buyer_yoy)}`}>{formatHy0001Yoy(level?.buyer_yoy)}</TableCell>,
                        ];
                      })}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {report?.manager_summary.length ? (
        <Card>
          <CardHeader><CardTitle className="text-base">品类主管黑金、黑钻会员人数及销售汇总</CardTitle></CardHeader>
          <CardContent>
            <div className="mb-3 text-xs text-muted-foreground">{selectedStore?.store_name ?? submitted?.storeCode} · 与样表底部主管汇总口径一致</div>
            <Table>
              <TableHeader><TableRow><TableHead>品类主管</TableHead><TableHead className="text-right">重点品牌数</TableHead><TableHead className="text-right">本期人数</TableHead><TableHead className="text-right">同期人数</TableHead><TableHead className="text-right">人数同比</TableHead><TableHead className="text-right">本期销售</TableHead><TableHead className="text-right">同期销售</TableHead><TableHead className="text-right">销售同比</TableHead></TableRow></TableHeader>
              <TableBody>
                {report.manager_summary.map((row) => (
                  <TableRow key={row.manager_name}>
                    <TableCell className="font-medium">{row.manager_name}</TableCell>
                    <TableCell className="text-right">{formatHy0001Count(row.key_brand_count)}</TableCell>
                    <TableCell className="text-right">{formatHy0001Count(row.current_premium_buyers)}</TableCell>
                    <TableCell className="text-right text-slate-500">{formatHy0001Count(row.prior_premium_buyers)}</TableCell>
                    <TableCell className={`text-right ${hy0001YoyClass(row.premium_buyer_yoy)}`}>{formatHy0001Yoy(row.premium_buyer_yoy)}</TableCell>
                    <TableCell className="text-right">{formatHy0001Money(row.current_premium_sales)}</TableCell>
                    <TableCell className="text-right text-slate-500">{formatHy0001Money(row.prior_premium_sales)}</TableCell>
                    <TableCell className={`text-right ${hy0001YoyClass(row.premium_sales_yoy)}`}>{formatHy0001Yoy(row.premium_sales_yoy)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
