import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Equal, Info, Loader2, Search, TrendingDown, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";


type Classification = "增长" | "下降" | "持平" | "待复核";

type JointRenewalRevenueItem = {
  pair_id: string;
  store_code: string;
  store_name: string;
  department_code: string;
  department_name: string;
  supplier_code: string;
  supplier_name: string;
  group_code: string;
  group_name: string;
  brand_name: string;
  old_contract_no: string;
  old_start_date: string;
  old_end_date: string;
  new_contract_no: string;
  new_start_date: string;
  new_end_date: string;
  gap_days: number;
  old_contract_rate: number | null;
  new_contract_rate: number | null;
  contract_rate_delta: number | null;
  sales_row_count: number;
  sales_first_date: string | null;
  sales_last_date: string | null;
  priced_sales_amount: number;
  sales_revenue: number;
  actual_gross_profit: number;
  base_rate_impact: number | null;
  simulated_new_profit: number | null;
  change_rate: number | null;
  classification: Classification;
  review_required: boolean;
  review_reasons: string[];
  activity_payment_breakdown_available: boolean;
};

type JointRenewalRevenueResponse = {
  start_date: string;
  end_date: string;
  operation_method: string;
  source_coverage: {
    sales_min_date: string | null;
    sales_max_date: string | null;
    sales_source: string;
  };
  calculation_note: string;
  summary: {
    renewal_contract_count: number;
    pair_count: number;
    growth_count: number;
    decline_count: number;
    flat_count: number;
    pending_review_count: number;
    review_flag_count: number;
    priced_sales_amount: number;
    actual_gross_profit: number;
    base_rate_impact: number;
    simulated_new_profit: number;
  };
  items: JointRenewalRevenueItem[];
};

type DateFilters = { startDate: string; endDate: string };
type ResultFilter = "全部" | Classification | "需复核";


function localIsoDate(value: Date): string {
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function defaultDates(): DateFilters {
  const today = new Date();
  return {
    startDate: localIsoDate(new Date(today.getFullYear(), 0, 1)),
    endDate: localIsoDate(today),
  };
}

function money(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function rate(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function classificationClass(value: Classification): string {
  if (value === "增长") return "border-red-200 bg-red-50 text-red-700";
  if (value === "下降") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value === "待复核") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function MetricCard({
  title,
  value,
  note,
  tone = "slate",
}: {
  title: string;
  value: string;
  note?: string;
  tone?: "slate" | "red" | "green" | "amber";
}) {
  const toneClass = {
    slate: "text-slate-900",
    red: "text-red-700",
    green: "text-emerald-700",
    amber: "text-amber-700",
  }[tone];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-slate-500">{title}</CardTitle></CardHeader>
      <CardContent>
        <div className={cn("text-2xl font-semibold tabular-nums", toneClass)}>{value}</div>
        {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
      </CardContent>
    </Card>
  );
}

export default function JointRenewalRevenueReportPage() {
  const initialDates = useMemo(() => defaultDates(), []);
  const [draft, setDraft] = useState<DateFilters>(initialDates);
  const [submitted, setSubmitted] = useState<DateFilters>(initialDates);
  const [resultFilter, setResultFilter] = useState<ResultFilter>("全部");

  const params = useMemo(() => {
    const query = new URLSearchParams({
      start_date: submitted.startDate,
      end_date: submitted.endDate,
    });
    return query.toString();
  }, [submitted]);

  const reportQuery = useQuery<JointRenewalRevenueResponse>({
    queryKey: ["joint-renewal-revenue", submitted.startDate, submitted.endDate],
    queryFn: () => apiGet(`/api/reports/joint-renewal-revenue?${params}`),
    enabled: Boolean(submitted.startDate && submitted.endDate && submitted.startDate <= submitted.endDate),
  });

  const items = useMemo(() => {
    const source = reportQuery.data?.items ?? [];
    const filtered = source.filter((item) => {
      if (resultFilter === "全部") return true;
      if (resultFilter === "需复核") return item.review_required;
      return item.classification === resultFilter;
    });
    return [...filtered].sort((left, right) => {
      const leftAmount = Math.abs(left.base_rate_impact ?? 0);
      const rightAmount = Math.abs(right.base_rate_impact ?? 0);
      return rightAmount - leftAmount;
    });
  }, [reportQuery.data?.items, resultFilter]);

  const submit = () => {
    if (!draft.startDate || !draft.endDate || draft.endDate < draft.startDate) return;
    if (draft.startDate === submitted.startDate && draft.endDate === submitted.endDate) {
      void reportQuery.refetch();
      return;
    }
    setSubmitted({ ...draft });
  };

  const summary = reportQuery.data?.summary;
  const comparableCount = summary
    ? summary.growth_count + summary.decline_count + summary.flat_count
    : 0;

  return (
    <div className="container mx-auto space-y-6 p-6" data-testid="joint-renewal-revenue-report-page">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-slate-900">联营续签合同收益影响分析</h1>
          <Badge variant="outline" className="border-blue-200 bg-blue-50 text-blue-700">第一稿</Badge>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          用上一合同期间的实际销售，测算续签合同基础扣率变化带来的收益影响。
        </p>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">查询条件</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="joint-renewal-start">续签生效开始日期</Label>
              <Input
                id="joint-renewal-start"
                type="date"
                className="w-[210px]"
                value={draft.startDate}
                onChange={(event) => setDraft((current) => ({ ...current, startDate: event.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="joint-renewal-end">续签生效结束日期</Label>
              <Input
                id="joint-renewal-end"
                type="date"
                className="w-[210px]"
                value={draft.endDate}
                onChange={(event) => setDraft((current) => ({ ...current, endDate: event.target.value }))}
              />
            </div>
            <Button onClick={submit} disabled={reportQuery.isFetching || draft.endDate < draft.startDate}>
              {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
          </div>
          {draft.endDate < draft.startDate && <p className="mt-3 text-sm text-red-600">结束日期不能早于开始日期</p>}
        </CardContent>
      </Card>

      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
          <MetricCard title="续签合同" value={`${summary.renewal_contract_count} 份`} note={`${summary.pair_count} 条合同-柜组`} />
          <MetricCard title="可测算柜组" value={`${comparableCount} 条`} note={`${summary.pending_review_count} 条无完整测算`} />
          <MetricCard title="收益增长" value={`${summary.growth_count} 条`} tone="red" />
          <MetricCard title="收益下降" value={`${summary.decline_count} 条`} tone="green" />
          <MetricCard title="上一合同销售基数" value={money(summary.priced_sales_amount)} />
          <MetricCard
            title="基础扣率收益影响"
            value={money(summary.base_rate_impact)}
            tone={summary.base_rate_impact > 0 ? "red" : summary.base_rate_impact < 0 ? "green" : "slate"}
          />
        </div>
      )}

      {reportQuery.data && (
        <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950">
          <div className="flex gap-2">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">第一稿计算边界</p>
              <p className="mt-1">{reportQuery.data.calculation_note}</p>
              <p className="mt-1 text-blue-800">
                销售日汇总覆盖 {reportQuery.data.source_coverage.sales_min_date || "—"} 至 {reportQuery.data.source_coverage.sales_max_date || "—"}；
                活动扣点、付款方式收费及会员储值卡比例暂不拆分为独立收益项。
              </p>
            </div>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="text-base">续签合同—柜组明细</CardTitle>
            <p className="mt-1 text-xs text-slate-500">增长用红色、下降用绿色；“需复核”不代表没有收益。</p>
          </div>
          <Select value={resultFilter} onValueChange={(value) => setResultFilter(value as ResultFilter)}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {(["全部", "增长", "下降", "持平", "待复核", "需复核"] as ResultFilter[]).map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[180px]">门店 / 部门</TableHead>
                  <TableHead className="min-w-[220px]">供应商 / 柜组</TableHead>
                  <TableHead className="min-w-[225px]">上一合同</TableHead>
                  <TableHead className="min-w-[225px]">续签合同</TableHead>
                  <TableHead className="min-w-[135px] text-right">上一合同销售</TableHead>
                  <TableHead className="min-w-[135px] text-right">实际毛利</TableHead>
                  <TableHead className="min-w-[150px] text-right">基础扣率变化</TableHead>
                  <TableHead className="min-w-[150px] text-right">收益影响</TableHead>
                  <TableHead className="min-w-[200px]">结果 / 复核说明</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reportQuery.isFetching ? (
                  <TableRow><TableCell colSpan={9} className="py-12 text-center text-slate-500"><Loader2 className="mr-2 inline h-4 w-4 animate-spin" />正在计算续签合同收益影响…</TableCell></TableRow>
                ) : reportQuery.isError ? (
                  <TableRow><TableCell colSpan={9} className="py-12 text-center text-red-600">报表加载失败，请缩短查询期间后重试。</TableCell></TableRow>
                ) : items.length === 0 ? (
                  <TableRow><TableCell colSpan={9} className="py-12 text-center text-slate-500">当前期间没有符合条件的联营续签合同。</TableCell></TableRow>
                ) : items.map((item) => (
                  <TableRow key={item.pair_id} className={item.review_required ? "bg-amber-50/30" : undefined}>
                    <TableCell>
                      <div className="font-medium">{item.store_name || item.store_code}</div>
                      <div className="text-xs text-slate-500">{item.department_name || item.department_code || "未匹配部门"}</div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{item.supplier_name || item.supplier_code}</div>
                      <div className="text-xs text-slate-500">{item.group_name || item.brand_name || "—"}</div>
                      <div className="text-xs text-slate-400">{item.group_code}</div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{item.old_contract_no}</div>
                      <div className="text-xs text-slate-500">{item.old_start_date} 至 {item.old_end_date}</div>
                      <div className="text-xs text-slate-500">扣率1：{rate(item.old_contract_rate)}</div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{item.new_contract_no}</div>
                      <div className="text-xs text-slate-500">{item.new_start_date} 至 {item.new_end_date}</div>
                      <div className="text-xs text-slate-500">扣率1：{rate(item.new_contract_rate)}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div className="font-medium">{money(item.priced_sales_amount)}</div>
                      <div className="text-xs text-slate-500">{item.sales_first_date || "—"} 至 {item.sales_last_date || "—"}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div className="font-medium">{money(item.actual_gross_profit)}</div>
                      <div className="text-xs text-slate-500">已含活动及支付影响</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div className={cn("font-medium", (item.contract_rate_delta ?? 0) > 0 ? "text-red-600" : (item.contract_rate_delta ?? 0) < 0 ? "text-emerald-600" : "")}>{rate(item.contract_rate_delta)}</div>
                      <div className="text-xs text-slate-500">新 {rate(item.new_contract_rate)} / 原 {rate(item.old_contract_rate)}</div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div className={cn("font-semibold", (item.base_rate_impact ?? 0) > 0 ? "text-red-600" : (item.base_rate_impact ?? 0) < 0 ? "text-emerald-600" : "")}>{money(item.base_rate_impact)}</div>
                      <div className="text-xs text-slate-500">模拟毛利 {money(item.simulated_new_profit)}</div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline" className={classificationClass(item.classification)}>
                          {item.classification === "增长" && <TrendingUp className="mr-1 h-3 w-3" />}
                          {item.classification === "下降" && <TrendingDown className="mr-1 h-3 w-3" />}
                          {item.classification === "持平" && <Equal className="mr-1 h-3 w-3" />}
                          {item.classification}
                        </Badge>
                        {item.review_required && <Badge variant="outline" className="border-amber-300 text-amber-800">需复核</Badge>}
                      </div>
                      {item.review_reasons.length > 0 && (
                        <div className="mt-2 flex gap-1 text-xs leading-5 text-amber-800">
                          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          <span>{item.review_reasons.join("；")}</span>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {items.length > 0 && <p className="mt-3 text-xs text-slate-500">当前显示 {items.length} 条，按收益影响绝对值从大到小排列。</p>}
        </CardContent>
      </Card>
    </div>
  );
}
