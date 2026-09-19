import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarCheck2,
  ChevronRight,
  CircleDollarSign,
  Download,
  Gift,
  Loader2,
  RefreshCw,
  Search,
  ShoppingBag,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { apiGet } from "@/lib/api";
import {
  birthdayCouponStatusLabel,
  birthdayCouponAssetLabel,
  centerCouponGroupsForDepartment,
  exportBirthdayCouponWorkbook,
  maskBirthdayCouponMemberName,
  maskBirthdayCouponMemberNo,
} from "@/lib/birthday-coupon-analysis";
import type { BirthdayCouponReport, BirthdayCouponRow } from "@/lib/birthday-coupon-analysis";
import type { BirthdayCouponExportDetails } from "@/lib/birthday-coupon-analysis";
import { cn } from "@/lib/utils";

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));
const moneyDetailed = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value || 0));
const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));
const decimal = (value: unknown, digits = 2) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(Number(value || 0));
const percent = (value: unknown) => (value === null || value === undefined ? "—" : `${decimal(value, 2)}%`);
const fmtDate = (value: unknown) => (typeof value === "string" && value ? value.slice(0, 10) : "—");
const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 16) : "—");
const errorText = (error: unknown) => (error instanceof Error ? error.message : "请求失败");

function localMonth(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthOffset(offset: number) {
  const date = new Date();
  date.setDate(1);
  date.setMonth(date.getMonth() + offset);
  return localMonth(date);
}

function buildQuery(params: Record<string, string | number>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) search.set(key, String(value));
  return `?${search.toString()}`;
}

function MetricCard({
  title,
  value,
  note,
  icon: Icon,
  tone = "slate",
}: {
  title: string;
  value: string;
  note: string;
  icon: LucideIcon;
  tone?: "slate" | "violet" | "emerald" | "amber";
}) {
  const toneClass = {
    slate: "bg-slate-100 text-slate-700",
    violet: "bg-violet-100 text-violet-700",
    emerald: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
  }[tone];
  return (
    <Card className="rounded-lg">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-2 break-words text-2xl font-semibold leading-tight tabular-nums text-slate-900">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{note}</p>
        </div>
        <div className={cn("rounded-md p-2", toneClass)}><Icon className="h-5 w-5" /></div>
      </CardContent>
    </Card>
  );
}

function EmptyRow({ colSpan, children = "暂无数据" }: { colSpan: number; children?: ReactNode }) {
  return <TableRow><TableCell colSpan={colSpan} className="h-24 text-center text-muted-foreground">{children}</TableCell></TableRow>;
}

type CouponUsageResponse = { coupons: BirthdayCouponRow[]; flows: BirthdayCouponRow[] };
type LevelMembersResponse = { items: BirthdayCouponRow[]; total: number; limit: number; offset: number };
type MemberSalesResponse = { items: BirthdayCouponRow[]; summary: BirthdayCouponRow };
type CouponFollowupResponse = {
  period_month: string;
  history_window: { start_date: string; end_date: string; basis: string };
  summary: BirthdayCouponRow;
  items: BirthdayCouponRow[];
  total: number;
  limit: number;
  offset: number;
};
const LEVEL_MEMBER_PAGE_SIZE = 200;

export default function BirthdayCouponAnalysisPage() {
  const { toast } = useToast();
  const [couponType, setCouponType] = useState("L");
  const [startMonth, setStartMonth] = useState(() => monthOffset(-2));
  const [endMonth, setEndMonth] = useState(() => localMonth());
  const [memberKeyword, setMemberKeyword] = useState("");
  const [memberStatus, setMemberStatus] = useState("all");
  const [activeTab, setActiveTab] = useState("monthly");
  const [selectedLevelMonth, setSelectedLevelMonth] = useState(() => localMonth());
  const [selectedDepartment, setSelectedDepartment] = useState<BirthdayCouponRow | null>(null);
  const [selectedCouponMember, setSelectedCouponMember] = useState<BirthdayCouponRow | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<BirthdayCouponRow | null>(null);
  const [levelMemberKeywordDraft, setLevelMemberKeywordDraft] = useState("");
  const [levelMemberKeyword, setLevelMemberKeyword] = useState("");
  const [levelMemberOffset, setLevelMemberOffset] = useState(0);
  const [selectedLevelMember, setSelectedLevelMember] = useState<BirthdayCouponRow | null>(null);
  const [followupKeyword, setFollowupKeyword] = useState("");
  const [followupStatus, setFollowupStatus] = useState("ALL");
  const [exporting, setExporting] = useState(false);
  const invalidRange = startMonth > endMonth;

  const reportQuery = useQuery<BirthdayCouponReport>({
    queryKey: ["/api/activity-analysis/birthday-coupon/dashboard", couponType, startMonth, endMonth],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/dashboard${buildQuery({ coupon_type: couponType, start_month: startMonth, end_month: endMonth, detail_limit: 500 })}`),
    enabled: !invalidRange,
  });
  const report = reportQuery.data;
  const summary = report?.summary || {};
  const monthly = report?.monthly || [];
  const departments = report?.departments || [];
  const members = report?.members || [];
  const qualityIssues = report?.quality_issues || [];
  const couponName = String(report?.scope.coupon_name || (couponType === "C" ? "美妆券" : "中心生日券"));
  const couponLabel = `${couponType} ${couponName}`;
  const selectedGroups = report && selectedDepartment
    ? centerCouponGroupsForDepartment(report, selectedDepartment.department_code)
    : [];

  const memberLevelsQuery = useQuery<BirthdayCouponRow[]>({
    queryKey: ["/api/activity-analysis/birthday-coupon/member-levels", couponType, selectedLevelMonth],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/member-levels${buildQuery({ coupon_type: couponType, period_month: selectedLevelMonth })}`),
    enabled: Boolean(report) && activeTab === "levels" && !invalidRange && selectedLevelMonth >= startMonth && selectedLevelMonth <= endMonth,
  });

  const usageDetailsQuery = useQuery<CouponUsageResponse>({
    queryKey: ["/api/activity-analysis/birthday-coupon/usage-details", couponType, selectedCouponMember?.period_month, selectedCouponMember?.member_no],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/usage-details${buildQuery({
      coupon_type: couponType,
      period_month: String(selectedCouponMember?.period_month || "").slice(0, 7),
      member_no: String(selectedCouponMember?.member_no || ""),
    })}`),
    enabled: Boolean(selectedCouponMember),
  });

  const levelMembersQuery = useQuery<LevelMembersResponse>({
    queryKey: ["/api/activity-analysis/birthday-coupon/level-members", couponType, selectedLevelMonth, selectedLevel?.customer_level, levelMemberKeyword, levelMemberOffset],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/level-members${buildQuery({
      coupon_type: couponType,
      period_month: selectedLevelMonth,
      customer_level: String(selectedLevel?.customer_level || ""),
      keyword: levelMemberKeyword,
      limit: LEVEL_MEMBER_PAGE_SIZE,
      offset: levelMemberOffset,
    })}`),
    enabled: Boolean(selectedLevel),
  });

  const memberSalesQuery = useQuery<MemberSalesResponse>({
    queryKey: ["/api/activity-analysis/birthday-coupon/member-sales", couponType, selectedLevelMonth, selectedLevelMember?.member_no],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/member-sales${buildQuery({
      coupon_type: couponType,
      period_month: selectedLevelMonth,
      member_no: String(selectedLevelMember?.member_no || ""),
      limit: 500,
    })}`),
    enabled: Boolean(selectedLevelMember),
  });

  const followupsQuery = useQuery<CouponFollowupResponse>({
    queryKey: ["/api/activity-analysis/birthday-coupon/followups", selectedLevelMonth, followupStatus, followupKeyword],
    queryFn: () => apiGet(`/api/activity-analysis/birthday-coupon/followups${buildQuery({
      period_month: selectedLevelMonth,
      status_code: followupStatus,
      keyword: followupKeyword,
      limit: 5000,
      offset: 0,
    })}`),
    enabled: couponType === "C" && activeTab === "followups" && selectedLevelMonth >= startMonth && selectedLevelMonth <= endMonth,
  });

  const visibleMembers = useMemo(() => {
    const keyword = memberKeyword.trim().toLowerCase();
    return members.filter((row) => {
      const statusMatches = memberStatus === "all" || row.redemption_status === memberStatus;
      if (!statusMatches) return false;
      if (!keyword) return true;
      return [row.member_no, row.customer_level, birthdayCouponStatusLabel(row.redemption_status)]
        .some((value) => String(value || "").toLowerCase().includes(keyword));
    });
  }, [members, memberKeyword, memberStatus]);

  const monthlyChart = useMemo(() => monthly.map((row) => ({
    ...row,
    month: String(row.period_month || "").slice(0, 7),
  })), [monthly]);
  const dailyChart = useMemo(() => (report?.daily || []).map((row) => ({
    ...row,
    date: String(row.business_date || "").slice(5, 10),
  })), [report?.daily]);

  const issueVerified = Number(summary.issued_member_count || 0) > 0
    && Number(summary.off_schedule_issue_count || 0) === 0
    && Number(summary.duplicate_issue_count || 0) === 0
    && Number(summary.face_value_exception_count || 0) === 0;

  const exportReport = async () => {
    if (invalidRange) return;
    setExporting(true);
    try {
      const fullReport = await apiGet<BirthdayCouponReport>(
        `/api/activity-analysis/birthday-coupon/dashboard${buildQuery({ coupon_type: couponType, start_month: startMonth, end_month: endMonth, detail_limit: 50000 })}`,
      );
      const exportDetails = await apiGet<BirthdayCouponExportDetails>(
        `/api/activity-analysis/birthday-coupon/export-details${buildQuery({ coupon_type: couponType, start_month: startMonth, end_month: endMonth, detail_limit: 50000 })}`,
      );
      exportBirthdayCouponWorkbook(fullReport, exportDetails);
      const detailSections = [exportDetails.detail.level_members, exportDetails.detail.member_sales, exportDetails.detail.usage_flows, exportDetails.detail.followups]
        .filter((value): value is Record<string, unknown> => Boolean(value) && typeof value === "object");
      const exportTruncated = fullReport.detail.truncated || detailSections.some((value) => Boolean(value.truncated));
      toast({
        title: exportTruncated ? "报表已导出（明细有截断）" : "报表已导出",
        description: exportTruncated
          ? "部分明细达到50,000条上限，请缩小月份范围后分批导出。"
          : `包含 ${number(exportDetails.level_members.length)} 条会员月汇总、${number(exportDetails.member_sales.length)} 张消费小票、${number(exportDetails.usage_flows.length)} 条用券流水${couponType === "C" ? `、${number(exportDetails.followups.length)} 条跟进分配` : ""}`,
        variant: exportTruncated ? "destructive" : "default",
      });
    } catch (error) {
      toast({ title: "报表导出失败", description: errorText(error), variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-end 2xl:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">购物中心券分析</h1>
            <Badge variant="secondary">601 常州购物中心</Badge>
            <Badge className="bg-violet-100 text-violet-800 hover:bg-violet-100">{couponLabel}</Badge>
          </div>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            在L中心生日券与C美妆券之间切换，按发放批次观察每月1日发放、会员核销、过期沉淀和使用小票带动销售；部门可继续下钻到柜组。
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div>
            <Label>券种</Label>
            <Select value={couponType} onValueChange={(value) => {
              setCouponType(value);
              if (value !== "C" && activeTab === "followups") setActiveTab("monthly");
              setSelectedDepartment(null);
              setSelectedCouponMember(null);
              setSelectedLevel(null);
              setSelectedLevelMember(null);
            }}>
              <SelectTrigger className="mt-1 w-full sm:w-44"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="L">L 中心生日券</SelectItem>
                <SelectItem value="C">C 美妆券</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="birthday-coupon-start">开始月份</Label>
            <Input id="birthday-coupon-start" className="mt-1 w-full sm:w-40" type="month" value={startMonth} onChange={(event) => {
              const value = event.target.value;
              setStartMonth(value);
              if (selectedLevelMonth < value) setSelectedLevelMonth(value);
              setSelectedLevel(null);
            }} />
          </div>
          <div>
            <Label htmlFor="birthday-coupon-end">结束月份</Label>
            <Input id="birthday-coupon-end" className="mt-1 w-full sm:w-40" type="month" value={endMonth} onChange={(event) => {
              const value = event.target.value;
              setEndMonth(value);
              setSelectedLevelMonth(value);
              setSelectedLevel(null);
            }} />
          </div>
          <Button variant="outline" onClick={() => reportQuery.refetch()} disabled={reportQuery.isFetching || invalidRange}>
            {reportQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
          <Button onClick={exportReport} disabled={!report || exporting || invalidRange}>
            {exporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            导出分析报表
          </Button>
        </div>
      </div>

      {invalidRange ? (
        <Card className="border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">开始月份不能晚于结束月份。</CardContent></Card>
      ) : null}
      {reportQuery.isError ? (
        <Card className="border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">{errorText(reportQuery.error)}</CardContent></Card>
      ) : null}
      {reportQuery.isLoading ? (
        <Card><CardContent className="flex items-center justify-center gap-2 py-20 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在汇总中心券数据…</CardContent></Card>
      ) : null}

      {report ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <MetricCard title="发放会员人次" value={number(summary.issued_member_count)} note={`发放金额 ${money(summary.issued_amount)}`} icon={Gift} tone="violet" />
            <MetricCard title="净核销会员人次" value={number(summary.net_redeemed_member_count)} note={`会员核销率 ${percent(summary.member_redemption_rate)}`} icon={Users} tone="emerald" />
            <MetricCard title="净核销金额" value={money(summary.net_redeemed_amount)} note={`金额核销率 ${percent(summary.amount_redemption_rate)}`} icon={CircleDollarSign} tone="emerald" />
            <MetricCard title="带动销售额" value={money(summary.driven_sales_amount)} note={`销售带动 ${decimal(summary.sales_leverage)} 倍`} icon={ShoppingBag} tone="slate" />
            <MetricCard title="未使用金额" value={money(summary.unused_amount)} note={`其中已过期 ${money(summary.expired_unused_amount)}`} icon={CalendarCheck2} tone="amber" />
            <MetricCard title="发放异常" value={number(qualityIssues.reduce((sum, row) => sum + Number(row.issue_count || 0), 0))} note={`${qualityIssues.length} 类月度异常`} icon={AlertTriangle} tone={qualityIssues.length ? "amber" : "slate"} />
          </div>

          <Card className={cn("rounded-lg", issueVerified ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50")}>
            <CardContent className="flex flex-col gap-2 p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className={cn("font-medium", issueVerified ? "text-emerald-800" : "text-amber-900")}>
                  {issueVerified
                    ? `当前筛选范围内，${couponType}券均为每月1日发放、单张${number(report.scope.expected_face_value)}元、每位会员${number(report.scope.expected_issue_count_per_member)}张。`
                    : "发放批次存在需核对项目，请查看“异常核对”。"}
                </p>
                <p className="mt-1 text-muted-foreground">
                  源数据最新日 {fmtDate(report.source.latest_data_date)}；发放日志覆盖起点 {fmtDate(report.source.issue_coverage_start)}；动作码 M。
                </p>
              </div>
              <Badge variant="outline" className="w-fit bg-white">数据按所选券种有效期起始月归批次</Badge>
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="rounded-lg">
              <CardHeader><CardTitle className="text-base">月度发放与会员核销率</CardTitle></CardHeader>
              <CardContent className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={monthlyChart} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis yAxisId="count" tick={{ fontSize: 12 }} tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`} />
                    <YAxis yAxisId="rate" orientation="right" domain={[0, "auto"]} tick={{ fontSize: 12 }} tickFormatter={(value) => `${value}%`} />
                    <Tooltip formatter={(value, name) => [name === "会员核销率" ? `${decimal(value)}%` : number(value), name]} />
                    <Legend />
                    <Bar yAxisId="count" dataKey="issued_member_count" name="发放会员人次" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    <Bar yAxisId="count" dataKey="net_redeemed_member_count" name="净核销会员人次" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Line yAxisId="rate" dataKey="member_redemption_rate" name="会员核销率" stroke="#f59e0b" strokeWidth={2.5} dot={{ r: 4 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="rounded-lg">
              <CardHeader><CardTitle className="text-base">每日净核销走势</CardTitle></CardHeader>
              <CardContent className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={dailyChart} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `¥${Number(value).toLocaleString()}`} />
                    <Tooltip formatter={(value, name) => [name === "核销会员" ? number(value) : money(value), name]} />
                    <Legend />
                    <Bar dataKey="net_redeemed_amount" name="净核销金额" fill="#7c3aed" radius={[3, 3, 0, 0]} />
                    <Line dataKey="redeemed_member_count" name="核销会员" stroke="#0f766e" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
            <TabsList className="h-auto flex-wrap justify-start">
              <TabsTrigger value="monthly">月度汇总</TabsTrigger>
              <TabsTrigger value="departments">部门带动</TabsTrigger>
              <TabsTrigger value="members">会员明细</TabsTrigger>
              <TabsTrigger value="levels">会员级别汇总</TabsTrigger>
              {couponType === "C" ? <TabsTrigger value="followups">会员跟进分配</TabsTrigger> : null}
              <TabsTrigger value="quality">异常核对</TabsTrigger>
            </TabsList>

            <TabsContent value="monthly">
              <Card className="rounded-lg"><CardContent className="p-0"><div className="overflow-x-auto"><Table className="min-w-[1180px]">
                <TableHeader><TableRow>
                  <TableHead className="whitespace-nowrap">发放月</TableHead><TableHead className="whitespace-nowrap text-right">发放会员人次</TableHead><TableHead className="whitespace-nowrap text-right">发放金额</TableHead>
                  <TableHead className="whitespace-nowrap text-right">净核销会员人次</TableHead><TableHead className="whitespace-nowrap text-right">会员核销率</TableHead><TableHead className="whitespace-nowrap text-right">净核销金额</TableHead>
                  <TableHead className="whitespace-nowrap text-right">未使用金额</TableHead><TableHead className="whitespace-nowrap text-right">已过期未使用</TableHead><TableHead className="whitespace-nowrap">有效期</TableHead><TableHead className="whitespace-nowrap">状态</TableHead>
                </TableRow></TableHeader>
                <TableBody>{monthly.length ? monthly.map((row) => <TableRow key={String(row.period_month)}>
                  <TableCell className="font-medium">{String(row.period_month).slice(0, 7)}</TableCell>
                  <TableCell className="text-right tabular-nums">{number(row.issued_member_count)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.issued_amount)}</TableCell>
                  <TableCell className="text-right tabular-nums">{number(row.net_redeemed_member_count)}</TableCell>
                  <TableCell className="text-right tabular-nums">{percent(row.member_redemption_rate)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.net_redeemed_amount)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.unused_amount)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.expired_unused_amount)}</TableCell>
                  <TableCell className="whitespace-nowrap">{fmtDate(row.valid_from)} 至 {fmtDate(row.valid_to)}</TableCell>
                  <TableCell><Badge variant={row.cohort_status === "EXPIRED" ? "outline" : "secondary"}>{row.cohort_status === "EXPIRED" ? "已到期" : "有效期内"}</Badge></TableCell>
                </TableRow>) : <EmptyRow colSpan={10} />}</TableBody>
              </Table></div></CardContent></Card>
            </TabsContent>

            <TabsContent value="departments">
              <Card className="rounded-lg"><CardHeader><CardTitle className="text-base">{couponType}券使用小票带动销售（按部门，点击查看柜组）</CardTitle></CardHeader><CardContent className="p-0"><div className="overflow-x-auto"><Table className="min-w-[900px]">
                <TableHeader><TableRow><TableHead>部门</TableHead><TableHead className="text-right">小票数</TableHead><TableHead className="text-right">带动销售额</TableHead><TableHead className="text-right">分摊{couponType}券金额</TableHead><TableHead className="text-right">销售带动倍数</TableHead><TableHead className="text-right">销售毛利</TableHead><TableHead className="text-right">毛利率</TableHead><TableHead className="w-12" /></TableRow></TableHeader>
                <TableBody>{departments.length ? departments.map((row) => <TableRow
                  key={String(row.department_code)}
                  role="button"
                  tabIndex={0}
                  className="cursor-pointer hover:bg-violet-50"
                  onClick={() => setSelectedDepartment(row)}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelectedDepartment(row); }}
                >
                  <TableCell><p className="font-medium">{String(row.department_name || "未归属部门")}</p><p className="text-xs text-muted-foreground">{String(row.department_code || "—")}</p></TableCell>
                  <TableCell className="text-right tabular-nums">{number(row.ticket_count)}</TableCell><TableCell className="text-right tabular-nums">{money(row.driven_sales_amount)}</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.allocated_coupon_amount)}</TableCell><TableCell className="text-right tabular-nums">{decimal(row.sales_leverage)} 倍</TableCell>
                  <TableCell className="text-right tabular-nums">{money(row.gross_profit)}</TableCell><TableCell className="text-right tabular-nums">{percent(row.gross_margin_rate)}</TableCell>
                  <TableCell><ChevronRight className="h-4 w-4 text-muted-foreground" /></TableCell>
                </TableRow>) : <EmptyRow colSpan={8} />}</TableBody>
              </Table></div></CardContent></Card>
            </TabsContent>

            <TabsContent value="members" className="space-y-3">
              <Card className="rounded-lg"><CardContent className="grid gap-3 p-4 md:grid-cols-[minmax(0,1fr)_220px_auto] md:items-end">
                <div><Label htmlFor="birthday-member-search">会员卡号/等级/状态</Label><div className="relative mt-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><Input id="birthday-member-search" value={memberKeyword} onChange={(event) => setMemberKeyword(event.target.value)} className="pl-9" placeholder="搜索当前页面明细" /></div></div>
                <div><Label>核销状态</Label><Select value={memberStatus} onValueChange={setMemberStatus}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">全部状态</SelectItem><SelectItem value="REDEEMED">已核销</SelectItem><SelectItem value="UNUSED">有效期内未用</SelectItem><SelectItem value="EXPIRED_UNUSED">已过期未用</SelectItem></SelectContent></Select></div>
                <p className="pb-2 text-xs text-muted-foreground">页面 {number(visibleMembers.length)} 条；{report.detail.truncated ? "导出将重新获取最多 50,000 条" : "已显示全部"}</p>
              </CardContent></Card>
              <Card className="rounded-lg"><CardContent className="p-0"><div className="max-h-[560px] overflow-auto"><Table className="min-w-[1320px]">
                <TableHeader className="sticky top-0 z-10 bg-white"><TableRow><TableHead>发放月</TableHead><TableHead>会员卡号</TableHead><TableHead>会员等级</TableHead><TableHead>发放日</TableHead><TableHead className="text-right">发放金额</TableHead><TableHead>首次核销</TableHead><TableHead className="text-right">净核销</TableHead><TableHead className="text-right">未使用</TableHead><TableHead>状态</TableHead><TableHead>异常</TableHead><TableHead className="w-12" /></TableRow></TableHeader>
                <TableBody>{visibleMembers.length ? visibleMembers.map((row, index) => <TableRow
                  key={`${row.period_month}-${row.member_no}-${index}`}
                  role="button"
                  tabIndex={0}
                  className="cursor-pointer hover:bg-violet-50"
                  onClick={() => setSelectedCouponMember(row)}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelectedCouponMember(row); }}
                >
                  <TableCell>{String(row.period_month).slice(0, 7)}</TableCell><TableCell className="font-mono text-xs">{maskBirthdayCouponMemberNo(row.member_no)}</TableCell>
                  <TableCell>{String(row.customer_level || "未识别")}</TableCell><TableCell>{fmtDate(row.issue_date)}</TableCell><TableCell className="text-right tabular-nums">{money(row.issued_amount)}</TableCell>
                  <TableCell>{fmtDate(row.first_redeem_date)}</TableCell><TableCell className="text-right tabular-nums">{money(row.net_redeemed_amount)}</TableCell><TableCell className="text-right tabular-nums">{money(row.unused_amount)}</TableCell>
                  <TableCell><Badge variant={row.redemption_status === "REDEEMED" ? "secondary" : "outline"}>{birthdayCouponStatusLabel(row.redemption_status)}</Badge></TableCell>
                  <TableCell>{row.duplicate_issue ? <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">超额发放</Badge> : "—"}</TableCell>
                  <TableCell><ChevronRight className="h-4 w-4 text-muted-foreground" /></TableCell>
                </TableRow>) : <EmptyRow colSpan={11} />}</TableBody>
              </Table></div></CardContent></Card>
            </TabsContent>

            <TabsContent value="levels" className="space-y-3">
              <Card className="rounded-lg">
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <Label>发放月</Label>
                    <Select value={selectedLevelMonth} onValueChange={(value) => {
                      setSelectedLevelMonth(value);
                      setSelectedLevel(null);
                      setSelectedLevelMember(null);
                      setLevelMemberOffset(0);
                    }}>
                      <SelectTrigger className="mt-1 w-full sm:w-44"><SelectValue /></SelectTrigger>
                      <SelectContent>{monthly.map((row) => {
                        const value = String(row.period_month || "").slice(0, 7);
                        return <SelectItem key={value} value={value}>{value}</SelectItem>;
                      })}</SelectContent>
                    </Select>
                  </div>
                  <p className="text-sm text-muted-foreground">汇总当月领取{couponType}券的会员；点击会员级别查看会员及整月消费金额。</p>
                </CardContent>
              </Card>
              {memberLevelsQuery.isLoading ? (
                <Card><CardContent className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在汇总会员级别与月消费…</CardContent></Card>
              ) : memberLevelsQuery.isError ? (
                <Card className="border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">{errorText(memberLevelsQuery.error)}</CardContent></Card>
              ) : (
                <Card className="rounded-lg"><CardContent className="p-0"><div className="overflow-x-auto"><Table className="min-w-[1120px]">
                  <TableHeader><TableRow>
                    <TableHead>会员级别</TableHead><TableHead className="text-right">领券会员</TableHead><TableHead className="text-right">发放金额</TableHead>
                    <TableHead className="text-right">净核销会员</TableHead><TableHead className="text-right">净核销金额</TableHead><TableHead className="text-right">当月消费会员</TableHead>
                    <TableHead className="text-right">当月小票</TableHead><TableHead className="text-right">当月消费金额</TableHead><TableHead className="w-12" />
                  </TableRow></TableHeader>
                  <TableBody>{memberLevelsQuery.data?.length ? memberLevelsQuery.data.map((row) => <TableRow
                    key={String(row.customer_level)}
                    role="button"
                    tabIndex={0}
                    className="cursor-pointer hover:bg-violet-50"
                    onClick={() => { setSelectedLevel(row); setLevelMemberOffset(0); setLevelMemberKeyword(""); setLevelMemberKeywordDraft(""); }}
                    onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { setSelectedLevel(row); setLevelMemberOffset(0); } }}
                  >
                    <TableCell className="font-medium">{String(row.customer_level || "未识别")}</TableCell>
                    <TableCell className="text-right tabular-nums">{number(row.issued_member_count)}</TableCell><TableCell className="text-right tabular-nums">{money(row.issued_amount)}</TableCell>
                    <TableCell className="text-right tabular-nums">{number(row.redeemed_member_count)}</TableCell><TableCell className="text-right tabular-nums">{money(row.net_redeemed_amount)}</TableCell>
                    <TableCell className="text-right tabular-nums">{number(row.consuming_member_count)}</TableCell><TableCell className="text-right tabular-nums">{number(row.ticket_count)}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">{moneyDetailed(row.monthly_sales_amount)}</TableCell><TableCell><ChevronRight className="h-4 w-4 text-muted-foreground" /></TableCell>
                  </TableRow>) : <EmptyRow colSpan={9}>该月暂无会员级别数据</EmptyRow>}</TableBody>
                </Table></div></CardContent></Card>
              )}
            </TabsContent>

            <TabsContent value="followups" className="space-y-3">
              <Card className="rounded-lg">
                <CardContent className="grid gap-3 p-4 lg:grid-cols-[180px_minmax(260px,1fr)_220px] lg:items-end">
                  <div>
                    <Label>发放月</Label>
                    <Select value={selectedLevelMonth} onValueChange={setSelectedLevelMonth}>
                      <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                      <SelectContent>{monthly.map((row) => {
                        const value = String(row.period_month || "").slice(0, 7);
                        return <SelectItem key={value} value={value}>{value}</SelectItem>;
                      })}</SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="coupon-followup-search">会员 / 品牌柜组 / 品类主管</Label>
                    <div className="relative mt-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><Input id="coupon-followup-search" className="pl-9" value={followupKeyword} onChange={(event) => setFollowupKeyword(event.target.value)} placeholder="搜索跟进分配" /></div>
                  </div>
                  <div>
                    <Label>跟进状态</Label>
                    <Select value={followupStatus} onValueChange={setFollowupStatus}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent>
                      <SelectItem value="ALL">全部状态</SelectItem><SelectItem value="NOT_VISITED">未到店</SelectItem><SelectItem value="VISITED_NOT_REDEEMED">已到店未用券</SelectItem>
                      <SelectItem value="REDEEMED">已用券</SelectItem><SelectItem value="REDEEMED_RETURNED">用券后已退</SelectItem><SelectItem value="UNASSIGNED_BRAND">待分配品牌</SelectItem><SelectItem value="UNASSIGNED_MANAGER">待分配品类主管</SelectItem>
                    </SelectContent></Select>
                  </div>
                </CardContent>
              </Card>
              <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm leading-6 text-violet-900">
                仅纳入当月领取C券的黑金、黑钻会员。主跟进品牌按发券月前12个月在601店正向净消费金额最高的柜组自动确定，金额相同时取最近消费柜组；再按“品类主管绩效”中当前有效的品牌负责人分配。
              </div>
              {followupsQuery.data ? <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                <MetricCard title="目标会员" value={number(followupsQuery.data.summary.target_member_count)} note="黑金+黑钻" icon={Users} />
                <MetricCard title="已分品牌" value={number(followupsQuery.data.summary.assigned_brand_count)} note="历史主消费柜组" icon={ShoppingBag} tone="violet" />
                <MetricCard title="已分主管" value={number(followupsQuery.data.summary.assigned_manager_count)} note="现行负责人关系" icon={Users} tone="emerald" />
                <MetricCard title="已到店" value={number(followupsQuery.data.summary.visited_member_count)} note="当月正向消费" icon={CalendarCheck2} tone="amber" />
                <MetricCard title="已用券" value={number(followupsQuery.data.summary.redeemed_member_count)} note="C券净核销大于0" icon={Gift} tone="violet" />
                <MetricCard title="待补负责人" value={number(followupsQuery.data.summary.unassigned_manager_count)} note="先维护品牌主管" icon={AlertTriangle} tone="amber" />
              </div> : null}
              {followupsQuery.isLoading ? (
                <Card><CardContent className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在生成品牌与品类主管跟进清单…</CardContent></Card>
              ) : followupsQuery.isError ? (
                <Card className="border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">{errorText(followupsQuery.error)}</CardContent></Card>
              ) : (
                <Card className="rounded-lg"><CardContent className="p-0"><div className="max-h-[620px] overflow-auto"><Table className="min-w-[1500px]">
                  <TableHeader className="sticky top-0 z-10 bg-white"><TableRow><TableHead>会员</TableHead><TableHead>级别</TableHead><TableHead>跟进品牌柜组</TableHead><TableHead>部门</TableHead><TableHead>品类主管</TableHead><TableHead className="text-right">历史12月消费</TableHead><TableHead className="text-right">历史小票</TableHead><TableHead className="text-right">当月消费</TableHead><TableHead className="text-right">当月小票</TableHead><TableHead className="text-right">C券净核销</TableHead><TableHead>状态</TableHead></TableRow></TableHeader>
                  <TableBody>{followupsQuery.data?.items.length ? followupsQuery.data.items.map((row) => <TableRow key={String(row.member_no)}>
                    <TableCell><p className="font-mono text-xs">{String(row.masked_member_no || "—")}</p><p className="mt-1 text-xs text-muted-foreground">{String(row.masked_customer_name || "—")}</p></TableCell>
                    <TableCell>{String(row.customer_level || "—")}</TableCell><TableCell><p className="font-medium">{String(row.followup_group_name || "待分配")}</p><p className="text-xs text-muted-foreground">{String(row.followup_group_code || "—")}</p></TableCell>
                    <TableCell>{String(row.department_name || "—")}</TableCell><TableCell className={row.manager_name ? "font-medium" : "text-amber-700"}>{String(row.manager_name || "待维护")}</TableCell>
                    <TableCell className="text-right tabular-nums">{moneyDetailed(row.history_sales_amount)}</TableCell><TableCell className="text-right tabular-nums">{number(row.history_ticket_count)}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">{moneyDetailed(row.current_sales_amount)}</TableCell><TableCell className="text-right tabular-nums">{number(row.current_ticket_count)}</TableCell>
                    <TableCell className="text-right tabular-nums">{moneyDetailed(row.net_redeemed_amount)}</TableCell><TableCell><Badge variant={row.followup_status === "REDEEMED" ? "secondary" : "outline"}>{String(row.followup_status_label || "待核对")}</Badge></TableCell>
                  </TableRow>) : <EmptyRow colSpan={11}>没有符合条件的跟进会员</EmptyRow>}</TableBody>
                </Table></div><div className="border-t px-4 py-3 text-xs text-muted-foreground">当前条件共 {number(followupsQuery.data?.total || 0)} 位。未维护品类主管的品牌，请先到“销售管理 → 品类主管绩效”补充负责人。</div></CardContent></Card>
              )}
            </TabsContent>

            <TabsContent value="quality">
              <Card className="rounded-lg"><CardHeader><CardTitle className="text-base">发放批次异常</CardTitle></CardHeader><CardContent className="space-y-4">
                <div className="rounded-md border bg-slate-50 p-3 text-sm text-slate-700">
                  系统核对四类问题：非每月1日发放、超过每人标准张数（L券1张/C券2张）、单笔面值不是100元、发放日志缺会员号。历史月份若只有核销没有发放，也会提示发放批次缺失。
                </div>
                <div className="overflow-x-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead>月份</TableHead><TableHead>问题编码</TableHead><TableHead>问题</TableHead><TableHead className="text-right">数量</TableHead></TableRow></TableHeader>
                  <TableBody>{qualityIssues.length ? qualityIssues.map((row, index) => <TableRow key={`${row.period_month}-${row.issue_code}-${index}`}><TableCell>{String(row.period_month || "—")}</TableCell><TableCell className="font-mono text-xs">{String(row.issue_code || "—")}</TableCell><TableCell>{String(row.issue_name || "—")}</TableCell><TableCell className="text-right tabular-nums font-medium text-amber-700">{number(row.issue_count)}</TableCell></TableRow>) : <EmptyRow colSpan={4}>当前筛选范围未发现发放批次异常</EmptyRow>}</TableBody>
                </Table></div>
              </CardContent></Card>
            </TabsContent>
          </Tabs>

          <Dialog open={Boolean(selectedDepartment)} onOpenChange={(open) => !open && setSelectedDepartment(null)}>
            <DialogContent className="max-h-[88vh] w-[96vw] max-w-6xl overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{String(selectedDepartment?.department_name || "部门")} · {couponType}券使用柜组</DialogTitle>
                <p className="text-sm text-muted-foreground">
                  部门编码 {String(selectedDepartment?.department_code || "—")}；共 {number(selectedGroups.length)} 个使用柜组。券金额按同一小票各柜组销售额比例分摊。
                </p>
              </DialogHeader>
              <div className="overflow-x-auto rounded-lg border">
                <Table className="min-w-[980px]">
                  <TableHeader><TableRow>
                    <TableHead>柜组</TableHead><TableHead className="text-right">小票数</TableHead><TableHead className="text-right">带动销售额</TableHead>
                    <TableHead className="text-right">分摊{couponType}券金额</TableHead><TableHead className="text-right">销售带动倍数</TableHead>
                    <TableHead className="text-right">销售毛利</TableHead><TableHead className="text-right">毛利率</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>{selectedGroups.length ? selectedGroups.map((row) => <TableRow key={`${row.department_code}-${row.group_code}`}>
                    <TableCell><p className="font-medium">{String(row.group_name || "未归属柜组")}</p><p className="text-xs text-muted-foreground">{String(row.group_code || "—")}</p></TableCell>
                    <TableCell className="text-right tabular-nums">{number(row.ticket_count)}</TableCell><TableCell className="text-right tabular-nums">{money(row.driven_sales_amount)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.allocated_coupon_amount)}</TableCell><TableCell className="text-right tabular-nums">{decimal(row.sales_leverage)} 倍</TableCell>
                    <TableCell className="text-right tabular-nums">{money(row.gross_profit)}</TableCell><TableCell className="text-right tabular-nums">{percent(row.gross_margin_rate)}</TableCell>
                  </TableRow>) : <EmptyRow colSpan={7}>该部门暂未匹配到使用柜组</EmptyRow>}</TableBody>
                </Table>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={Boolean(selectedCouponMember)} onOpenChange={(open) => !open && setSelectedCouponMember(null)}>
            <DialogContent className="max-h-[90vh] w-[96vw] max-w-6xl overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{String(selectedCouponMember?.period_month || "").slice(0, 7)} · {maskBirthdayCouponMemberNo(selectedCouponMember?.member_no)} · 用券明细</DialogTitle>
                <p className="text-sm text-muted-foreground">按券资产序号精确关联该行所含的每张{couponType}券及后续核销、退券、冲正流水。</p>
              </DialogHeader>
              {usageDetailsQuery.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在读取用券流水…</div>
              ) : usageDetailsQuery.isError ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{errorText(usageDetailsQuery.error)}</div>
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {(usageDetailsQuery.data?.coupons || []).map((row, index) => <div key={String(row.coupon_asset_id || index)} className="rounded-lg border bg-slate-50 p-3">
                      <p className="font-medium">{birthdayCouponAssetLabel(row.coupon_no, row.coupon_asset_id, index)}</p>
                      <p className="mt-1 text-sm text-muted-foreground">发放 {fmtDate(row.issue_date)} · 面额 {money(row.issued_amount)}</p>
                      <p className="mt-1 text-xs text-muted-foreground">有效期 {fmtDate(row.valid_from)} 至 {fmtDate(row.valid_to)}</p>
                    </div>)}
                  </div>
                  <div className="overflow-x-auto rounded-lg border"><Table className="min-w-[1180px]">
                    <TableHeader><TableRow><TableHead>券</TableHead><TableHead>发生日</TableHead><TableHead>动作</TableHead><TableHead className="text-right">发生金额</TableHead><TableHead className="text-right">券后余额</TableHead><TableHead>销售时间</TableHead><TableHead>业务单号</TableHead><TableHead>收银机/小票</TableHead><TableHead>消费柜组</TableHead><TableHead className="text-right">小票销售额</TableHead></TableRow></TableHeader>
                    <TableBody>{usageDetailsQuery.data?.flows.length ? usageDetailsQuery.data.flows.map((row, index) => <TableRow key={String(row.flow_id || index)}>
                      <TableCell className="font-mono text-xs">{birthdayCouponAssetLabel(row.coupon_no, row.coupon_asset_id, index)}</TableCell><TableCell>{fmtDate(row.flow_date)}</TableCell>
                      <TableCell><Badge variant={row.action_code === "O" ? "secondary" : "outline"}>{String(row.action_name || row.action_code || "—")}</Badge></TableCell>
                      <TableCell className="text-right tabular-nums">{moneyDetailed(row.flow_amount)}</TableCell><TableCell className="text-right tabular-nums">{moneyDetailed(row.balance_amount)}</TableCell>
                      <TableCell>{fmtDateTime(row.sale_time)}</TableCell><TableCell className="font-mono text-xs">{String(row.billno || "—")}</TableCell><TableCell>{String(row.cashier_no || "—")} / {String(row.invoice_no || "—")}</TableCell><TableCell className="max-w-[240px] whitespace-normal">{String(row.group_names || "未归属柜组")}</TableCell>
                      <TableCell className="text-right tabular-nums">{moneyDetailed(row.sales_amount)}</TableCell>
                    </TableRow>) : <EmptyRow colSpan={10}>该券尚无核销、退券或冲正流水</EmptyRow>}</TableBody>
                  </Table></div>
                </div>
              )}
            </DialogContent>
          </Dialog>

          <Dialog open={Boolean(selectedLevel)} onOpenChange={(open) => {
            if (!open) {
              setSelectedLevel(null);
              setSelectedLevelMember(null);
            }
          }}>
            <DialogContent className="max-h-[90vh] w-[96vw] max-w-7xl overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{selectedLevelMonth} · {String(selectedLevel?.customer_level || "会员级别")} · 会员月消费</DialogTitle>
                <p className="text-sm text-muted-foreground">消费金额为该会员在 601 常州购物中心当月全部销售小票金额，不限于使用本券的小票。</p>
              </DialogHeader>
              <form className="flex flex-col gap-2 sm:flex-row" onSubmit={(event) => {
                event.preventDefault();
                setLevelMemberKeyword(levelMemberKeywordDraft.trim());
                setLevelMemberOffset(0);
              }}>
                <div className="relative flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><Input value={levelMemberKeywordDraft} onChange={(event) => setLevelMemberKeywordDraft(event.target.value)} className="pl-9" placeholder="按会员卡号或姓名搜索" /></div>
                <Button type="submit" variant="outline">查询</Button>
              </form>
              {levelMembersQuery.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在读取会员月消费…</div>
              ) : levelMembersQuery.isError ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{errorText(levelMembersQuery.error)}</div>
              ) : (
                <>
                  <div className="overflow-x-auto rounded-lg border"><Table className="min-w-[1100px]">
                    <TableHeader><TableRow><TableHead>会员卡号</TableHead><TableHead>会员姓名</TableHead><TableHead className="text-right">领券张数</TableHead><TableHead className="text-right">发放金额</TableHead><TableHead className="text-right">净核销</TableHead><TableHead className="text-right">当月小票</TableHead><TableHead className="text-right">当月消费金额</TableHead><TableHead>末次消费</TableHead><TableHead className="w-12" /></TableRow></TableHeader>
                    <TableBody>{levelMembersQuery.data?.items.length ? levelMembersQuery.data.items.map((row) => <TableRow
                      key={String(row.member_no)} role="button" tabIndex={0} className="cursor-pointer hover:bg-violet-50"
                      onClick={() => setSelectedLevelMember(row)}
                      onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") setSelectedLevelMember(row); }}
                    >
                      <TableCell className="font-mono text-xs">{maskBirthdayCouponMemberNo(row.member_no)}</TableCell><TableCell>{maskBirthdayCouponMemberName(row.customer_name)}</TableCell>
                      <TableCell className="text-right tabular-nums">{number(row.issue_count)}</TableCell><TableCell className="text-right tabular-nums">{money(row.issued_amount)}</TableCell>
                      <TableCell className="text-right tabular-nums">{money(row.net_redeemed_amount)}</TableCell><TableCell className="text-right tabular-nums">{number(row.ticket_count)}</TableCell>
                      <TableCell className="text-right tabular-nums font-medium">{moneyDetailed(row.monthly_sales_amount)}</TableCell><TableCell>{fmtDateTime(row.last_sale_time)}</TableCell><TableCell><ChevronRight className="h-4 w-4 text-muted-foreground" /></TableCell>
                    </TableRow>) : <EmptyRow colSpan={9}>没有符合条件的会员</EmptyRow>}</TableBody>
                  </Table></div>
                  <div className="flex flex-col gap-2 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                    <span>共 {number(levelMembersQuery.data?.total || 0)} 位；当前显示 {levelMembersQuery.data?.total ? levelMemberOffset + 1 : 0}–{Math.min(levelMemberOffset + LEVEL_MEMBER_PAGE_SIZE, levelMembersQuery.data?.total || 0)}</span>
                    <div className="flex gap-2"><Button variant="outline" size="sm" disabled={levelMemberOffset === 0} onClick={() => setLevelMemberOffset(Math.max(0, levelMemberOffset - LEVEL_MEMBER_PAGE_SIZE))}>上一页</Button><Button variant="outline" size="sm" disabled={levelMemberOffset + LEVEL_MEMBER_PAGE_SIZE >= (levelMembersQuery.data?.total || 0)} onClick={() => setLevelMemberOffset(levelMemberOffset + LEVEL_MEMBER_PAGE_SIZE)}>下一页</Button></div>
                  </div>
                </>
              )}
            </DialogContent>
          </Dialog>

          <Dialog open={Boolean(selectedLevelMember)} onOpenChange={(open) => !open && setSelectedLevelMember(null)}>
            <DialogContent className="max-h-[90vh] w-[96vw] max-w-7xl overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{selectedLevelMonth} · {maskBirthdayCouponMemberNo(selectedLevelMember?.member_no)} · 月消费明细</DialogTitle>
                <p className="text-sm text-muted-foreground">{maskBirthdayCouponMemberName(selectedLevelMember?.customer_name)} · {String(selectedLevelMember?.customer_level || "未识别")}</p>
              </DialogHeader>
              {memberSalesQuery.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />正在读取月消费明细…</div>
              ) : memberSalesQuery.isError ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">{errorText(memberSalesQuery.error)}</div>
              ) : (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs text-muted-foreground">小票数</p><p className="mt-1 text-xl font-semibold tabular-nums">{number(memberSalesQuery.data?.summary.ticket_count)}</p></div>
                    <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs text-muted-foreground">消费金额</p><p className="mt-1 text-xl font-semibold tabular-nums">{moneyDetailed(memberSalesQuery.data?.summary.sales_amount)}</p></div>
                    <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs text-muted-foreground">商品数量</p><p className="mt-1 text-xl font-semibold tabular-nums">{decimal(memberSalesQuery.data?.summary.quantity)}</p></div>
                  </div>
                  <div className="overflow-x-auto rounded-lg border"><Table className="min-w-[1250px]">
                    <TableHeader><TableRow><TableHead>消费时间</TableHead><TableHead>业务单号</TableHead><TableHead className="text-right">SKU数</TableHead><TableHead className="text-right">数量</TableHead><TableHead className="text-right">消费金额</TableHead><TableHead>部门</TableHead><TableHead>柜组</TableHead><TableHead>品牌编码</TableHead></TableRow></TableHeader>
                    <TableBody>{memberSalesQuery.data?.items.length ? memberSalesQuery.data.items.map((row, index) => <TableRow key={String(row.billno || index)}>
                      <TableCell>{fmtDateTime(row.sale_time)}</TableCell><TableCell className="font-mono text-xs">{String(row.billno || "—")}</TableCell>
                      <TableCell className="text-right tabular-nums">{number(row.sku_count)}</TableCell><TableCell className="text-right tabular-nums">{decimal(row.quantity)}</TableCell><TableCell className="text-right tabular-nums font-medium">{moneyDetailed(row.sales_amount)}</TableCell>
                      <TableCell className="max-w-[260px] whitespace-normal">{String(row.departments || "—")}</TableCell><TableCell className="max-w-[300px] whitespace-normal">{String(row.groups || "—")}</TableCell><TableCell className="max-w-[220px] whitespace-normal">{String(row.brand_codes || "—")}</TableCell>
                    </TableRow>) : <EmptyRow colSpan={8}>该会员当月没有消费小票</EmptyRow>}</TableBody>
                  </Table></div>
                  {memberSalesQuery.data?.summary.truncated ? <p className="text-xs text-amber-700">明细超过 500 张小票，当前仅显示前 500 张。</p> : null}
                </div>
              )}
            </DialogContent>
          </Dialog>

          <p className="text-xs leading-5 text-muted-foreground">
            口径提示：会员人数为“会员批次人次”，同一会员跨月领取会分别计算；页面隐藏完整会员卡号，导出表保留内部会员卡号用于授权范围内核对。当前发放动作 M 在源系统字典中标为“后台买券”；L券标准每人1张，C券标准每人2张。
          </p>
        </>
      ) : null}
    </div>
  );
}
