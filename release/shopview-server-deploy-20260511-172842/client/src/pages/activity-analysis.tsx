import { useEffect, useMemo, useState } from "react";
import type { ComponentType } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, ClipboardList, CreditCard, Loader2, RefreshCw, Search, TicketPercent, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet } from "@/lib/api";

type ActivityOption = {
  activity_id: string;
  activity_name: string;
  start_date: string;
  end_date: string;
  ticket_count: number;
  card_log_amount: number;
  coupon_pay_amount: number;
};

type ActivityOverview = {
  activity?: {
    activity_id: string;
    activity_name: string;
    start_date: string;
    end_date: string;
    coupon_start_date?: string | null;
    coupon_end_date?: string | null;
    memo?: string | null;
  } | null;
  summary: Record<string, number | string | null>;
  payment_methods: Array<Record<string, number | string | null>>;
  departments: Array<Record<string, number | string | null>>;
  products: Array<Record<string, number | string | null>>;
  members: Array<Record<string, number | string | null>>;
  quality: Record<string, number | string | null>;
};

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(
    Number(value || 0),
  );

const number = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));

const percent = (numerator: unknown, denominator: unknown) => {
  const n = Number(numerator || 0);
  const d = Number(denominator || 0);
  if (!(d > 0)) return "—";
  return `${((n / d) * 100).toFixed(1)}%`;
};

const fmtDate = (value?: string | null) => (value ? value.slice(0, 10) : "—");

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="rounded-lg">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-2 truncate text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
          {subtitle ? <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p> : null}
        </div>
        <div className="rounded-md bg-slate-100 p-2 text-slate-700">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function ActivityAnalysisPage() {
  const [keyword, setKeyword] = useState("");
  const [activityId, setActivityId] = useState("");

  const activitiesQuery = useQuery<ActivityOption[]>({
    queryKey: ["/api/activity-analysis/activities", keyword],
    queryFn: () => apiGet(`/api/activity-analysis/activities${buildQuery({ keyword, limit: 120 })}`),
  });

  const activities = activitiesQuery.data || [];

  useEffect(() => {
    if (!activityId && activities.length > 0) {
      setActivityId((activities.find((item) => Number(item.ticket_count || 0) > 0) || activities[0]).activity_id);
    }
  }, [activityId, activities]);

  const overviewQuery = useQuery<ActivityOverview>({
    queryKey: ["/api/activity-analysis/overview", activityId],
    queryFn: () => apiGet(`/api/activity-analysis/overview${buildQuery({ activity_id: activityId, limit: 30 })}`),
    enabled: !!activityId,
  });

  const selectedActivity = useMemo(
    () => activities.find((item) => item.activity_id === activityId),
    [activities, activityId],
  );
  const overview = overviewQuery.data;
  const summary = overview?.summary || {};
  const quality = overview?.quality || {};

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">活动分析</h1>
          <p className="mt-1 text-sm text-muted-foreground">一期聚焦卡券使用，销售、成本和毛利取销售汇总表。</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="w-full sm:w-72">
            <Label htmlFor="activity-search">活动搜索</Label>
            <div className="mt-1 flex gap-2">
              <Input
                id="activity-search"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="活动编码或主题"
              />
              <Button variant="outline" size="icon" onClick={() => activitiesQuery.refetch()} aria-label="搜索活动">
                <Search className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="w-full sm:w-96">
            <Label>活动档期</Label>
            <Select value={activityId} onValueChange={setActivityId}>
              <SelectTrigger className="mt-1">
                <SelectValue placeholder="选择活动" />
              </SelectTrigger>
              <SelectContent>
                {activities.map((activity) => (
                  <SelectItem key={activity.activity_id} value={activity.activity_id}>
                    {activity.activity_id}｜{activity.activity_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={() => overviewQuery.refetch()} disabled={!activityId || overviewQuery.isFetching}>
            {overviewQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </div>
      </div>

      {selectedActivity ? (
        <Card className="rounded-lg">
          <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{selectedActivity.activity_id}</Badge>
                <span className="font-medium text-slate-900">{selectedActivity.activity_name}</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                活动期：{fmtDate(selectedActivity.start_date)} 至 {fmtDate(selectedActivity.end_date)}
              </p>
            </div>
            <div className="text-sm text-muted-foreground">
              已关联小票 {number(selectedActivity.ticket_count)}，卡券日志金额 {money(selectedActivity.card_log_amount)}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {overviewQuery.isLoading ? (
        <div className="flex min-h-64 items-center justify-center text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          正在加载活动分析...
        </div>
      ) : overviewQuery.isError ? (
        <Card className="rounded-lg border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-700">活动分析加载失败，请检查接口或数据表。</CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="活动销售额" value={money(summary.sales_amount)} subtitle={`小票 ${number(summary.ticket_count)} 笔`} icon={BarChart3} />
            <MetricCard title="卡券付款金额" value={money(summary.coupon_pay_amount)} subtitle={`0500 ${money(summary.pay_0500_amount)} / 0580 ${money(summary.pay_0580_amount)}`} icon={CreditCard} />
            <MetricCard title="净毛利" value={money(summary.net_profit)} subtitle={`毛利率 ${percent(summary.net_profit, summary.sales_amount)}`} icon={TicketPercent} />
            <MetricCard title="会员人数" value={number(summary.member_count)} subtitle={`卡券日志 ${number(summary.card_log_count)} 条`} icon={Users} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="rounded-lg lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">卡券口径核对</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">日志金额</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.card_log_amount)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">付款金额</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.coupon_pay_amount)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">期间0500/0580付款</p>
                  <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.period_coupon_pay_amount)}</p>
                </div>
              </CardContent>
            </Card>
            <Card className="rounded-lg">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center text-base">
                  <ClipboardList className="mr-2 h-4 w-4" />
                  数据质量
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between"><span>原始日志</span><span className="tabular-nums">{number(quality.raw_log_count)}</span></div>
                <div className="flex justify-between"><span>已关联小票日志</span><span className="tabular-nums">{number(quality.matched_log_count)}</span></div>
                <div className="flex justify-between"><span>未关联日志</span><span className="tabular-nums">{number(quality.unmatched_log_count)}</span></div>
                <div className="flex justify-between"><span>期间付款无日志</span><span className="tabular-nums">{number(quality.period_payment_without_log_count)}</span></div>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="payments" className="space-y-4">
            <TabsList>
              <TabsTrigger value="payments">付款方式</TabsTrigger>
              <TabsTrigger value="departments">部门柜组</TabsTrigger>
              <TabsTrigger value="products">商品品牌</TabsTrigger>
              <TabsTrigger value="members">会员</TabsTrigger>
            </TabsList>

            <TabsContent value="payments">
              <SimpleTable
                rows={overview?.payment_methods || []}
                columns={[
                  ["paycode", "付款代码"],
                  ["payname", "付款名称"],
                  ["payment_count", "笔数", number],
                  ["payment_amount", "金额", money],
                ]}
              />
            </TabsContent>
            <TabsContent value="departments">
              <SimpleTable
                rows={overview?.departments || []}
                columns={[
                  ["department_code", "部门编码"],
                  ["department_name", "部门名称"],
                  ["ticket_count", "小票数", number],
                  ["sales_amount", "销售额", money],
                  ["received_coupon_amount", "收券额", money],
                  ["net_profit", "净毛利", money],
                ]}
              />
            </TabsContent>
            <TabsContent value="products">
              <SimpleTable
                rows={overview?.products || []}
                columns={[
                  ["goods_code", "商品编码"],
                  ["goods_name", "商品名称"],
                  ["brand_code", "品牌"],
                  ["category_code", "品类"],
                  ["quantity", "数量", number],
                  ["sales_amount", "销售额", money],
                  ["net_profit", "净毛利", money],
                ]}
              />
            </TabsContent>
            <TabsContent value="members">
              <SimpleTable
                rows={overview?.members || []}
                columns={[
                  ["customer_level", "会员等级"],
                  ["regist_channel", "注册渠道"],
                  ["customer_status", "状态"],
                  ["member_count", "会员数", number],
                  ["ticket_count", "小票数", number],
                  ["sales_amount", "销售额", money],
                  ["net_profit", "净毛利", money],
                ]}
              />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

function SimpleTable({
  rows,
  columns,
}: {
  rows: Array<Record<string, unknown>>;
  columns: Array<[string, string, ((value: unknown) => string)?]>;
}) {
  return (
    <Card className="rounded-lg">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map(([key, label]) => (
                <TableHead key={key}>{label}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="py-10 text-center text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row, index) => (
                <TableRow key={index}>
                  {columns.map(([key, , formatter]) => (
                    <TableCell key={key} className={typeof row[key] === "number" ? "text-right tabular-nums" : ""}>
                      {formatter ? formatter(row[key]) : String(row[key] ?? "—")}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
