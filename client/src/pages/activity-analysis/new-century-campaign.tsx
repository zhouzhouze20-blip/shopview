import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarDays, Download, Gift, RefreshCw, TicketPercent, TrendingUp, Users } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet } from "@/lib/api";
import { CampaignDashboard, exportNewCenturyCampaign, filterGiftRedemptionDetails } from "@/lib/new-century-campaign";

const money = (value: unknown) => new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));
const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));
const percent = (value: unknown) => value === null || value === undefined ? "—" : `${Number(value).toFixed(1)}%`;
const dateTime = (value: unknown) => typeof value === "string" && value ? value.replace("T", " ").slice(0, 16) : "—";

function isoLocal(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function initialDates() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const compareStart = new Date(start); compareStart.setFullYear(compareStart.getFullYear() - 1);
  const compareEnd = new Date(now); compareEnd.setFullYear(compareEnd.getFullYear() - 1);
  return { start: isoLocal(start), end: isoLocal(now), compareStart: isoLocal(compareStart), compareEnd: isoLocal(compareEnd) };
}

function Change({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-xs text-slate-400">同期为 0</span>;
  const positive = value >= 0;
  const Icon = positive ? ArrowUpRight : ArrowDownRight;
  return <span className={`inline-flex items-center text-xs font-medium ${positive ? "text-rose-600" : "text-emerald-600"}`}><Icon className="mr-0.5 h-3.5 w-3.5" />同比 {Math.abs(value).toFixed(1)}%</span>;
}

function MetricCard({ title, value, comparison, change, subtitle }: { title: string; value: string; comparison: string; change?: number | null; subtitle?: string }) {
  return (
    <Card className="border-slate-200 shadow-sm">
      <CardContent className="p-5">
        <div className="text-sm text-slate-500">{title}</div>
        <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{value}</div>
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1"><span className="text-xs text-slate-500">同期 {comparison}</span><Change value={change} /></div>
        {subtitle ? <div className="mt-2 text-xs text-slate-400">{subtitle}</div> : null}
      </CardContent>
    </Card>
  );
}

function SummaryCard({ title, value, note, tone = "blue" }: { title: string; value: string; note: string; tone?: "blue" | "violet" | "emerald" | "amber" }) {
  const colors = { blue: "bg-blue-50 text-blue-700", violet: "bg-violet-50 text-violet-700", emerald: "bg-emerald-50 text-emerald-700", amber: "bg-amber-50 text-amber-700" }[tone];
  return <div className={`rounded-xl p-4 ${colors}`}><div className="text-xs opacity-75">{title}</div><div className="mt-1 text-xl font-semibold">{value}</div><div className="mt-1 text-xs opacity-70">{note}</div></div>;
}

function buildQuery(values: Record<string, string | number>) {
  const query = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => query.set(key, String(value)));
  return `?${query}`;
}

export default function NewCenturyCampaignPage() {
  const defaults = useMemo(initialDates, []);
  const [draft, setDraft] = useState(defaults);
  const [filters, setFilters] = useState(defaults);
  const [giftTemplateId, setGiftTemplateId] = useState("all");
  const invalid = draft.start > draft.end || draft.compareStart > draft.compareEnd;
  const query = useQuery<CampaignDashboard>({
    queryKey: ["/api/activity-analysis/new-century/dashboard", filters],
    queryFn: () => apiGet(`/api/activity-analysis/new-century/dashboard${buildQuery({ start_date: filters.start, end_date: filters.end, compare_start_date: filters.compareStart, compare_end_date: filters.compareEnd, detail_limit: 1000 })}`),
  });
  const report = query.data;
  const current = report?.overview.current;
  const comparison = report?.overview.comparison;
  const change = report?.overview.change_percent;
  const qualityCritical = report?.quality.status === "critical";
  const filteredGiftDetails = useMemo(
    () => filterGiftRedemptionDetails(report?.gift_redemption.details || [], giftTemplateId),
    [giftTemplateId, report?.gift_redemption.details],
  );

  return (
    <div className="min-h-full bg-slate-50/70 p-4 md:p-6">
      <div className="mx-auto max-w-[1600px] space-y-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2"><Badge className="bg-blue-600 hover:bg-blue-600">603</Badge><span className="text-sm text-slate-500">常州新世纪商城</span></div>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">新世纪活动分析</h1>
            <p className="mt-1 text-sm text-slate-500">活动销售与会员表现 · 卡券增值 · 礼品券核销后当日消费</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw className={`mr-2 h-4 w-4 ${query.isFetching ? "animate-spin" : ""}`} />刷新</Button>
            <Button variant="outline" onClick={() => report && exportNewCenturyCampaign(report)} disabled={!report}><Download className="mr-2 h-4 w-4" />导出整体活动 Excel</Button>
          </div>
        </div>

        <Card className="border-slate-200 shadow-sm"><CardContent className="p-4"><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[repeat(4,minmax(150px,1fr))_auto]">
          {([
            ["活动开始", "start"], ["活动结束", "end"], ["同期开始", "compareStart"], ["同期结束", "compareEnd"],
          ] as const).map(([label, key]) => <div key={key}><Label className="text-xs text-slate-500">{label}</Label><Input className="mt-1" type="date" value={draft[key]} onChange={(event) => setDraft((old) => ({ ...old, [key]: event.target.value }))} /></div>)}
          <Button className="self-end bg-blue-600 hover:bg-blue-700" disabled={invalid} onClick={() => { setFilters(draft); setGiftTemplateId("all"); }}><CalendarDays className="mr-2 h-4 w-4" />应用</Button>
        </div>{invalid ? <div className="mt-2 text-xs text-rose-600">开始日期不能晚于结束日期</div> : null}</CardContent></Card>

        {query.isLoading ? <Card><CardContent className="py-16 text-center text-slate-500">正在汇总销售、会员和卡券数据…</CardContent></Card> : null}
        {query.isError ? <Card className="border-rose-200 bg-rose-50"><CardContent className="py-8 text-center text-rose-700">{query.error instanceof Error ? query.error.message : "数据加载失败"}</CardContent></Card> : null}

        {report ? <>
          <div className={`flex gap-3 rounded-xl border p-4 ${qualityCritical ? "border-amber-300 bg-amber-50" : "border-emerald-200 bg-emerald-50"}`}>
            <AlertTriangle className={`mt-0.5 h-5 w-5 shrink-0 ${qualityCritical ? "text-amber-600" : "text-emerald-600"}`} />
            <div className="min-w-0"><div className="font-medium text-slate-900">卡券数据质量：{qualityCritical ? "需关注" : "正常"}</div><div className="mt-1 text-sm text-slate-700">{String(report.quality.message || "")}</div><div className="mt-1 text-xs text-slate-500">源数据最新：{dateTime(report.quality.max_source_dt)} · 本地装载：{dateTime(report.quality.record_loaded_at)} · 缺失模板的核销记录 {number(report.quality.used_orphan_record_count)} 条</div></div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="销售额" value={money(current?.sales_amount)} comparison={money(comparison?.sales_amount)} change={change?.sales_amount} />
            <MetricCard title="小票数 / 客单价" value={`${number(current?.ticket_count)} / ${money(current?.average_ticket)}`} comparison={`${number(comparison?.ticket_count)} / ${money(comparison?.average_ticket)}`} change={change?.ticket_count} />
            <MetricCard title="会员消费人数" value={number(current?.consuming_member_count)} comparison={number(comparison?.consuming_member_count)} change={change?.consuming_member_count} subtitle={`会员消费额 ${money(current?.member_sales_amount)} · 销售占比 ${percent(current?.member_sales_share)}`} />
            <MetricCard title="招新 / 新客转化" value={`${number(current?.new_member_count)} / ${percent(current?.new_member_conversion)}`} comparison={`${number(comparison?.new_member_count)} / ${percent(comparison?.new_member_conversion)}`} change={change?.new_member_count} />
          </div>

          <Card className="border-slate-200 shadow-sm"><CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-4 w-4 text-blue-600" />活动期逐日销售</CardTitle></CardHeader><CardContent className="h-[290px] pt-2"><ResponsiveContainer width="100%" height="100%"><LineChart data={report.daily_sales}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="business_date" tickFormatter={(value) => String(value).slice(5)} fontSize={12} /><YAxis tickFormatter={(value) => `${Math.round(Number(value) / 10000)}万`} fontSize={12} /><Tooltip formatter={(value) => money(value)} labelFormatter={(value) => `日期 ${value}`} /><Line type="monotone" dataKey="sales_amount" name="销售额" stroke="#2563eb" strokeWidth={2.5} dot={false} /></LineChart></ResponsiveContainer></CardContent></Card>

          <Tabs defaultValue="recharge" className="space-y-4"><TabsList className="grid w-full max-w-lg grid-cols-2"><TabsTrigger value="recharge"><TicketPercent className="mr-2 h-4 w-4" />增值</TabsTrigger><TabsTrigger value="gift"><Gift className="mr-2 h-4 w-4" />礼品券核销消费</TabsTrigger></TabsList>
            <TabsContent value="recharge" className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><SummaryCard title="增值面值" value={money(report.recharge.summary.increase_face_amount)} note="m/M 增值日志" /><SummaryCard title="冲正/退值" value={money(report.recharge.summary.reversal_face_amount)} note="n/N/w 日志" tone="amber" /><SummaryCard title="净增值" value={money(report.recharge.summary.net_face_amount)} note="增值减冲正退值" tone="emerald" /><SummaryCard title="涉及会员" value={number(report.recharge.summary.member_count)} note={`${number(report.recharge.summary.flow_count)} 笔日志`} tone="violet" /></div>
              <Card><CardHeader><CardTitle className="text-base">增值日志明细</CardTitle></CardHeader><CardContent><div className="max-h-[520px] overflow-auto"><Table><TableHeader><TableRow><TableHead>日期</TableHead><TableHead>会员</TableHead><TableHead>券种</TableHead><TableHead>动作</TableHead><TableHead>来源</TableHead><TableHead className="text-right">面值</TableHead></TableRow></TableHeader><TableBody>{report.recharge.details.map((row) => <TableRow key={String(row.sequence_no)}><TableCell>{String(row.business_date || "—")}</TableCell><TableCell className="font-mono text-xs">{String(row.member_no)}</TableCell><TableCell>{String(row.coupon_name)}</TableCell><TableCell><Badge variant="outline">{String(row.action_name)}</Badge></TableCell><TableCell>{String(row.source_name)}</TableCell><TableCell className="text-right font-medium">{money(row.face_amount)}</TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card>
            </TabsContent>
            <TabsContent value="gift" className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><SummaryCard title="礼品券核销" value={number(report.gift_redemption.summary.redemption_count)} note={`${number(report.gift_redemption.summary.member_day_count)} 个会员日`} /><SummaryCard title="同日消费转化" value={percent(report.gift_redemption.summary.conversion_rate)} note={`${number(report.gift_redemption.summary.consuming_member_day_count)} 个会员日有消费`} tone="emerald" /><SummaryCard title="同日消费额" value={money(report.gift_redemption.summary.same_day_sales_amount)} note={`${number(report.gift_redemption.summary.same_day_ticket_count)} 张小票`} tone="violet" /><SummaryCard title="消费会员客单" value={money(report.gift_redemption.summary.spend_per_consumer)} note={`未匹配会员 ${number(report.gift_redemption.summary.unmatched_redemption_count)} 条`} tone="amber" /></div>
              <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]"><Card><CardHeader><CardTitle className="text-base">礼品券核销与同日消费趋势</CardTitle></CardHeader><CardContent className="h-[300px]"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={report.gift_redemption.daily}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="business_date" tickFormatter={(value) => String(value).slice(5)} fontSize={12} /><YAxis yAxisId="left" fontSize={12} /><YAxis yAxisId="right" orientation="right" tickFormatter={(value) => `${Math.round(Number(value) / 1000)}千`} fontSize={12} /><Tooltip /><Bar yAxisId="left" dataKey="redemption_count" name="核销张数" fill="#8b5cf6" radius={[4, 4, 0, 0]} /><Line yAxisId="right" dataKey="same_day_sales_amount" name="同日消费额" stroke="#059669" /></ComposedChart></ResponsiveContainer></CardContent></Card>
                <Card><CardHeader><CardTitle className="text-base">礼品券类型</CardTitle></CardHeader><CardContent><div className="max-h-[300px] overflow-auto"><Table><TableHeader><TableRow><TableHead>礼品券</TableHead><TableHead className="text-right">核销</TableHead><TableHead className="text-right">会员</TableHead></TableRow></TableHeader><TableBody>{report.gift_redemption.templates.map((row) => <TableRow key={String(row.template_id)}><TableCell className="max-w-[220px] truncate" title={String(row.gift_name)}>{String(row.gift_name)}</TableCell><TableCell className="text-right">{number(row.redemption_count)}</TableCell><TableCell className="text-right">{number(row.member_count)}</TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card></div>
              <Card><CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between"><CardTitle className="flex items-center gap-2 text-base"><Users className="h-4 w-4 text-violet-600" />核销会员当日消费明细</CardTitle><div className="flex flex-col gap-2 sm:flex-row sm:items-center"><span className="whitespace-nowrap text-xs text-slate-500">{number(filteredGiftDetails.length)} / {number(report.gift_redemption.details.length)} 条</span><Select value={giftTemplateId} onValueChange={setGiftTemplateId}><SelectTrigger id="gift-template-filter" className="w-full sm:w-[320px]" aria-label="筛选礼品券"><SelectValue placeholder="选择礼品券" /></SelectTrigger><SelectContent><SelectItem value="all">全部礼品券</SelectItem>{report.gift_redemption.templates.map((row) => <SelectItem key={String(row.template_id)} value={String(row.template_id)}>{String(row.gift_name)}（{number(row.redemption_count)}）</SelectItem>)}</SelectContent></Select></div></CardHeader><CardContent><div className="max-h-[560px] overflow-auto"><Table><TableHeader><TableRow><TableHead>核销时间</TableHead><TableHead>礼品券</TableHead><TableHead>会员号</TableHead><TableHead>手机号</TableHead><TableHead>等级</TableHead><TableHead className="text-right">同日小票</TableHead><TableHead className="text-right">同日消费</TableHead></TableRow></TableHeader><TableBody>{filteredGiftDetails.length ? filteredGiftDetails.map((row) => <TableRow key={`${row.coupon_code}-${row.used_date_time}`}><TableCell>{dateTime(row.used_date_time)}</TableCell><TableCell className="max-w-[260px] truncate" title={String(row.gift_name)}>{String(row.gift_name)}</TableCell><TableCell className="font-mono text-xs">{String(row.member_no)}</TableCell><TableCell className="font-mono text-xs">{String(row.mobile)}</TableCell><TableCell>{String(row.level_code || "—")}</TableCell><TableCell className="text-right">{number(row.same_day_ticket_count)}</TableCell><TableCell className="text-right font-medium">{money(row.same_day_sales_amount)}</TableCell></TableRow>) : <TableRow><TableCell colSpan={7} className="py-10 text-center text-slate-500">当前礼品券暂无核销消费明细</TableCell></TableRow>}</TableBody></Table></div></CardContent></Card>
            </TabsContent>
          </Tabs>
          <div className="rounded-lg bg-slate-100 p-3 text-xs leading-5 text-slate-500">口径：{Object.values(report.definitions).join(" ")}</div>
        </> : null}
      </div>
    </div>
  );
}
