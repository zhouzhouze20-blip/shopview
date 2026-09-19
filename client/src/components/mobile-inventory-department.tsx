import { useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Building2, ChevronRight, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/lib/api";

type DepartmentOption = { value: string; label: string; code: string; name: string };

export type DepartmentInventoryRow = {
  store_code: string;
  store_display: string;
  supplier_code: string;
  supplier_display: string;
  group_code: string;
  group_name: string;
  group_display: string;
  inventory_quantity: number;
  retail_amount: number | null;
};

type DepartmentInventoryResponse = {
  department_code: string;
  rows: DepartmentInventoryRow[];
  summary: {
    total_count: number;
    inventory_quantity: number;
    retail_amount: number;
  };
  limit: number;
  offset: number;
  source_note: string;
};

const PAGE_SIZE = 50;
const format = (value: number | null | undefined, digits: number) =>
  value == null || !Number.isFinite(Number(value)) ? "—" : new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));

export function MobileInventoryDepartment({
  active,
  userId,
  onDrilldown,
  onQuery,
}: {
  active: boolean;
  userId: number | undefined;
  onDrilldown: (row: DepartmentInventoryRow) => void;
  onQuery: (department: DepartmentOption) => void;
}) {
  const [department, setDepartment] = useState<DepartmentOption | null>(null);
  const optionsQuery = useQuery<{ options: DepartmentOption[] }>({
    queryKey: ["/api/sales/reports/inventory-departments", userId],
    queryFn: () => apiGet("/api/sales/reports/inventory-departments"),
    enabled: active,
  });
  const inventoryQuery = useInfiniteQuery<DepartmentInventoryResponse>({
    queryKey: ["/api/sales/reports/inventory-department-summary", userId, department?.value],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({
        department_code: department?.value ?? "",
        limit: String(PAGE_SIZE),
        offset: String(Number(pageParam) || 0),
      });
      return apiGet(`/api/sales/reports/inventory-department-summary?${params.toString()}`);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.rows.length;
      return lastPage.rows.length > 0 && nextOffset < lastPage.summary.total_count ? nextOffset : undefined;
    },
    enabled: active && Boolean(department),
  });
  const rows = inventoryQuery.data?.pages.flatMap((page) => page.rows) ?? [];
  const summary = inventoryQuery.data?.pages[0]?.summary;

  return (
    <div className="space-y-4">
      <Card className="rounded-3xl border-0 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base"><Building2 className="h-5 w-5 text-teal-700" />部门库存</CardTitle>
          <CardDescription>选择部门，按供应商、柜组查看正库存汇总。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="block text-xs font-medium text-slate-600" htmlFor="mobile-inventory-department">部门</label>
          <select
            id="mobile-inventory-department"
            className="h-12 w-full min-w-0 rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-900"
            value={department?.value ?? ""}
            disabled={optionsQuery.isLoading || Boolean(optionsQuery.error)}
            onChange={(event) => {
              const selected = optionsQuery.data?.options.find((option) => option.value === event.target.value) ?? null;
              setDepartment(selected);
              if (selected) onQuery(selected);
            }}
          >
            <option value="">{optionsQuery.isLoading ? "正在加载部门…" : "请选择部门"}</option>
            {optionsQuery.data?.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          {optionsQuery.error ? (
            <div role="alert" className="text-sm text-red-700">部门加载失败。
              <Button variant="link" className="h-auto px-2 py-0" onClick={() => optionsQuery.refetch()}>重试</Button>
            </div>
          ) : optionsQuery.isSuccess && optionsQuery.data.options.length === 0 ? (
            <div className="text-sm text-slate-500">当前数据范围内没有可查询的正库存部门。</div>
          ) : null}
          <div className="text-[11px] leading-5 text-slate-500">仅显示账号数据范围内有正库存的部门；汇总金额按零售价合计。</div>
        </CardContent>
      </Card>

      {!department ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center text-sm text-slate-500">请选择部门查看库存列表</div>
      ) : inventoryQuery.isLoading ? (
        <div className="flex items-center justify-center rounded-3xl bg-white py-12 text-sm text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询部门库存…</div>
      ) : inventoryQuery.isError && !inventoryQuery.data ? (
        <div role="alert" className="rounded-3xl bg-red-50 px-5 py-8 text-center text-sm text-red-700">
          部门库存查询失败，请检查网络或权限。
          <Button variant="link" className="block w-full" onClick={() => inventoryQuery.refetch()}>重新查询</Button>
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-3xl bg-white px-5 py-10 text-center text-sm text-slate-500">该部门在当前数据范围内没有正库存。</div>
      ) : (
        <>
          <Card className="overflow-hidden rounded-3xl border-0 bg-gradient-to-br from-teal-700 to-emerald-800 text-white shadow-lg">
            <CardContent className="space-y-3 p-4">
              <div className="text-sm font-semibold leading-6">{department.label}</div>
              <div className="grid grid-cols-1 gap-2 min-[360px]:grid-cols-2">
                <div className="min-w-0 rounded-2xl bg-white/10 p-3">
                  <div className="text-xs text-teal-100">库存数量</div>
                  <div className="mt-1 break-all text-lg font-bold tabular-nums">{format(summary?.inventory_quantity, 4)}</div>
                </div>
                <div className="min-w-0 rounded-2xl bg-white/10 p-3">
                  <div className="text-xs text-teal-100">供应商 / 柜组组合</div>
                  <div className="mt-1 text-lg font-bold tabular-nums">{summary?.total_count ?? 0}</div>
                </div>
                <div className="min-w-0 rounded-2xl bg-white/10 p-3 min-[360px]:col-span-2">
                  <div className="text-xs text-teal-100">零售价金额（元）</div>
                  <div className="mt-1 break-all text-2xl font-bold tabular-nums">¥{format(summary?.retail_amount, 2)}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <section aria-label="部门库存汇总列表" className="space-y-2">
            <div className="flex items-center justify-between px-1 text-xs text-slate-500">
              <h2 className="font-semibold text-slate-800">供应商 / 柜组库存</h2><span>点击查看柜组明细</span>
            </div>
            {rows.map((row) => (
              <button
                key={JSON.stringify([row.store_code, row.supplier_code, row.group_code])}
                type="button"
                className="block w-full rounded-2xl bg-white p-4 text-left shadow-sm outline-offset-2 hover:bg-teal-50 focus-visible:outline-teal-600 active:bg-teal-100"
                onClick={() => onDrilldown(row)}
                aria-label={`查看${row.group_display}柜组库存，供应商${row.supplier_display}`}
              >
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="break-words text-sm font-semibold leading-5 text-slate-900"><span className="mr-2 font-normal text-slate-500">供应商</span>{row.supplier_display || "未标记供应商"}</div>
                    <div className="break-words text-xs leading-5 text-slate-700"><span className="mr-2 text-slate-500">柜组</span>{row.group_display}</div>
                  </div>
                  <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-teal-700" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-100 pt-2">
                  <div className="min-w-0"><div className="text-[11px] text-slate-500">数量</div><div className="mt-1 break-all text-sm font-semibold tabular-nums text-slate-900">{format(row.inventory_quantity, 4)}</div></div>
                  <div className="min-w-0 text-right"><div className="text-[11px] text-slate-500">零售价金额（元）</div><div className="mt-1 break-all text-sm font-semibold tabular-nums text-teal-800">¥{format(row.retail_amount, 2)}</div></div>
                </div>
              </button>
            ))}
          </section>
          <div className="space-y-2 text-center">
            <div className="text-xs text-slate-500">已显示 {rows.length} / {summary?.total_count ?? 0} 条汇总</div>
            {inventoryQuery.isError && <div role="alert" className="text-xs text-red-700">库存更新失败，当前显示上次查询结果，请重试。</div>}
            {inventoryQuery.hasNextPage ? (
              <Button variant="outline" className="h-11 w-full rounded-xl" disabled={inventoryQuery.isFetching} onClick={() => inventoryQuery.fetchNextPage()}>
                {inventoryQuery.isFetchingNextPage && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {inventoryQuery.isFetchNextPageError ? "重试加载" : "继续加载"}
              </Button>
            ) : <div className="text-xs text-teal-700">已显示全部汇总</div>}
            <Button variant="ghost" className="h-9 text-xs" disabled={inventoryQuery.isFetching} onClick={() => inventoryQuery.refetch()}>刷新部门库存</Button>
          </div>
          <p className="px-1 text-[11px] leading-5 text-slate-500">{inventoryQuery.data?.pages[0]?.source_note}</p>
        </>
      )}
    </div>
  );
}
