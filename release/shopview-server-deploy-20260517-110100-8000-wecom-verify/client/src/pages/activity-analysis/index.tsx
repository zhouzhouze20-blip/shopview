import { useEffect, useMemo, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BarChart3, ClipboardList, CreditCard, Eye, EyeOff, Loader2, RefreshCw, Search, TicketPercent, UserPlus, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";

type ActivityOption = {
  activity_id: string;
  activity_name: string;
  store_id?: number | string | null;
  store_code?: string | null;
  store_name?: string | null;
  start_date: string;
  end_date: string;
  ticket_count: number;
  card_log_amount: number;
  issued_log_amount: number;
  consumed_log_amount: number;
  coupon_pay_amount: number;
};

type ActivityOverview = {
  activity?: {
    activity_id: string;
    activity_name: string;
    store_id?: number | string | null;
    store_code?: string | null;
    store_name?: string | null;
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

type RowData = Record<string, number | string | null>;
type TableColumn = [string, string, ((value: unknown) => string)?, ((row: RowData) => ReactNode)?];

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

const fmtDate = (value: unknown) => (typeof value === "string" && value ? value.slice(0, 10) : "—");
const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 19) : "—");

const errorText = (error: unknown) => (error instanceof Error ? error.message : "请求失败");

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    qs.set(key, String(value));
  });
  const s = qs.toString();
  return s ? `?${s}` : "";
}

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
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
          <p className="mt-2 break-words text-2xl font-semibold leading-tight tabular-nums text-slate-900">{value}</p>
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
  const [startDate, setStartDate] = useState(() => localDateString());
  const [endDate, setEndDate] = useState("");
  const [analysisScope, setAnalysisScope] = useState<"activity" | "standalone" | "all">("activity");
  const [flowKeyword, setFlowKeyword] = useState("");
  const [issueType, setIssueType] = useState("unmatched_logs");
  const [activeTab, setActiveTab] = useState("coupon-summary");
  const [selectedGroup, setSelectedGroup] = useState<RowData | null>(null);
  const [selectedCoupon, setSelectedCoupon] = useState<RowData | null>(null);
  const [selectedCouponDepartment, setSelectedCouponDepartment] = useState<RowData | null>(null);
  const [selectedCouponGroup, setSelectedCouponGroup] = useState<RowData | null>(null);
  const [showReconciliationPanel, setShowReconciliationPanel] = useState(false);
  const [showReconciliationDetails, setShowReconciliationDetails] = useState(false);
  const couponDrillOpen = !!selectedCoupon;

  const activitiesQuery = useQuery<ActivityOption[]>({
    queryKey: ["/api/activity-analysis/activities", keyword, startDate, endDate],
    queryFn: () => apiGet(`/api/activity-analysis/activities${buildQuery({ keyword, start_date: startDate, end_date: endDate, limit: 120 })}`),
  });

  const activities = activitiesQuery.data || [];

  useEffect(() => {
    if (activitiesQuery.isSuccess && activities.length === 0 && activityId) {
      setActivityId("");
      return;
    }
    if (activities.length > 0 && (!activityId || !activities.some((item) => item.activity_id === activityId))) {
      setActivityId((activities.find((item) => Number(item.ticket_count || 0) > 0) || activities[0]).activity_id);
    }
  }, [activityId, activities, activitiesQuery.isSuccess]);

  const overviewQuery = useQuery<ActivityOverview>({
    queryKey: ["/api/activity-analysis/overview", activityId, analysisScope, startDate, endDate],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/overview${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          limit: 30,
        })}`,
      ),
    enabled: analysisScope !== "activity" || !!activityId,
  });

  const couponSummaryQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/coupon-summary", activityId, analysisScope, startDate, endDate],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-summary${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          limit: 100,
        })}`,
      ),
    enabled: analysisScope !== "activity" || !!activityId,
  });

  const couponFlowsQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/coupon-flows", activityId, analysisScope, startDate, endDate, flowKeyword],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-flows${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          keyword: flowKeyword,
          limit: 100,
        })}`,
      ),
    enabled: analysisScope !== "activity" || !!activityId,
  });

  const qualityIssuesQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/quality-issues", activityId, analysisScope, startDate, endDate, issueType],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/quality-issues${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          issue_type: issueType,
          limit: 100,
        })}`,
      ),
    enabled: analysisScope !== "activity" || !!activityId,
  });

  const groupTicketsQuery = useQuery<RowData[]>({
    queryKey: [
      "/api/activity-analysis/department-tickets",
      activityId,
      analysisScope,
      startDate,
      endDate,
      selectedGroup?.department_code,
      selectedGroup?.group_code,
    ],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/department-tickets${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          department_code: selectedGroup?.department_code,
          group_code: selectedGroup?.group_code,
          limit: 200,
        })}`,
      ),
    enabled: (analysisScope !== "activity" || !!activityId) && !!selectedGroup?.department_code && !!selectedGroup?.group_code,
  });

  const couponDepartmentsQuery = useQuery<RowData[]>({
    queryKey: [
      "/api/activity-analysis/coupon-type-departments",
      activityId,
      analysisScope,
      startDate,
      endDate,
      selectedCoupon?.coupon_type,
    ],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-type-departments${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          coupon_type: selectedCoupon?.coupon_type,
          limit: 100,
        })}`,
      ),
    enabled: (analysisScope !== "activity" || !!activityId) && !!selectedCoupon?.coupon_type,
  });

  const couponGroupsQuery = useQuery<RowData[]>({
    queryKey: [
      "/api/activity-analysis/coupon-type-departments",
      activityId,
      analysisScope,
      startDate,
      endDate,
      selectedCoupon?.coupon_type,
      selectedCouponDepartment?.department_code,
    ],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/coupon-type-departments${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          coupon_type: selectedCoupon?.coupon_type,
          department_code: selectedCouponDepartment?.department_code,
          limit: 100,
        })}`,
      ),
    enabled:
      (analysisScope !== "activity" || !!activityId) &&
      !!selectedCoupon?.coupon_type &&
      !!selectedCouponDepartment?.department_code,
  });

  const couponGroupTicketsQuery = useQuery<RowData[]>({
    queryKey: [
      "/api/activity-analysis/department-tickets",
      activityId,
      analysisScope,
      startDate,
      endDate,
      selectedCoupon?.coupon_type,
      selectedCouponGroup?.department_code,
      selectedCouponGroup?.group_code,
    ],
    queryFn: () =>
      apiGet(
        `/api/activity-analysis/department-tickets${buildQuery({
          activity_id: analysisScope === "activity" ? activityId : "",
          scope: analysisScope,
          start_date: startDate,
          end_date: endDate,
          coupon_type: selectedCoupon?.coupon_type,
          department_code: selectedCouponGroup?.department_code,
          group_code: selectedCouponGroup?.group_code,
          limit: 200,
        })}`,
      ),
    enabled:
      (analysisScope !== "activity" || !!activityId) &&
      !!selectedCoupon?.coupon_type &&
      !!selectedCouponGroup?.department_code &&
      !!selectedCouponGroup?.group_code,
  });

  const selectedActivity = useMemo(
    () => activities.find((item) => item.activity_id === activityId),
    [activities, activityId],
  );
  const overview = overviewQuery.data;
  const summary = overview?.summary || {};
  const quality = overview?.quality || {};

  const openQualityIssue = (type: string) => {
    setIssueType(type);
    setActiveTab("quality");
  };

  useEffect(() => {
    setSelectedGroup(null);
    setSelectedCoupon(null);
    setSelectedCouponDepartment(null);
    setSelectedCouponGroup(null);
  }, [activityId, analysisScope, startDate, endDate]);

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="space-y-4">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">活动分析</h1>
          <p className="mt-1 text-sm text-muted-foreground">一期聚焦卡券使用，销售、成本和毛利取销售汇总表。</p>
        </div>

        <Card className="rounded-lg">
          <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-12 lg:items-end">
          <div className="min-w-0 lg:col-span-2">
            <Label>分析范围</Label>
            <Select value={analysisScope} onValueChange={(value) => setAnalysisScope(value as "activity" | "standalone" | "all")}>
              <SelectTrigger className="mt-1 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="activity">活动档期券</SelectItem>
                <SelectItem value="standalone">非档期券</SelectItem>
                <SelectItem value="all">全部卡券</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-0 lg:col-span-2">
            <Label htmlFor="activity-start">开始日期</Label>
            <Input
              id="activity-start"
              className="mt-1"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>
          <div className="min-w-0 lg:col-span-2">
            <Label htmlFor="activity-end">结束日期</Label>
            <Input
              id="activity-end"
              className="mt-1"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </div>
          <div className="min-w-0 lg:col-span-3">
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
          <div className="min-w-0 sm:col-span-2 lg:col-span-2">
            <Label>活动档期</Label>
            <Select value={activityId} onValueChange={setActivityId} disabled={analysisScope !== "activity"}>
              <SelectTrigger className="mt-1 w-full overflow-hidden [&>span]:truncate">
                <SelectValue placeholder="选择活动" />
              </SelectTrigger>
              <SelectContent className="max-w-[min(760px,92vw)]">
                {activities.map((activity) => (
                  <SelectItem key={activity.activity_id} value={activity.activity_id} className="max-w-[min(720px,88vw)]">
                    <span className="block truncate">
                      {activity.activity_id}｜{activity.store_name ? `${activity.store_name}｜` : ""}{activity.activity_name}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              activitiesQuery.refetch();
              overviewQuery.refetch();
              couponSummaryQuery.refetch();
              couponFlowsQuery.refetch();
              qualityIssuesQuery.refetch();
            }}
            disabled={(analysisScope === "activity" && !activityId) || overviewQuery.isFetching || couponSummaryQuery.isFetching}
          >
            {overviewQuery.isFetching || couponSummaryQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
          </CardContent>
        </Card>
      </div>

      {analysisScope === "activity" && selectedActivity ? (
        <Card className="rounded-lg">
          <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{selectedActivity.activity_id}</Badge>
                {selectedActivity.store_name ? <Badge variant="secondary">{selectedActivity.store_name}</Badge> : null}
                <span className="font-medium text-slate-900">{selectedActivity.activity_name}</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                活动期：{fmtDate(selectedActivity.start_date)} 至 {fmtDate(selectedActivity.end_date)}
              </p>
            </div>
            <div className="text-sm text-muted-foreground">
              已关联小票 {number(selectedActivity.ticket_count)}，发券日志 {money(selectedActivity.issued_log_amount)}，用券日志 {money(selectedActivity.consumed_log_amount)}
            </div>
          </CardContent>
        </Card>
      ) : analysisScope !== "activity" ? (
        <Card className="rounded-lg">
          <CardContent className="p-4 text-sm text-muted-foreground">
            当前范围：{analysisScope === "standalone" ? "非档期发券/用券，不强行归属活动档期。" : "全部卡券流水，含活动档期券与非档期券。"}
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
          <CardContent className="p-4 text-sm text-red-700">{errorText(overviewQuery.error)}</CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <MetricCard title="活动销售额" value={money(summary.sales_amount)} subtitle={`小票 ${number(summary.ticket_count)} 笔`} icon={BarChart3} />
            <MetricCard title="本档新会员" value={number(summary.new_member_count)} subtitle="入会日期在活动期内" icon={UserPlus} />
            <MetricCard title="新会员销售" value={money(summary.new_member_sales_amount)} subtitle="本档新会员关联小票" icon={BarChart3} />
            <MetricCard title="实际卡券付款" value={money(summary.coupon_pay_amount)} subtitle={`经营结果以此为准`} icon={CreditCard} />
            <MetricCard title="券消费日志" value={money(summary.consumed_log_amount)} subtitle={`0500 ${money(summary.pay_0500_amount)} / 0580 ${money(summary.pay_0580_amount)}`} icon={TicketPercent} />
            <MetricCard title="会员人数" value={number(summary.member_count)} subtitle={`卡券日志 ${number(summary.card_log_count)} 条`} icon={Users} />
          </div>

          <div className="flex justify-end">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowReconciliationPanel((value) => !value)}
            >
              {showReconciliationPanel ? <EyeOff className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
              {showReconciliationPanel ? "隐藏核对与质量" : "显示核对与质量"}
            </Button>
          </div>

          {showReconciliationPanel ? (
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="rounded-lg lg:col-span-2">
                <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
                  <CardTitle className="text-base">卡券口径核对</CardTitle>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={() => setShowReconciliationDetails((value) => !value)}
                  >
                    {showReconciliationDetails ? <EyeOff className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
                    {showReconciliationDetails ? "隐藏辅助口径" : "显示辅助口径"}
                  </Button>
                </CardHeader>
                <CardContent className={cn("grid gap-3", showReconciliationDetails ? "sm:grid-cols-3" : "sm:grid-cols-2")}>
                  <div className="rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">发券日志</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.issued_log_amount)}</p>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">用券日志</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.consumed_log_amount)}</p>
                  </div>
                  <div className="rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">其他日志</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.other_log_amount)}</p>
                  </div>
                  {showReconciliationDetails ? (
                    <div className="rounded-md border p-3">
                      <p className="text-xs text-muted-foreground">日志发生合计</p>
                      <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.card_log_amount)}</p>
                    </div>
                  ) : null}
                  <div className="rounded-md border p-3">
                    <p className="text-xs text-muted-foreground">付款金额</p>
                    <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.coupon_pay_amount)}</p>
                  </div>
                  {showReconciliationDetails ? (
                    <div className="rounded-md border p-3">
                      <p className="text-xs text-muted-foreground">期间0500/0580付款</p>
                      <p className="mt-1 text-lg font-semibold tabular-nums">{money(summary.period_coupon_pay_amount)}</p>
                    </div>
                  ) : null}
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
                  <QualityRow label="原始日志" value={quality.raw_log_count} />
                  <QualityRow label="已关联小票日志" value={quality.matched_log_count} />
                  <QualityRow label="未关联日志" value={quality.unmatched_log_count} onClick={() => openQualityIssue("unmatched_logs")} />
                  <QualityRow
                    label="付款未匹配卡券流水"
                    value={quality.period_payment_without_log_count}
                    onClick={() => openQualityIssue("payments_without_logs")}
                  />
                </CardContent>
              </Card>
            </div>
          ) : null}

          <CouponDrillDialog
            open={couponDrillOpen}
            coupon={selectedCoupon}
            department={selectedCouponDepartment}
            group={selectedCouponGroup}
            departments={couponDepartmentsQuery.data || []}
            groups={couponGroupsQuery.data || []}
            tickets={couponGroupTicketsQuery.data || []}
            loading={couponDepartmentsQuery.isFetching || couponGroupsQuery.isFetching || couponGroupTicketsQuery.isFetching}
            error={couponDepartmentsQuery.error || couponGroupsQuery.error || couponGroupTicketsQuery.error}
            onOpenChange={(open) => {
              if (!open) {
                setSelectedCoupon(null);
                setSelectedCouponDepartment(null);
                setSelectedCouponGroup(null);
              }
            }}
            onDepartmentSelect={(row) => {
              setSelectedCouponDepartment(row);
              setSelectedCouponGroup(null);
            }}
            onGroupSelect={setSelectedCouponGroup}
            onBackToDepartments={() => {
              setSelectedCouponDepartment(null);
              setSelectedCouponGroup(null);
            }}
            onBackToGroups={() => setSelectedCouponGroup(null)}
          />

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="max-w-full overflow-x-auto">
              <TabsTrigger value="coupon-summary">卡券汇总</TabsTrigger>
              <TabsTrigger value="payments">付款方式</TabsTrigger>
              <TabsTrigger value="flows">卡券流水</TabsTrigger>
              <TabsTrigger value="departments">部门柜组</TabsTrigger>
              <TabsTrigger value="products">商品品牌</TabsTrigger>
              <TabsTrigger value="members">会员</TabsTrigger>
              <TabsTrigger value="quality">数据质量</TabsTrigger>
            </TabsList>

            <TabsContent value="coupon-summary">
              {couponSummaryQuery.isError ? (
                <ErrorCard message={errorText(couponSummaryQuery.error)} />
              ) : (
                <SimpleTable
                  rows={couponSummaryQuery.data || []}
                  columns={[
                    ["action_name", "动作"],
                    ["source_name", "来源"],
                    ["coupon_type", "券字母"],
                    ["first_flow_date", "开始日期", fmtDate],
                    ["last_flow_date", "结束日期", fmtDate],
                    ["flow_count", "流水数", number],
                    ["member_count", "会员数", number],
                    ["coupon_count", "券号数", number],
                    ["ticket_count", "小票数", number],
                    ["issued_log_amount", "发券金额", money],
                    ["consumed_log_amount", "用券金额", money],
                    ["flow_amount", "发生金额", money],
                    ["raw_flow_amount", "原始金额", money],
                    ["coupon_pay_amount", "付款金额", money],
                  ]}
                />
              )}
            </TabsContent>

            <TabsContent value="payments">
              <div className="space-y-4">
                <SimpleTable
                  rows={overview?.payment_methods || []}
                  columns={[
                    [
                      "__coupon_departments",
                      "部门使用",
                      undefined,
                      (row) => {
                        const active =
                          row.paycode === selectedCoupon?.paycode &&
                          row.payname === selectedCoupon?.payname &&
                          row.coupon_type === selectedCoupon?.coupon_type;
                        return (
                          <Button
                            type="button"
                            size="sm"
                            variant={active ? "default" : "outline"}
                            onClick={(event) => {
                              event.stopPropagation();
                              setSelectedCoupon(row);
                              setSelectedCouponDepartment(null);
                              setSelectedCouponGroup(null);
                            }}
                          >
                            看部门
                          </Button>
                        );
                      },
                    ],
                    ["paycode", "付款代码"],
                    ["payname", "付款名称"],
                    ["coupon_type", "券字母"],
                    ["payment_count", "付款笔数", number],
                    ["payment_amount", "付款金额", money],
                    ["issued_log_amount", "发券金额", money],
                    ["consumed_log_amount", "用券金额", money],
                  ]}
                  onRowClick={(row) => {
                    setSelectedCoupon(row);
                    setSelectedCouponDepartment(null);
                    setSelectedCouponGroup(null);
                  }}
                  rowClassName={(row) =>
                    row.paycode === selectedCoupon?.paycode &&
                    row.payname === selectedCoupon?.payname &&
                    row.coupon_type === selectedCoupon?.coupon_type
                      ? "bg-slate-100"
                      : ""
                  }
                />
              </div>
            </TabsContent>
            <TabsContent value="flows">
              <Card className="mb-4 rounded-lg">
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
                  <div className="w-full sm:w-80">
                    <Label htmlFor="flow-search">流水搜索</Label>
                    <Input
                      id="flow-search"
                      className="mt-1"
                      value={flowKeyword}
                      onChange={(event) => setFlowKeyword(event.target.value)}
                      placeholder="券号、会员、小票、流水"
                    />
                  </div>
                  <Button variant="outline" onClick={() => couponFlowsQuery.refetch()} disabled={couponFlowsQuery.isFetching}>
                    {couponFlowsQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                    查询
                  </Button>
                </CardContent>
              </Card>
              {couponFlowsQuery.isError ? (
                <ErrorCard message={errorText(couponFlowsQuery.error)} />
              ) : (
                <SimpleTable
                  rows={couponFlowsQuery.data || []}
                  columns={[
                    ["flow_date", "日期", fmtDate],
                    ["action_name", "摘要"],
                    ["source_name", "来源"],
                    ["member_no", "会员"],
                    ["coupon_no", "券号"],
                    ["flow_amount", "发生金额", money],
                    ["raw_flow_amount", "原始金额", money],
                    ["balance_amount", "余额", money],
                    ["billno", "小票"],
                    ["coupon_pay_amount", "付款金额", money],
                    ["sales_amount", "销售额", money],
                  ]}
                />
              )}
            </TabsContent>
            <TabsContent value="departments">
              <div className="space-y-4">
                {selectedGroup ? (
                  <div className="space-y-3">
                    <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-center sm:justify-between">
                      <h2 className="text-base font-semibold text-slate-900">
                        {String(selectedGroup.department_display || selectedGroup.department_name || "未归属部门")} / {String(selectedGroup.group_display || selectedGroup.group_name || "未归属柜组")} 小票
                      </h2>
                      <div className="flex items-center gap-2">
                        {groupTicketsQuery.isFetching ? (
                          <span className="flex items-center text-sm text-muted-foreground">
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            加载中
                          </span>
                        ) : null}
                        <Button type="button" variant="outline" size="sm" onClick={() => setSelectedGroup(null)}>
                          返回部门柜组
                        </Button>
                      </div>
                    </div>
                    {groupTicketsQuery.isError ? (
                      <ErrorCard message={errorText(groupTicketsQuery.error)} />
                    ) : (
                      <SimpleTable
                        rows={groupTicketsQuery.data || []}
                        columns={[
                          ["sale_time", "销售时间", fmtDateTime],
                          ["billno", "小票"],
                          ["member_no", "会员"],
                          ["sales_amount", "销售额", money],
                          ["allocated_coupon_pay_amount", "分摊卡券付款", money],
                          ["allocated_issued_log_amount", "分摊发券日志", money],
                          ["allocated_consumed_log_amount", "分摊用券日志", money],
                          ["net_profit", "净毛利", money],
                          ["pay_discount_amount", "不计收入折扣", money],
                          ["supplier_discount_amount", "供应商承担", money],
                          ["shop_discount_amount", "商场承担", money],
                          ["return_loss", "退损", money],
                          ["bill_department_count", "跨部门数", number],
                          ["bill_group_count", "跨柜组数", number],
                        ]}
                      />
                    )}
                  </div>
                ) : null}
                <SimpleTable
                  rows={overview?.departments || []}
                  columns={[
                    [
                      "__tickets",
                      "小票明细",
                      undefined,
                      (row) => {
                        const active = row.department_code === selectedGroup?.department_code && row.group_code === selectedGroup?.group_code;
                        return (
                          <Button
                            type="button"
                            size="sm"
                            variant={active ? "default" : "outline"}
                            onClick={(event) => {
                              event.stopPropagation();
                              setSelectedGroup(row);
                            }}
                          >
                            查看小票
                          </Button>
                        );
                      },
                    ],
                    ["department_display", "部门"],
                    ["group_display", "柜组"],
                    ["ticket_count", "小票数", number],
                    ["sales_amount", "销售额", money],
                    ["allocated_coupon_pay_amount", "分摊卡券付款", money],
                    ["allocated_issued_log_amount", "分摊发券日志", money],
                    ["allocated_consumed_log_amount", "分摊用券日志", money],
                    ["net_profit", "净毛利", money],
                    ["pay_discount_amount", "不计收入折扣", money],
                    ["supplier_discount_amount", "供应商承担", money],
                    ["shop_discount_amount", "商场承担", money],
                    ["cross_department_ticket_count", "跨部门票数", number],
                    ["cross_group_ticket_count", "跨柜组票数", number],
                  ]}
                  onRowClick={setSelectedGroup}
                  rowClassName={(row) =>
                    row.department_code === selectedGroup?.department_code && row.group_code === selectedGroup?.group_code
                      ? "bg-slate-100"
                      : ""
                  }
                />
              </div>
            </TabsContent>
            <TabsContent value="products">
              <SimpleTable
                rows={overview?.products || []}
                columns={[
                  ["goods_code", "商品编码"],
                  ["goods_name", "商品名称"],
                  ["brand_display", "品牌"],
                  ["category_display", "品类"],
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
            <TabsContent value="quality">
              <Card className="mb-4 rounded-lg">
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
                  <div className="w-full sm:w-80">
                    <Label>问题类型</Label>
                    <Select value={issueType} onValueChange={setIssueType}>
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="unmatched_logs">卡券日志无法关联小票</SelectItem>
                        <SelectItem value="payments_without_logs">付款未匹配卡券流水</SelectItem>
                        <SelectItem value="amount_mismatch">日志与付款金额不一致</SelectItem>
                        <SelectItem value="unassigned_activity">无活动档期归属</SelectItem>
                        <SelectItem value="missing_member">小票无会员号</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button variant="outline" onClick={() => qualityIssuesQuery.refetch()} disabled={qualityIssuesQuery.isFetching}>
                    {qualityIssuesQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                    刷新
                  </Button>
                </CardContent>
              </Card>
              {qualityIssuesQuery.isError ? (
                <ErrorCard message={errorText(qualityIssuesQuery.error)} />
              ) : (
                <SimpleTable
                  rows={qualityIssuesQuery.data || []}
                  columns={[
                    ["issue", "问题"],
                    ["flow_date", "日志日期", fmtDate],
                    ["sale_time", "销售时间", fmtDate],
                    ["billno", "小票"],
                    ["member_no", "会员"],
                    ["payment_rowno", "付款行", number],
                    ["payno", "付款卡号"],
                    ["batch", "付款流水"],
                    ["coupon_no", "券号"],
                    ["action_name", "动作"],
                    ["flow_amount", "日志金额", money],
                    ["raw_flow_amount", "原始金额", money],
                    ["payment_amount", "付款金额", money],
                    ["difference_amount", "差异", money],
                  ]}
                />
              )}
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <Card className="rounded-lg border-red-200 bg-red-50">
      <CardContent className="flex items-start gap-2 p-4 text-sm text-red-700">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{message}</span>
      </CardContent>
    </Card>
  );
}

function CouponDrillDialog({
  open,
  coupon,
  department,
  group,
  departments,
  groups,
  tickets,
  loading,
  error,
  onOpenChange,
  onDepartmentSelect,
  onGroupSelect,
  onBackToDepartments,
  onBackToGroups,
}: {
  open: boolean;
  coupon: RowData | null;
  department: RowData | null;
  group: RowData | null;
  departments: RowData[];
  groups: RowData[];
  tickets: RowData[];
  loading: boolean;
  error: unknown;
  onOpenChange: (open: boolean) => void;
  onDepartmentSelect: (row: RowData) => void;
  onGroupSelect: (row: RowData) => void;
  onBackToDepartments: () => void;
  onBackToGroups: () => void;
}) {
  const title = coupon
    ? `${String(coupon.paycode)} ${String(coupon.payname)} / 券字母 ${String(coupon.coupon_type)}`
    : "券使用";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="h-[88vh] max-h-[88vh] w-[94vw] max-w-[94vw] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex min-h-9 items-center justify-between gap-3">
            <div className="text-sm font-semibold text-slate-900">
              {group
                ? `${String(group.department_display || group.department_name)} / ${String(group.group_display || group.group_name)} 小票`
                : department
                  ? `${String(department.department_display || department.department_name)} 柜组使用`
                  : "部门使用"}
            </div>
            <div className="flex items-center gap-2">
              {loading ? (
                <span className="flex items-center text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  加载中
                </span>
              ) : null}
              {group ? (
                <Button type="button" size="sm" variant="outline" onClick={onBackToGroups}>
                  返回柜组
                </Button>
              ) : department ? (
                <Button type="button" size="sm" variant="outline" onClick={onBackToDepartments}>
                  返回部门
                </Button>
              ) : null}
            </div>
          </div>
          {error ? (
            <ErrorCard message={errorText(error)} />
          ) : group ? (
            <SimpleTable
              rows={tickets}
              columns={[
                ["sale_time", "销售时间", fmtDateTime],
                ["billno", "小票"],
                ["member_no", "会员"],
                ["sales_amount", "销售额", money],
                ["allocated_coupon_pay_amount", "分摊卡券付款", money],
                ["allocated_issued_log_amount", "分摊发券日志", money],
                ["allocated_consumed_log_amount", "分摊用券日志", money],
                ["net_profit", "净毛利", money],
                ["pay_discount_amount", "不计收入折扣", money],
                ["supplier_discount_amount", "供应商承担", money],
                ["shop_discount_amount", "商场承担", money],
                ["return_loss", "退损", money],
              ]}
            />
          ) : department ? (
            <SimpleTable
              rows={groups}
              columns={[
                [
                  "__tickets",
                  "小票明细",
                  undefined,
                  (row) => (
                    <Button type="button" size="sm" variant="outline" onClick={() => onGroupSelect(row)}>
                      查看小票
                    </Button>
                  ),
                ],
                ["group_display", "柜组"],
                ["ticket_count", "小票数", number],
                ["sales_amount", "销售额", money],
                ["allocated_coupon_pay_amount", "分摊卡券付款", money],
                ["allocated_issued_log_amount", "分摊发券日志", money],
                ["allocated_consumed_log_amount", "分摊用券日志", money],
                ["net_profit", "净毛利", money],
                ["pay_discount_amount", "不计收入折扣", money],
                ["supplier_discount_amount", "供应商承担", money],
                ["shop_discount_amount", "商场承担", money],
              ]}
              onRowClick={onGroupSelect}
            />
          ) : (
            <SimpleTable
              rows={departments}
              columns={[
                [
                  "__groups",
                  "柜组明细",
                  undefined,
                  (row) => (
                    <Button type="button" size="sm" variant="outline" onClick={() => onDepartmentSelect(row)}>
                      查看柜组
                    </Button>
                  ),
                ],
                ["department_display", "部门"],
                ["ticket_count", "小票数", number],
                ["sales_amount", "销售额", money],
                ["allocated_coupon_pay_amount", "分摊卡券付款", money],
                ["allocated_issued_log_amount", "分摊发券日志", money],
                ["allocated_consumed_log_amount", "分摊用券日志", money],
                ["net_profit", "净毛利", money],
                ["pay_discount_amount", "不计收入折扣", money],
                ["supplier_discount_amount", "供应商承担", money],
                ["shop_discount_amount", "商场承担", money],
              ]}
              onRowClick={onDepartmentSelect}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function QualityRow({ label, value, onClick }: { label: string; value: unknown; onClick?: () => void }) {
  const content = (
    <>
      <span>{label}</span>
      <span className="tabular-nums">{number(value)}</span>
    </>
  );

  if (!onClick) {
    return <div className="flex justify-between gap-4">{content}</div>;
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full justify-between gap-4 rounded-md px-1 py-1 text-left transition hover:bg-slate-100 hover:text-slate-900"
    >
      {content}
    </button>
  );
}

function SimpleTable({
  rows,
  columns,
  onRowClick,
  rowClassName,
}: {
  rows: Array<Record<string, unknown>>;
  columns: TableColumn[];
  onRowClick?: (row: RowData) => void;
  rowClassName?: (row: Record<string, unknown>) => string;
}) {
  return (
    <Card className="rounded-lg">
      <CardContent className="overflow-hidden p-0">
        <div className="w-full overflow-x-auto">
        <Table className="min-w-max">
          <TableHeader>
            <TableRow>
              {columns.map(([key, label, formatter]) => (
                <TableHead key={key} className={isNumericFormatter(formatter) ? "whitespace-nowrap text-right" : "whitespace-nowrap"}>
                  {label}
                </TableHead>
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
                <TableRow
                  key={index}
                  onClick={onRowClick ? () => onRowClick(row as RowData) : undefined}
                  className={cn(onRowClick ? "cursor-pointer hover:bg-slate-50" : "", rowClassName?.(row))}
                >
                  {columns.map(([key, , formatter, render]) => (
                    <TableCell
                      key={key}
                      className={cn(
                        "whitespace-nowrap",
                        isNumericFormatter(formatter) || typeof row[key] === "number" ? "text-right tabular-nums" : "",
                      )}
                    >
                      {render ? render(row as RowData) : formatter ? formatter(row[key]) : String(row[key] ?? "—")}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        </div>
      </CardContent>
    </Card>
  );
}

function isNumericFormatter(formatter?: (value: unknown) => string) {
  return formatter === money || formatter === number;
}
