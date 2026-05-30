import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, RefreshCw, Search } from "lucide-react";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";

type CommoditySalesDetailRow = {
  floor_display: string;
  storage_area: string;
  counter_display: string;
  supplier_display: string;
  goods_code: string;
  barcode: string;
  goods_name: string;
  base_discount_rate: number;
  sales_discount_rate: number;
  preferential_discount_rate: number;
  concession_amount: number;
  sales_qty: number;
  priced_sales_amount: number;
  sales_revenue: number;
  gross_profit: number;
  gross_margin_rate: number;
  net_sales_amount: number;
  net_gross_profit: number;
  net_gross_margin_rate: number;
  sales_cost: number;
  net_sales_cost: number;
  total_discount: number;
  member_discount_amt: number;
  promo_discount_amt: number;
  auth_discount_amt: number;
  other_discount_amt: number;
};

type FilterState = {
  start_date: string;
  end_date: string;
  account_start_date: string;
  account_end_date: string;
  department: string;
  area: string;
  supplier_code: string;
  goods_code: string;
  group_code: string;
  operation_method: string;
  limit: number;
};

type DepartmentOption = {
  department_code: string;
  department_name: string;
  label: string;
};

type Column = {
  key: keyof CommoditySalesDetailRow;
  label: string;
  kind?: "money" | "number" | "rate";
  stickyLeft?: number;
  width?: number;
};

const columns: Column[] = [
  { key: "floor_display", label: "楼层" },
  { key: "storage_area", label: "库区" },
  { key: "counter_display", label: "柜组", stickyLeft: 0, width: 180 },
  { key: "supplier_display", label: "供应商" },
  { key: "goods_code", label: "商品编码", stickyLeft: 180, width: 100 },
  { key: "barcode", label: "商品条码", stickyLeft: 280, width: 150 },
  { key: "goods_name", label: "商品名称", stickyLeft: 430, width: 220 },
  { key: "base_discount_rate", label: "原扣率", kind: "rate" },
  { key: "sales_discount_rate", label: "销售扣率", kind: "rate" },
  { key: "preferential_discount_rate", label: "优惠扣率", kind: "rate" },
  { key: "concession_amount", label: "让扣金额", kind: "money" },
  { key: "sales_qty", label: "销售数量", kind: "number" },
  { key: "priced_sales_amount", label: "售价金额", kind: "money" },
  { key: "sales_revenue", label: "销售收入", kind: "money" },
  { key: "gross_profit", label: "毛利", kind: "money" },
  { key: "gross_margin_rate", label: "毛利率", kind: "rate" },
  { key: "net_sales_amount", label: "销售净额", kind: "money" },
  { key: "net_gross_profit", label: "净毛利", kind: "money" },
  { key: "net_gross_margin_rate", label: "净毛利率", kind: "rate" },
  { key: "sales_cost", label: "销售成本", kind: "money" },
  { key: "net_sales_cost", label: "净销售成本", kind: "money" },
  { key: "total_discount", label: "总折扣", kind: "money" },
  { key: "member_discount_amt", label: "会员折扣", kind: "money" },
  { key: "promo_discount_amt", label: "促销折扣", kind: "money" },
  { key: "auth_discount_amt", label: "授权折扣", kind: "money" },
  { key: "other_discount_amt", label: "其他折扣", kind: "money" },
];

const toDateString = (date: Date) => {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

const defaultFilters = (): FilterState => {
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  return {
    start_date: toDateString(monthStart),
    end_date: toDateString(yesterday),
    account_start_date: "",
    account_end_date: "",
    department: "",
    area: "",
    supplier_code: "",
    goods_code: "",
    group_code: "",
    operation_method: "",
    limit: 500,
  };
};

const buildQuery = (params: Record<string, string | number | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    const text = String(value).trim();
    if (text) search.set(key, text);
  });
  const query = search.toString();
  return query ? `?${query}` : "";
};

const formatValue = (value: string | number | null | undefined, kind?: "money" | "number" | "rate") => {
  if (value === null || value === undefined || value === "") return "";
  if (!kind) return String(value);
  const numeric = Number(value || 0);
  if (kind === "rate") return `${(numeric * 100).toFixed(2)}%`;
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
};

const numericExportValue = (value: string | number | null | undefined, kind?: "money" | "number" | "rate") => {
  if (value === null || value === undefined || value === "") return "";
  const numeric = Number(value || 0);
  if (!kind) return String(value);
  if (kind === "rate") return Math.round(numeric * 10000) / 100;
  return numeric;
};

const safeFilenamePart = (value: string) => value.replace(/[/\\?%*:|"<>]/g, "_");

const stickyColumnClass = (column: Column) =>
  column.stickyLeft === undefined ? "" : "sticky z-20 bg-white shadow-[1px_0_0_0_rgba(15,23,42,0.2)]";

export default function CommoditySalesDetailReportPage() {
  const [filters, setFilters] = useState<FilterState>(() => defaultFilters());
  const queryParams = useMemo(
    () => ({
      ...filters,
      limit: filters.limit || 500,
    }),
    [filters],
  );

  const reportQuery = useQuery<CommoditySalesDetailRow[]>({
    queryKey: ["/api/sales/reports/commodity-sales-detail", queryParams],
    queryFn: () => apiGet(`/api/sales/reports/commodity-sales-detail${buildQuery(queryParams)}`),
  });

  const departmentsQuery = useQuery<DepartmentOption[]>({
    queryKey: ["/api/sales/reports/commodity-sales-detail/departments"],
    queryFn: () => apiGet("/api/sales/reports/commodity-sales-detail/departments"),
  });

  const departmentOptions = useMemo(() => {
    return (departmentsQuery.data ?? []).map((department) => ({
      value: department.department_code || department.department_name,
      label: department.label || department.department_name || `[${department.department_code}]`,
    }));
  }, [departmentsQuery.data]);

  const setField = (key: keyof FilterState, value: string) => {
    setFilters((current) => ({
      ...current,
      [key]: key === "limit" ? Number(value || 500) : value,
    }));
  };

  const rows = reportQuery.data ?? [];

  const exportExcel = () => {
    const header = columns.map((column) => (column.kind === "rate" ? `${column.label}(%)` : column.label));
    const body = rows.map((row) => columns.map((column) => numericExportValue(row[column.key], column.kind)));
    const ws = XLSX.utils.aoa_to_sheet([header, ...body]);
    ws["!cols"] = columns.map((column) => ({
      wch: column.key === "goods_name" ? 28 : column.key === "counter_display" ? 24 : column.kind ? 12 : 16,
    }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "商品销售明细");
    XLSX.writeFile(
      wb,
      `商品销售明细_${safeFilenamePart(filters.start_date || "未选")}_${safeFilenamePart(filters.end_date || "未选")}.xlsx`,
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">商品销售明细</h1>
        <p className="text-sm text-muted-foreground mt-1">
          对应 ERP「销售管理 · 报表分析 · 633 · 商品销售明细报表」。当前直接按 SQL 从 salegoodslist 汇总，并用
          manaframe 替换 VIEW_MFRAME_ALL。
        </p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">筛选</CardTitle>
          <CardDescription>发生日期、记账日期、部门、库区、供应商、商品编码、柜组、经营方式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="csd-start">发生日期起</Label>
              <Input id="csd-start" type="date" value={filters.start_date} onChange={(e) => setField("start_date", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-end">发生日期止</Label>
              <Input id="csd-end" type="date" value={filters.end_date} onChange={(e) => setField("end_date", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-account-start">记账日期起</Label>
              <Input
                id="csd-account-start"
                type="date"
                value={filters.account_start_date}
                onChange={(e) => setField("account_start_date", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-account-end">记账日期止</Label>
              <Input
                id="csd-account-end"
                type="date"
                value={filters.account_end_date}
                onChange={(e) => setField("account_end_date", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-dept">部门</Label>
              <Select
                value={filters.department || "__all__"}
                onValueChange={(value) => setField("department", value === "__all__" ? "" : value)}
              >
                <SelectTrigger id="csd-dept">
                  <SelectValue placeholder="全部部门" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">全部部门</SelectItem>
                  {departmentOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-area">库区</Label>
              <Input id="csd-area" value={filters.area} onChange={(e) => setField("area", e.target.value)} placeholder="编码或名称" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-supplier">供应商</Label>
              <Input
                id="csd-supplier"
                value={filters.supplier_code}
                onChange={(e) => setField("supplier_code", e.target.value)}
                placeholder="供应商编码"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-goods">商品编码</Label>
              <Input id="csd-goods" value={filters.goods_code} onChange={(e) => setField("goods_code", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-group">柜组</Label>
              <Input id="csd-group" value={filters.group_code} onChange={(e) => setField("group_code", e.target.value)} placeholder="编码或名称，支持模糊查询" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-method">经营方式</Label>
              <Input
                id="csd-method"
                value={filters.operation_method}
                onChange={(e) => setField("operation_method", e.target.value)}
                placeholder="租赁/联营/自营"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="csd-limit">行数</Label>
              <Input id="csd-limit" type="number" min={1} max={5000} value={filters.limit} onChange={(e) => setField("limit", e.target.value)} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => reportQuery.refetch()} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button variant="outline" onClick={() => setFilters(defaultFilters())}>
              <RefreshCw className="mr-2 h-4 w-4" />
              重置
            </Button>
            <Button variant="outline" onClick={exportExcel} disabled={rows.length === 0}>
              <Download className="mr-2 h-4 w-4" />
              导出 Excel
            </Button>
            <span className="text-sm text-muted-foreground">共 {rows.length} 行</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">明细</CardTitle>
          <CardDescription>列与 ERP 报表一致；数据来自实时 SQL 汇总，不依赖 rpt_goods_sales_detail。</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table className="min-w-[2350px] border-separate border-spacing-0 text-[12px]">
            <TableHeader>
              <TableRow>
                {columns.map((c) => (
                  <TableHead
                    key={c.key}
                    className={cn(
                      "h-8 border-b border-r border-slate-300 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-900",
                      stickyColumnClass(c),
                      c.stickyLeft !== undefined && "z-30 overflow-hidden text-ellipsis",
                    )}
                    style={{
                      left: c.stickyLeft,
                      minWidth: c.width,
                      width: c.width,
                    }}
                  >
                    {c.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {reportQuery.isError ? (
                <TableRow>
                  <TableCell colSpan={columns.length} className="text-center text-red-600 py-10">
                    {(reportQuery.error as Error).message}
                  </TableCell>
                </TableRow>
              ) : reportQuery.isLoading ? (
                <TableRow>
                  <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-10">
                    正在查询...
                  </TableCell>
                </TableRow>
              ) : rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length} className="text-center text-muted-foreground py-10">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((row, index) => (
                  <TableRow key={`${row.goods_code}-${row.barcode}-${row.counter_display}-${index}`} className="h-8 hover:bg-slate-50">
                    {columns.map((column) => (
                      <TableCell
                        key={column.key}
                        className={cn(
                          column.kind
                            ? "whitespace-nowrap border-b border-r border-slate-200 px-2 py-1 text-right text-xs"
                            : "whitespace-nowrap overflow-hidden text-ellipsis border-b border-r border-slate-200 px-2 py-1 text-xs",
                          stickyColumnClass(column),
                        )}
                        style={{
                          left: column.stickyLeft,
                          minWidth: column.width,
                          width: column.width,
                        }}
                      >
                        {formatValue(row[column.key], column.kind)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
