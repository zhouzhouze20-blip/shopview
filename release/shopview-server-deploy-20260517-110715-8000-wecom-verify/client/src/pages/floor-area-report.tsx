import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface FloorAreaRow {
  floor_id: number;
  store_code?: string | null;
  store_name?: string | null;
  building_code: string;
  floor_code: string;
  name: string;
  unit_count: number;
  manual_area_total: number;
  building_area: number;
}

const fmt = (n: number) => Number(n || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export default function FloorAreaReportPage() {
  const query = useQuery({
    queryKey: ["floor-area-summary"],
    queryFn: () => apiGet<FloorAreaRow[]>("/api/reports/floor-area-summary"),
  });

  const rows = useMemo(() => query.data ?? [], [query.data]);
  const totals = useMemo(() => {
    const unitCount = rows.reduce((s, r) => s + r.unit_count, 0);
    const areaTotal = rows.reduce((s, r) => s + r.manual_area_total, 0);
    const buildingArea = rows.reduce((s, r) => s + r.building_area, 0);
    return { unitCount, areaTotal, buildingArea };
  }, [rows]);

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="floor-area-report-page">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">楼层面积报表</h1>
        <p className="text-sm text-muted-foreground mt-1">按楼层统计柜位数、柜位面积与建筑面积</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>统计结果</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>序号</TableHead>
                <TableHead>门店</TableHead>
                <TableHead>楼层</TableHead>
                <TableHead>楼层名称</TableHead>
                <TableHead>柜位数</TableHead>
                <TableHead>柜位面积</TableHead>
                <TableHead>建筑面积(m²)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.isLoading ? (
                <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    加载中...
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r, idx) => (
                  <TableRow key={r.floor_id}>
                    <TableCell>{idx + 1}</TableCell>
                    <TableCell>{r.store_name || r.store_code || "—"}</TableCell>
                    <TableCell>{r.building_code}-{r.floor_code}</TableCell>
                    <TableCell>{r.name}</TableCell>
                    <TableCell>{fmt(r.unit_count)}</TableCell>
                    <TableCell>{fmt(r.manual_area_total)}</TableCell>
                    <TableCell>{fmt(r.building_area)}</TableCell>
                  </TableRow>
                ))
              )}
              {rows.length > 0 && (
                <TableRow className="bg-slate-50 font-semibold">
                  <TableCell colSpan={4}>合计</TableCell>
                  <TableCell>{fmt(totals.unitCount)}</TableCell>
                  <TableCell>{fmt(totals.areaTotal)}</TableCell>
                  <TableCell>{fmt(totals.buildingArea)}</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
