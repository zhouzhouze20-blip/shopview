import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, CalendarDays, Crown, Eye, Loader2, RefreshCw, Search, ShoppingBag, Sparkles, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import { canAccessModule } from "@/lib/module-permissions";

type RowData = Record<string, number | string | null>;

type Overview = {
  summary: RowData;
  top_categories: RowData[];
  service_segments: RowData[];
};

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));
const fmtDateTime = (value: unknown) => (typeof value === "string" && value ? value.replace("T", " ").slice(0, 19) : "—");
const fmtDate = (value: unknown) => (typeof value === "string" && value ? value.slice(0, 10) : "—");
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

function defaultDateRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 30);
  return {
    startDate: start.toISOString().slice(0, 10),
    endDate: end.toISOString().slice(0, 10),
  };
}

function MetricCard({ title, value, subtitle, icon: Icon }: { title: string; value: string; subtitle?: string; icon: LucideIcon }) {
  return (
    <Card className="rounded-lg">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
          {subtitle ? <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p> : null}
        </div>
        <div className="rounded-md bg-slate-100 p-2 text-slate-700">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function SimpleTable({
  rows,
  columns,
  onRowClick,
  rowClassName,
}: {
  rows: RowData[];
  columns: Array<[string, string, (value: unknown) => string] | [string, string] | [string, string, undefined, (row: RowData) => ReactNode]>;
  onRowClick?: (row: RowData) => void;
  rowClassName?: (row: RowData) => string;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map(([, label]) => (
              <TableHead key={label} className="whitespace-nowrap">{label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length ? (
            rows.map((row, index) => (
              <TableRow
                key={`${row.member_no || row.billno || row.segment || row.category_code || "row"}-${index}`}
                className={`${onRowClick ? "cursor-pointer hover:bg-slate-50" : ""} ${rowClassName?.(row) || ""}`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(([key, , formatter, render]) => (
                  <TableCell key={key} className="whitespace-nowrap">
                    {render ? render(row) : formatter ? formatter(row[key]) : String(row[key] ?? "—")}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">暂无数据</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

export default function StarDiamondAnalysisPage() {
  const { menuUser } = useAuth();
  const canViewStarDiamond = canAccessModule(menuUser, "star-diamond-analysis");
  const defaults = useMemo(defaultDateRange, []);
  const [startDate, setStartDate] = useState(defaults.startDate);
  const [endDate, setEndDate] = useState(defaults.endDate);
  const [keyword, setKeyword] = useState("");
  const [selectedMember, setSelectedMember] = useState("");
  const [selectedSegment, setSelectedSegment] = useState("");
  const [activeTab, setActiveTab] = useState("members");
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<Record<string, unknown> | null>(null);
  const [overallAnalysisOpen, setOverallAnalysisOpen] = useState(false);
  const [overallAnalysisLoading, setOverallAnalysisLoading] = useState(false);
  const [overallAnalysisResult, setOverallAnalysisResult] = useState<Record<string, unknown> | null>(null);

  const commonParams = { start_date: startDate, end_date: endDate };
  const overviewQuery = useQuery<Overview>({
    queryKey: ["/api/activity-analysis/star-diamond/overview", commonParams],
    queryFn: () => apiGet(`/api/activity-analysis/star-diamond/overview${buildQuery(commonParams)}`),
    enabled: canViewStarDiamond,
  });
  const membersQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/star-diamond/members", commonParams, keyword],
    queryFn: () =>
      apiGet(`/api/activity-analysis/star-diamond/members${buildQuery({ ...commonParams, keyword, limit: 300 })}`),
    enabled: canViewStarDiamond,
  });
  const trailsQuery = useQuery<RowData[]>({
    queryKey: ["/api/activity-analysis/star-diamond/trails", commonParams, selectedMember],
    queryFn: () =>
      apiGet(`/api/activity-analysis/star-diamond/trails${buildQuery({ ...commonParams, member_no: selectedMember, limit: 300 })}`),
    enabled: canViewStarDiamond,
  });

  const summary = overviewQuery.data?.summary || {};
  const activeRate = Number(summary.star_member_count || 0) > 0
    ? `${((Number(summary.active_member_count || 0) / Number(summary.star_member_count || 0)) * 100).toFixed(1)}%`
    : "—";
  const repeatRate = Number(summary.active_member_count || 0) > 0
    ? `${((Number(summary.repeat_member_count || 0) / Number(summary.active_member_count || 0)) * 100).toFixed(1)}%`
    : "—";

  const refreshAll = () => {
    overviewQuery.refetch();
    membersQuery.refetch();
    trailsQuery.refetch();
  };
  const visibleMembers = useMemo(() => {
    const rows = membersQuery.data || [];
    if (!selectedSegment) return rows;
    return rows.filter((row) => row.service_segment === selectedSegment);
  }, [membersQuery.data, selectedSegment]);

  const openMemberDetail = (memberNo: unknown) => {
    const value = String(memberNo || "").trim();
    if (!value) return;
    setSelectedMember(value);
    setActiveTab("trails");
  };

  const runMemberAnalysis = async (row: RowData) => {
    if (!canViewStarDiamond) return;
    const memberNo = String(row.member_no || "").trim();
    if (!memberNo) return;
    setAnalysisOpen(true);
    setAnalysisLoading(true);
    setAnalysisResult(null);
    try {
      const result = await apiPost<Record<string, unknown>>("/api/activity-analysis/star-diamond/member-analysis", {
        member_no: memberNo,
        start_date: startDate,
        end_date: endDate,
      });
      setAnalysisResult(result);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const runOverallAnalysis = async () => {
    if (!canViewStarDiamond) return;
    setOverallAnalysisOpen(true);
    setOverallAnalysisLoading(true);
    setOverallAnalysisResult(null);
    try {
      const result = await apiPost<Record<string, unknown>>("/api/activity-analysis/star-diamond/overall-analysis", {
        start_date: startDate,
        end_date: endDate,
      });
      setOverallAnalysisResult(result);
    } finally {
      setOverallAnalysisLoading(false);
    }
  };

  if (!canViewStarDiamond) {
    return null;
  }

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">中心星钻会员分析</h1>
            <Badge variant="secondary">常州购物中心</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">针对已标记星钻会员，观察消费贡献、购物轨迹、偏好品类和服务分层。</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div>
            <Label htmlFor="star-start">开始日期</Label>
            <Input id="star-start" className="mt-1 w-full sm:w-40" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="star-end">结束日期</Label>
            <Input id="star-end" className="mt-1 w-full sm:w-40" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <Button variant="outline" onClick={refreshAll} disabled={overviewQuery.isFetching || membersQuery.isFetching || trailsQuery.isFetching}>
            {overviewQuery.isFetching || membersQuery.isFetching || trailsQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
          <Button onClick={runOverallAnalysis} disabled={overallAnalysisLoading}>
            {overallAnalysisLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Bot className="mr-2 h-4 w-4" />}
            AI整体方案
          </Button>
        </div>
      </div>

      {overviewQuery.isError ? (
        <Card className="rounded-lg border-red-200 bg-red-50">
          <CardContent className="p-4 text-sm text-red-700">{errorText(overviewQuery.error)}</CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard title="星钻会员" value={number(summary.star_member_count)} subtitle={`消费覆盖 ${activeRate}`} icon={Crown} />
            <MetricCard title="期间销售额" value={money(summary.sales_amount)} subtitle={`消费会员 ${number(summary.active_member_count)} 人`} icon={ShoppingBag} />
            <MetricCard title="客单价" value={money(summary.avg_ticket_amount)} subtitle={`小票 ${number(summary.ticket_count)} 笔`} icon={CalendarDays} />
            <MetricCard title="复购会员" value={number(summary.repeat_member_count)} subtitle={`复购率 ${repeatRate}`} icon={Users} />
            <MetricCard title="人均消费" value={money(summary.avg_member_amount)} subtitle="按有消费星钻会员计算" icon={Sparkles} />
            <MetricCard title="高价值维护" value={number(summary.high_value_member_count)} subtitle="期间消费 >= 10,000" icon={Crown} />
            <MetricCard title="待唤醒会员" value={number(summary.silent_member_count)} subtitle="期间暂无中心消费" icon={Users} />
            <MetricCard title="净毛利" value={money(summary.net_profit)} subtitle="销售汇总表口径" icon={ShoppingBag} />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="rounded-lg">
              <CardHeader><CardTitle className="text-base">服务分层建议</CardTitle></CardHeader>
              <CardContent>
                <SimpleTable
                  rows={overviewQuery.data?.service_segments || []}
                  onRowClick={(row) => {
                    setSelectedSegment(String(row.segment || ""));
                    setActiveTab("members");
                  }}
                  rowClassName={(row) => row.segment === selectedSegment ? "bg-slate-100" : ""}
                  columns={[
                    ["segment", "分层"],
                    ["member_count", "会员数", number],
                    ["sales_amount", "销售额", money],
                    ["service_action", "建议服务动作"],
                  ]}
                />
              </CardContent>
            </Card>
            <Card className="rounded-lg">
              <CardHeader><CardTitle className="text-base">偏好品类 Top10</CardTitle></CardHeader>
              <CardContent>
                <SimpleTable
                  rows={overviewQuery.data?.top_categories || []}
                  columns={[
                    ["category_display", "品类"],
                    ["member_count", "消费会员", number],
                    ["ticket_count", "小票数", number],
                    ["sales_amount", "销售额", money],
                  ]}
                />
              </CardContent>
            </Card>
          </div>
        </>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="members">会员清单</TabsTrigger>
          <TabsTrigger value="trails">购物轨迹</TabsTrigger>
        </TabsList>
        <TabsContent value="members" className="space-y-3">
          <Card className="rounded-lg">
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
              <div className="w-full sm:w-80">
                <Label htmlFor="star-keyword">会员搜索</Label>
                <Input id="star-keyword" className="mt-1" value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="会员号、姓名、手机号" />
              </div>
              <Button variant="outline" onClick={() => membersQuery.refetch()}>
                <Search className="mr-2 h-4 w-4" />
                查询
              </Button>
              {selectedSegment ? (
                <Button variant="ghost" onClick={() => setSelectedSegment("")}>
                  清除分层：{selectedSegment}
                </Button>
              ) : null}
            </CardContent>
          </Card>
          {membersQuery.isError ? (
            <Card className="rounded-lg border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">{errorText(membersQuery.error)}</CardContent></Card>
          ) : (
            <SimpleTable
              rows={visibleMembers}
              columns={[
                [
                  "__actions",
                  "操作",
                  undefined,
                  (row) => (
                    <div className="flex gap-2" onClick={(event) => event.stopPropagation()}>
                      <Button type="button" size="sm" variant="outline" onClick={() => openMemberDetail(row.member_no)}>
                        <Eye className="mr-1 h-3 w-3" />
                        明细
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => runMemberAnalysis(row)}>
                        <Bot className="mr-1 h-3 w-3" />
                        AI分析
                      </Button>
                    </div>
                  ),
                ],
                ["member_no", "会员号"],
                ["customer_name", "姓名"],
                ["telephone", "手机号"],
                ["customer_level", "等级"],
                ["admission_date", "入会日期", fmtDate],
                ["ticket_count", "小票数", number],
                ["sales_amount", "销售额", money],
                ["avg_ticket_amount", "客单", money],
                ["last_sale_time", "最近消费", fmtDateTime],
                ["categories", "消费品类"],
                ["brands", "消费品牌"],
                ["service_segment", "服务分层"],
              ]}
            />
          )}
        </TabsContent>
        <TabsContent value="trails" className="space-y-3">
          <Card className="rounded-lg">
            <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
              <div className="w-full sm:w-80">
                <Label htmlFor="trail-member">指定会员</Label>
                <Input id="trail-member" className="mt-1" value={selectedMember} onChange={(event) => setSelectedMember(event.target.value)} placeholder="留空查看全部星钻会员轨迹" />
              </div>
              <Button variant="outline" onClick={() => trailsQuery.refetch()}>
                <Search className="mr-2 h-4 w-4" />
                查询轨迹
              </Button>
            </CardContent>
          </Card>
          {trailsQuery.isError ? (
            <Card className="rounded-lg border-red-200 bg-red-50"><CardContent className="p-4 text-sm text-red-700">{errorText(trailsQuery.error)}</CardContent></Card>
          ) : (
            <SimpleTable
              rows={trailsQuery.data || []}
              columns={[
                ["sale_time", "销售时间", fmtDateTime],
                ["billno", "小票"],
                ["member_no", "会员号"],
                ["customer_name", "姓名"],
                ["sku_count", "SKU数", number],
                ["quantity", "件数", number],
                ["sales_amount", "销售额", money],
                ["net_profit", "净毛利", money],
                ["departments", "部门"],
                ["groups", "柜组"],
                ["categories", "品类"],
                ["brands", "品牌"],
              ]}
            />
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={analysisOpen} onOpenChange={setAnalysisOpen}>
        <DialogContent className="max-h-[86vh] w-[92vw] max-w-4xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>星钻会员 AI 分析</DialogTitle>
          </DialogHeader>
          {analysisLoading ? (
            <div className="flex min-h-40 items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在生成会员分析...
            </div>
          ) : analysisResult ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">会员</p>
                  <p className="mt-1 font-semibold">{String((analysisResult.member as RowData)?.member_no || "—")}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">期间消费</p>
                  <p className="mt-1 font-semibold">{money((analysisResult.summary as RowData)?.sales_amount)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">小票数</p>
                  <p className="mt-1 font-semibold">{number((analysisResult.summary as RowData)?.ticket_count)}</p>
                </div>
              </div>
              <Card className="rounded-lg">
                <CardHeader><CardTitle className="text-base">AI 建议</CardTitle></CardHeader>
                <CardContent>
                  {(analysisResult.ai as RowData)?.report ? (
                    <div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{String((analysisResult.ai as RowData).report)}</div>
                  ) : (
                    <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                      {String((analysisResult.ai as RowData)?.error || "AI 暂不可用，已展示规则建议。")}
                    </div>
                  )}
                </CardContent>
              </Card>
              <Card className="rounded-lg">
                <CardHeader><CardTitle className="text-base">规则建议</CardTitle></CardHeader>
                <CardContent className="space-y-2 text-sm text-slate-700">
                  {((analysisResult.rule_notes as unknown[]) || []).map((item, index) => (
                    <div key={index} className="rounded-md border p-2">{String(item)}</div>
                  ))}
                </CardContent>
              </Card>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={overallAnalysisOpen} onOpenChange={setOverallAnalysisOpen}>
        <DialogContent className="max-h-[86vh] w-[92vw] max-w-5xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>星钻会员整体 AI 方案</DialogTitle>
          </DialogHeader>
          {overallAnalysisLoading ? (
            <div className="flex min-h-40 items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在生成整体运营方案...
            </div>
          ) : overallAnalysisResult ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">星钻会员</p>
                  <p className="mt-1 font-semibold">{number((overallAnalysisResult.summary as RowData)?.star_member_count)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">消费会员</p>
                  <p className="mt-1 font-semibold">{number((overallAnalysisResult.summary as RowData)?.active_member_count)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">期间销售</p>
                  <p className="mt-1 font-semibold">{money((overallAnalysisResult.summary as RowData)?.sales_amount)}</p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">待唤醒</p>
                  <p className="mt-1 font-semibold">{number((overallAnalysisResult.summary as RowData)?.silent_member_count)}</p>
                </div>
              </div>
              <Card className="rounded-lg">
                <CardHeader><CardTitle className="text-base">AI 整体方案</CardTitle></CardHeader>
                <CardContent>
                  {(overallAnalysisResult.ai as RowData)?.report ? (
                    <div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{String((overallAnalysisResult.ai as RowData).report)}</div>
                  ) : (
                    <div className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                      {String((overallAnalysisResult.ai as RowData)?.error || "AI 暂不可用，已展示规则提示。")}
                    </div>
                  )}
                </CardContent>
              </Card>
              <div className="grid gap-4 xl:grid-cols-2">
                <Card className="rounded-lg">
                  <CardHeader><CardTitle className="text-base">分层规模</CardTitle></CardHeader>
                  <CardContent>
                    <SimpleTable
                      rows={(overallAnalysisResult.service_segments as RowData[]) || []}
                      columns={[
                        ["segment", "分层"],
                        ["member_count", "会员数", number],
                        ["sales_amount", "销售额", money],
                      ]}
                    />
                  </CardContent>
                </Card>
                <Card className="rounded-lg">
                  <CardHeader><CardTitle className="text-base">规则提示</CardTitle></CardHeader>
                  <CardContent className="space-y-2 text-sm text-slate-700">
                    {((overallAnalysisResult.rule_notes as unknown[]) || []).map((item, index) => (
                      <div key={index} className="rounded-md border p-2">{String(item)}</div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
