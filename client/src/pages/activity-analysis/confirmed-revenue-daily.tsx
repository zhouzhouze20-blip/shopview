import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";

type ConfirmedRevenueSummary = {
  movement_count: number;
  missing_rate_count: number;
  business_amount: number;
  confirmed_revenue_amount: number;
  sales_revenue_amount: number | null;
  confirmed_revenue_ratio: number | null;
};

type StoreSummaryRow = ConfirmedRevenueSummary & {
  market_code: string;
  store_name: string;
};

type ConfirmedRevenueRow = {
  id: number;
  business_date: string;
  period_month: string;
  market_code: string;
  store_name: string;
  coupon_type: string;
  coupon_name: string | null;
  match_type: string;
  movement_direction: string;
  confirmed_at: string | null;
  confirmed_by_name: string | null;
  business_amount: number;
  revenue_rate: number | null;
  actual_revenue_amount: number;
  rate_status: "OK" | "MISSING_RATE";
  voucher_match_id: number | null;
  voucher_detail_id: string | null;
};

type ConfirmedRevenueResponse = {
  summary: ConfirmedRevenueSummary;
  store_summary: StoreSummaryRow[];
  rows: ConfirmedRevenueRow[];
};

const emptySummary: ConfirmedRevenueSummary = {
  movement_count: 0,
  missing_rate_count: 0,
  business_amount: 0,
  confirmed_revenue_amount: 0,
  sales_revenue_amount: null,
  confirmed_revenue_ratio: null,
};

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));

const percent = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "—";
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return "—";
  return `${(numericValue * 100).toFixed(2)}%`;
};

const fmtDate = (value: unknown) => (typeof value === "string" && value ? value.slice(0, 10) : "—");
const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 19) : "—");

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

const errorText = (error: unknown) => (error instanceof Error ? error.message : "请求失败");

export default function ConfirmedRevenueDailyPage() {
  const [startDate, setStartDate] = useState(() => localDateString());
  const [endDate, setEndDate] = useState("");
  const [storeCode, setStoreCode] = useState("all");
  const [couponType, setCouponType] = useState("all");

  const query = useQuery<ConfirmedRevenueResponse>({
    queryKey: ["/api/activity-analysis/coupon-confirmed-revenue-daily", startDate, endDate, storeCode, couponType],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-confirmed-revenue-daily${buildQuery({
          start_date: startDate,
          end_date: endDate || startDate,
          market_code: storeCode === "all" ? "" : storeCode,
          coupon_type: couponType === "all" ? "" : couponType,
        })}`,
      ),
  });

  const summary = query.data?.summary ?? emptySummary;
  const storeSummary = useMemo(() => query.data?.store_summary ?? [], [query.data]);
  const rows = useMemo(() => query.data?.rows ?? [], [query.data]);
  const couponOptions = useMemo(() => {
    const optionMap = new Map<string, string>();
    rows.forEach((row) => {
      const value = String(row.coupon_type || "").trim().toUpperCase();
      if (!value) return;
      optionMap.set(value, row.coupon_name ? `${value} ${row.coupon_name}` : value);
    });
    if (couponType !== "all" && !optionMap.has(couponType)) {
      optionMap.set(couponType, couponType);
    }
    return Array.from(optionMap.entries()).map(([value, label]) => ({ value, label }));
  }, [couponType, rows]);

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="max-w-3xl">
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">确认收入占比</h1>
        <p className="mt-1 text-sm text-muted-foreground">按财务确认时间查看已确认凭证匹配折算后的销售收入金额。</p>
      </div>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6 lg:items-end">
          <div className="min-w-0">
            <Label htmlFor="confirmed-revenue-start">开始日期</Label>
            <Input id="confirmed-revenue-start" className="mt-1" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </div>
          <div className="min-w-0">
            <Label htmlFor="confirmed-revenue-end">结束日期</Label>
            <Input id="confirmed-revenue-end" className="mt-1" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </div>
          <div className="min-w-0">
            <Label>门店</Label>
            <Select value={storeCode} onValueChange={setStoreCode}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部门店</SelectItem>
                <SelectItem value="601">601 购物中心</SelectItem>
                <SelectItem value="602">602 百货大楼</SelectItem>
                <SelectItem value="603">603 新世纪</SelectItem>
                <SelectItem value="604">604 半山</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-0">
            <Label>卡券</Label>
            <Select value={couponType} onValueChange={setCouponType}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部卡券</SelectItem>
                {couponOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={() => query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-lg">
        <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
          <SummaryBox label="确认收入金额" value={money(summary.confirmed_revenue_amount)} />
          <SummaryBox label="业务金额" value={money(summary.business_amount)} />
          <SummaryBox label="当天销售收入" value={summary.sales_revenue_amount == null ? "—" : money(summary.sales_revenue_amount)} />
          <SummaryBox label="确认收入占比" value={percent(summary.confirmed_revenue_ratio)} />
          <SummaryBox label="明细行数" value={number(summary.movement_count)} />
          <SummaryBox label="缺占比行" value={number(summary.missing_rate_count)} danger={summary.missing_rate_count > 0} />
        </CardContent>
      </Card>

      {query.isError ? <ErrorCard message={errorText(query.error)} /> : null}
      {!query.isFetching && !query.isError && rows.length === 0 ? <EmptyCard /> : null}
      {summary.missing_rate_count > 0 ? <ErrorCard message="存在缺收入占比的明细行，这些行的确认收入金额按 0 展示。" /> : null}

      <StoreSummaryTable rows={storeSummary} />
      <DetailTable rows={rows} />
    </div>
  );
}

function SummaryBox({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className={cn("rounded-lg border p-3", danger ? "border-amber-300 bg-amber-50" : "border-slate-200 bg-white")}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="rounded-lg border-amber-300 bg-amber-50">
      <CardContent className="flex items-center gap-2 p-4 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4" />
        {message}
      </CardContent>
    </Card>
  );
}

function EmptyCard() {
  return (
    <Card className="rounded-lg">
      <CardContent className="p-6 text-center text-sm text-muted-foreground">
        当前筛选范围没有每日收入变动，请先在卡券月结页面生成对应期间的每日变动。
      </CardContent>
    </Card>
  );
}

function StoreSummaryTable({ rows }: { rows: StoreSummaryRow[] }) {
  return (
    <Card className="rounded-lg">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>门店</TableHead>
              <TableHead className="text-right">行数</TableHead>
              <TableHead className="text-right">缺占比</TableHead>
              <TableHead className="text-right">业务金额</TableHead>
              <TableHead className="text-right">确认收入金额</TableHead>
              <TableHead className="text-right">销售收入</TableHead>
              <TableHead className="text-right">确认收入占比</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.market_code}>
                <TableCell className="font-medium">
                  {row.market_code} {row.store_name}
                </TableCell>
                <TableCell className="text-right">{number(row.movement_count)}</TableCell>
                <TableCell className={cn("text-right", row.missing_rate_count > 0 && "text-amber-700")}>{number(row.missing_rate_count)}</TableCell>
                <TableCell className="text-right">{money(row.business_amount)}</TableCell>
                <TableCell className="text-right">{money(row.confirmed_revenue_amount)}</TableCell>
                <TableCell className="text-right">{row.sales_revenue_amount == null ? "—" : money(row.sales_revenue_amount)}</TableCell>
                <TableCell className="text-right">{percent(row.confirmed_revenue_ratio)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function DetailTable({ rows }: { rows: ConfirmedRevenueRow[] }) {
  return (
    <Card className="rounded-lg">
      <CardContent className="overflow-x-auto p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>状态</TableHead>
              <TableHead>确认时间</TableHead>
              <TableHead>业务发生日</TableHead>
              <TableHead>门店</TableHead>
              <TableHead>券种</TableHead>
              <TableHead>方向</TableHead>
              <TableHead className="text-right">业务金额</TableHead>
              <TableHead className="text-right">收入占比</TableHead>
              <TableHead className="text-right">确认收入金额</TableHead>
              <TableHead>确认人</TableHead>
              <TableHead>凭证匹配ID</TableHead>
              <TableHead>凭证明细ID</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <RateStatusBadge status={row.rate_status} />
                </TableCell>
                <TableCell className="whitespace-nowrap">{fmtDateTime(row.confirmed_at)}</TableCell>
                <TableCell className="whitespace-nowrap">{fmtDate(row.business_date)}</TableCell>
                <TableCell className="whitespace-nowrap">
                  {row.market_code} {row.store_name}
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {row.coupon_type} {row.coupon_name || ""}
                </TableCell>
                <TableCell className="whitespace-nowrap">{row.movement_direction === "INCREASE" ? "增加" : "减少"}</TableCell>
                <TableCell className="text-right">{money(row.business_amount)}</TableCell>
                <TableCell className="text-right">{percent(row.revenue_rate)}</TableCell>
                <TableCell className="text-right">{money(row.actual_revenue_amount)}</TableCell>
                <TableCell className="whitespace-nowrap">{row.confirmed_by_name || "—"}</TableCell>
                <TableCell>{row.voucher_match_id || "—"}</TableCell>
                <TableCell className="max-w-[220px] truncate">{row.voucher_detail_id || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function RateStatusBadge({ status }: { status: string }) {
  if (status === "OK") {
    return <Badge variant="secondary">正常</Badge>;
  }
  return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">缺占比</Badge>;
}
