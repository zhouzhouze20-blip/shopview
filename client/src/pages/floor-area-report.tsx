import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useStore } from "@/contexts/StoreContext";
import { apiGet } from "@/lib/api";
import {
  floorAreaSummaryPath,
  floorDisplayCode,
  floorTotalArea,
  floorVacancyRate,
  formatFloorArea,
  formatFloorAreaCount,
  formatFloorVacancyRate,
  totalFloorAreaRows,
  type FloorAreaRow,
} from "@/lib/floor-area-report";

type StoreOption = {
  storeId: number;
  storeCode: string;
  storeName: string;
};

export default function FloorAreaReportPage() {
  const { stores, selectedStoreId, isLoading: storesLoading } = useStore();
  const [draftStoreCode, setDraftStoreCode] = useState("");
  const [submittedStoreCode, setSubmittedStoreCode] = useState("");

  const storeOptions = useMemo<StoreOption[]>(
    () =>
      stores
        .map((store) => ({
          storeId: store.storeId,
          storeCode: String(store.storeCode ?? store.storeId).trim(),
          storeName: String(store.storeName ?? store.storeCode ?? store.storeId).trim(),
        }))
        .filter((store) => store.storeCode),
    [stores],
  );

  useEffect(() => {
    if (!storeOptions.length || draftStoreCode) return;
    const initialStore =
      storeOptions.find((store) => store.storeId === selectedStoreId) ?? storeOptions[0];
    setDraftStoreCode(initialStore.storeCode);
    setSubmittedStoreCode(initialStore.storeCode);
  }, [draftStoreCode, selectedStoreId, storeOptions]);

  const query = useQuery({
    queryKey: ["floor-area-summary", submittedStoreCode],
    queryFn: () => apiGet<FloorAreaRow[]>(floorAreaSummaryPath(submittedStoreCode)),
    enabled: Boolean(submittedStoreCode),
  });

  const rows = useMemo(() => query.data ?? [], [query.data]);
  const totals = useMemo(() => totalFloorAreaRows(rows), [rows]);
  const missingAreaCount = totals.activeAreaMissingCount + totals.vacantAreaMissingCount;
  const selectedStoreName =
    storeOptions.find((store) => store.storeCode === submittedStoreCode)?.storeName ??
    submittedStoreCode;

  const handleQuery = () => {
    if (!draftStoreCode) return;
    if (draftStoreCode === submittedStoreCode) {
      void query.refetch();
      return;
    }
    setSubmittedStoreCode(draftStoreCode);
  };

  return (
    <div className="container mx-auto space-y-6 p-6" data-testid="floor-area-report-page">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">楼层在营及空置面积报表</h1>
        <p className="mt-1 text-sm text-slate-500">
          按门店汇总每个楼层的在营柜位、空置柜位及人工确认面积
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="floor-area-store">门店</Label>
              <Select value={draftStoreCode} onValueChange={setDraftStoreCode}>
                <SelectTrigger id="floor-area-store" className="w-[260px]">
                  <SelectValue placeholder={storesLoading ? "正在加载门店…" : "请选择门店"} />
                </SelectTrigger>
                <SelectContent>
                  {storeOptions.map((store) => (
                    <SelectItem key={store.storeId} value={store.storeCode}>
                      {store.storeName}（{store.storeCode}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleQuery} disabled={!draftStoreCode || query.isFetching}>
              <Search className="mr-2 h-4 w-4" />
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {submittedStoreCode && rows.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">在营柜位数量</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold text-emerald-700">{formatFloorAreaCount(totals.activeUnitCount)}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">在营面积（m²）</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold text-emerald-700">{formatFloorArea(totals.activeAreaTotal)}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">空置柜位数量</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold text-amber-700">{formatFloorAreaCount(totals.vacantUnitCount)}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500">空置面积（m²）</CardTitle></CardHeader>
            <CardContent className="text-2xl font-semibold text-amber-700">{formatFloorArea(totals.vacantAreaTotal)}</CardContent>
          </Card>
        </div>
      )}

      {(missingAreaCount > 0 || totals.otherUnitCount > 0) && (
        <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            {missingAreaCount > 0 && (
              <p>
                当前有 {formatFloorAreaCount(missingAreaCount)} 个在营或空置柜位未维护面积，面积合计不包含这些柜位。
              </p>
            )}
            {totals.otherUnitCount > 0 && (
              <p>
                另有 {formatFloorAreaCount(totals.otherUnitCount)} 个装修中或失效柜位，未计入在营和空置指标。
              </p>
            )}
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {submittedStoreCode ? `${selectedStoreName} · 楼层明细` : "楼层明细"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">序号</TableHead>
                  <TableHead>楼层</TableHead>
                  <TableHead>楼层名称</TableHead>
                  <TableHead className="text-right">在营柜位数量</TableHead>
                  <TableHead className="text-right">在营面积（m²）</TableHead>
                  <TableHead className="text-right">空置柜位数量</TableHead>
                  <TableHead className="text-right">空置面积（m²）</TableHead>
                  <TableHead className="text-right">总面积（m²）</TableHead>
                  <TableHead className="text-right">空置率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.isLoading || storesLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-slate-500">正在加载报表…</TableCell>
                  </TableRow>
                ) : query.isError ? (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-red-600">报表加载失败，请稍后重试</TableCell>
                  </TableRow>
                ) : !submittedStoreCode ? (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-slate-500">请选择门店后查询</TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="py-10 text-center text-slate-500">当前门店暂无楼层数据</TableCell>
                  </TableRow>
                ) : (
                  <>
                    {rows.map((row, index) => {
                      const totalArea = floorTotalArea(row);
                      const vacancyRate = floorVacancyRate(row.vacant_area_total, totalArea);

                      return (
                        <TableRow key={row.floor_id}>
                          <TableCell>{index + 1}</TableCell>
                          <TableCell className="font-medium">{floorDisplayCode(row)}</TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell className="text-right">{formatFloorAreaCount(row.active_unit_count)}</TableCell>
                          <TableCell className="text-right">{formatFloorArea(row.active_area_total)}</TableCell>
                          <TableCell className="text-right">{formatFloorAreaCount(row.vacant_unit_count)}</TableCell>
                          <TableCell className="text-right">{formatFloorArea(row.vacant_area_total)}</TableCell>
                          <TableCell className="text-right">{formatFloorArea(totalArea)}</TableCell>
                          <TableCell className="text-right">{formatFloorVacancyRate(vacancyRate)}</TableCell>
                        </TableRow>
                      );
                    })}
                    <TableRow className="bg-slate-50 font-semibold">
                      <TableCell colSpan={3}>合计</TableCell>
                      <TableCell className="text-right">{formatFloorAreaCount(totals.activeUnitCount)}</TableCell>
                      <TableCell className="text-right">{formatFloorArea(totals.activeAreaTotal)}</TableCell>
                      <TableCell className="text-right">{formatFloorAreaCount(totals.vacantUnitCount)}</TableCell>
                      <TableCell className="text-right">{formatFloorArea(totals.vacantAreaTotal)}</TableCell>
                      <TableCell className="text-right">{formatFloorArea(totals.totalArea)}</TableCell>
                      <TableCell className="text-right">{formatFloorVacancyRate(floorVacancyRate(totals.vacantAreaTotal, totals.totalArea))}</TableCell>
                    </TableRow>
                  </>
                )}
              </TableBody>
            </Table>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            口径：在营 = ACTIVE，空置 = VACANT；面积取经营单元“人工确认面积”；总面积 = 在营面积 + 空置面积，空置率 = 空置面积 ÷ 总面积。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
