import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight, RefreshCw, Loader2, Download } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { type LiveReport, type LiveRow, type LiveColumn, type LiveDepartment, type LiveQueryRange, couponColumns, departmentColumns, groupColumns,
  ticketColumns, trajectoryColumns, filterTrajectory, filterCouponDepartments, filterCouponGroups,
  couponLiveQueryUrl, validateLiveQueryRange, shanghaiToday, LIVE_COUPON_TYPES,
  summarizeHolderPeriod, holderPeriodDetails, hasMemberPeriodData, holderColumns, holderDetailColumns, holderDetailLabels, type HolderDetailMode } from "@/lib/coupon-live";
import { exportLiveWorkbook, includesMemberSheets, type LiveTab } from "@/lib/coupon-live-export";

const fmt = (value: unknown) => Array.isArray(value) ? value.join("、") : typeof value === "number" ? value.toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : String(value ?? "—");
const money = (value: unknown) => typeof value === "number" ? `¥${fmt(value)}` : "—";
const sum = (rows: LiveRow[], key: string) => rows.reduce((value, row) => value + (typeof row[key] === "number" ? row[key] as number : 0), 0);
const selectClass = "h-10 max-w-full rounded-md border border-input bg-background px-3 text-sm";

function Records({ rows, columns, onCouponClick, onDepartmentClick, onHolderClick, emptyMessage = "当前范围暂无记录" }: {
  rows: LiveRow[]; columns: LiveColumn[]; onCouponClick?: (coupon: string) => void;
  onDepartmentClick?: (row: LiveRow) => void; onHolderClick?: (holder: string) => void; emptyMessage?: string;
}) {
  const [page, setPage] = useState(0);
  const max = Math.max(0, Math.ceil(rows.length / 50) - 1);
  const current = Math.min(page, max);
  return <div className="min-w-0 space-y-3">
    <div className="max-w-full overflow-x-auto rounded-md border"><Table>
      <TableHeader><TableRow>{columns.map(([key, label]) => <TableHead className="whitespace-nowrap" key={key}>{label}</TableHead>)}</TableRow></TableHeader>
      <TableBody>{rows.slice(current * 50, current * 50 + 50).map((row, index) => <TableRow key={index}
        className={onCouponClick || onDepartmentClick || onHolderClick ? "cursor-pointer hover:bg-blue-50/60" : undefined}
        onClick={onCouponClick ? () => onCouponClick(String(row.coupon_type)) : onDepartmentClick ? () => onDepartmentClick(row) : onHolderClick ? () => onHolderClick(String(row.holder_member_no)) : undefined}>
        {columns.map(([key]) => <TableCell key={key} className="whitespace-nowrap tabular-nums">
          {key === "coupon_type" && onCouponClick ? <button type="button"
            className="inline-flex min-h-10 items-center gap-1 rounded px-2 font-semibold text-blue-700 underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`查看${row.coupon_type}券各部门使用情况`}
            onClick={event => { event.stopPropagation(); onCouponClick(String(row.coupon_type)); }}>
            {fmt(row[key])}券<ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button> : key === "department" && onDepartmentClick ? <button type="button"
            className="inline-flex min-h-10 items-center gap-1 rounded px-2 font-semibold text-blue-700 underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`查看${row.department}柜组使用情况`} data-department-code={String(row.department_code || "")}
            onClick={event => { event.stopPropagation(); onDepartmentClick(row); }}>
            {fmt(row[key])}<ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button> : key === "period_own_sales" && onHolderClick ? <button type="button"
            className="inline-flex min-h-10 items-center gap-1 rounded px-2 font-semibold text-blue-700 underline underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`查看会员${row.holder_member_no}所选期间其他消费`} data-holder={String(row.holder_member_no)}
            onClick={event => { event.stopPropagation(); onHolderClick(String(row.holder_member_no)); }}>
            {fmt(row[key])}<ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button> : fmt(row[key])}
        </TableCell>)}
      </TableRow>)}{!rows.length && <TableRow><TableCell className="h-24 text-center text-muted-foreground" colSpan={columns.length}>{emptyMessage}</TableCell></TableRow>}</TableBody>
    </Table></div>
    {rows.length > 50 && <div className="flex flex-wrap items-center justify-between gap-2 text-sm"><span>共 {rows.length} 行 · 每页 50 行</span><div className="flex items-center gap-2">
      <Button variant="outline" size="sm" disabled={!current} onClick={() => setPage(current - 1)}>上一页</Button>
      {current + 1} / {max + 1}<Button variant="outline" size="sm" disabled={current >= max} onClick={() => setPage(current + 1)}>下一页</Button>
    </div></div>}
  </div>;
}

export default function CouponLivePage() {
  const { menuUser, adminViewLoading, loading } = useAuth();
  const [end, setEnd] = useState("");
  const [range, setRange] = useState<LiveQueryRange | null>(null);
  const [draftStart, setDraftStart] = useState("2026-09-18");
  const [draftEnd, setDraftEnd] = useState(shanghaiToday);
  const [auto, setAuto] = useState(true);
  const [coupon, setCoupon] = useState("E");
  const [member, setMember] = useState("");
  const [ticketCoupon, setTicketCoupon] = useState("all");
  const [activeTab, setActiveTab] = useState<LiveTab>("overview");
  const [selectedHolder, setSelectedHolder] = useState<string | null>(null);
  const [holderMode, setHolderMode] = useState<HolderDetailMode>("other");
  const [exportError, setExportError] = useState("");
  const memberPanelRef = useRef<HTMLDivElement>(null);
  const memberHeadingRef = useRef<HTMLHeadingElement>(null);
  const returningToMembers = useRef<string | null>(null);
  const openHolder = (holder: string) => { setSelectedHolder(holder); setHolderMode("other"); };
  const returnToMembers = () => { returningToMembers.current = selectedHolder; setSelectedHolder(null); };
  useEffect(() => {
    returningToMembers.current = null;
    setSelectedHolder(null);
    setHolderMode("other");
    setExportError("");
  }, [menuUser?.user_id, end, range?.start, range?.end, coupon, member, activeTab]);
  useEffect(() => {
    if (selectedHolder) {
      memberPanelRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
      memberHeadingRef.current?.focus({ preventScroll: true });
    } else if (returningToMembers.current) {
      Array.from(memberPanelRef.current?.querySelectorAll<HTMLButtonElement>("button[data-holder]") || [])
        .find(button => button.dataset.holder === returningToMembers.current)?.focus();
      returningToMembers.current = null;
    }
  }, [selectedHolder]);
  const [departmentCoupon, setDepartmentCoupon] = useState<string | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState<LiveDepartment | null>(null);
  const overviewRef = useRef<HTMLDivElement>(null);
  const departmentHeadingRef = useRef<HTMLHeadingElement>(null);
  const returningToSummary = useRef<string | null>(null);
  const returningToDepartment = useRef<LiveDepartment | null>(null);
  const openDepartments = (selectedCoupon: string) => {
    setSelectedDepartment(null);
    setDepartmentCoupon(selectedCoupon);
  };
  const openGroups = (row: LiveRow) => setSelectedDepartment({ code: String(row.department_code || ""), name: String(row.department) });
  const returnToDepartments = () => {
    returningToDepartment.current = selectedDepartment;
    setSelectedDepartment(null);
  };
  const returnToSummary = () => {
    returningToSummary.current = departmentCoupon;
    setSelectedDepartment(null);
    setDepartmentCoupon(null);
  };
  useEffect(() => {
    // A different viewer/period must not inherit an old department selection.
    returningToSummary.current = null;
    returningToDepartment.current = null;
    setSelectedDepartment(null);
    setDepartmentCoupon(null);
  }, [menuUser?.user_id, end, range?.start, range?.end]);
  useEffect(() => {
    if (!departmentCoupon && !returningToSummary.current) return;
    overviewRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
    if (departmentCoupon) {
      const previous = returningToDepartment.current;
      const button = previous && !selectedDepartment
        ? Array.from(overviewRef.current?.querySelectorAll("button") || []).find(element =>
          element.getAttribute("aria-label") === `查看${previous.name}柜组使用情况`
          && element.dataset.departmentCode === previous.code)
        : undefined;
      (button || departmentHeadingRef.current)?.focus({ preventScroll: true });
      returningToDepartment.current = null;
    }
    else {
      const label = `查看${returningToSummary.current}券各部门使用情况`;
      const button = Array.from(overviewRef.current?.querySelectorAll("button") || [])
        .find(element => element.getAttribute("aria-label") === label);
      button?.focus({ preventScroll: true });
      returningToSummary.current = null;
    }
  }, [departmentCoupon, selectedDepartment]);
  const query = useQuery<LiveReport>({
    queryKey: ["coupon-live", menuUser?.user_id, end, range?.start, range?.end],
    queryFn: () => apiGet(couponLiveQueryUrl(end, range)),
    enabled: Boolean(menuUser) && !adminViewLoading && !loading,
    staleTime: 0, gcTime: 0, retry: false,
    refetchInterval: auto ? 60_000 : false, refetchIntervalInBackground: false,
  });
  // Do not keep privileged/stale data visible on a scope switch or denied refresh.
  const data = !query.isError && !adminViewLoading && !loading ? query.data : undefined;
  useEffect(() => {
    if (data?.query_start && data?.query_end) {
      setDraftStart(data.query_start);
      setDraftEnd(data.query_end);
    }
  }, [data?.query_start, data?.query_end]);
  const today = data?.today || shanghaiToday();
  const validTo = end || data?.valid_to || today;
  const lastQueryDate = validTo < today ? validTo : today;
  const firstQueryDate = data?.tracking_start || "2026-09-18";
  const rangeError = validateLiveQueryRange({ start: draftStart, end: draftEnd }, firstQueryDate, lastQueryDate);
  const applyRange = () => {
    if (rangeError) return;
    if (range?.start === draftStart && range.end === draftEnd) void query.refetch();
    else setRange({ start: draftStart, end: draftEnd });
  };
  const resetRange = () => {
    setDraftStart(firstQueryDate);
    setDraftEnd(lastQueryDate);
    setRange(null);
  };
  const ready = data?.status === "ready";
  const rows = data?.coupons || [];
  const full = data?.scope?.mode === "full_store";
  const trajectory = filterTrajectory(data?.trajectory || [], coupon, member);
  const ticketRows = (data?.tickets || []).filter(row => ticketCoupon === "all" || row.coupon_type === ticketCoupon);
  const departmentRows = filterCouponDepartments(data?.departments || [], departmentCoupon);
  const groupRows = filterCouponGroups(data?.groups || [], departmentCoupon, selectedDepartment);
  const showingDepartments = activeTab === "overview" && departmentCoupon !== null;
  const holderRows = data ? summarizeHolderPeriod(data, coupon, member) : [];
  const currentHolder = holderRows.find(row => row.holder_member_no === selectedHolder);
  const memberDetails = data ? holderPeriodDetails(data, coupon, member, selectedHolder, holderMode) : [];
  const membersReady = Boolean(data && hasMemberPeriodData(data));
  const exportWithMembers = includesMemberSheets(activeTab, departmentCoupon) && membersReady;
  const exportDisabled = !ready || !data || query.isFetching || adminViewLoading || loading
    || (activeTab === "members" && !membersReady);
  const exportCurrent = () => {
    if (exportDisabled || !data) return;
    try {
      setExportError("");
      exportLiveWorkbook(data, { tab: activeTab, coupon, member, ticketCoupon,
        departmentCoupon, department: selectedDepartment, holder: selectedHolder, detailMode: holderMode });
    } catch (error) { setExportError(error instanceof Error ? error.message : "导出失败，请重试"); }
  };
  return <div className="w-full min-w-0 space-y-6 p-4 md:p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h1 className="text-2xl font-semibold">秋v卡券跟进</h1><p className="mt-2 text-sm text-muted-foreground">购物中心 · {LIVE_COUPON_TYPES.join(" / ")} · 从 2026-09-18 起跟进，不需要活动建档</p></div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={auto} onChange={event => setAuto(event.target.checked)} />每60秒刷新</label>
        <Button variant="outline" disabled={query.isFetching || adminViewLoading} onClick={() => void query.refetch()}>
          {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}刷新数据</Button>
        <Button variant="outline" disabled={exportDisabled} onClick={exportCurrent} title="导出当前标签及筛选下全部匹配记录，不限页面50行">
          <Download className="mr-2 h-4 w-4" />{exportWithMembers ? "导出Excel（含会员汇总）" : "导出当前视图Excel"}</Button>
      </div>
    </div>
    {query.isError && <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-red-700">{query.error instanceof Error ? query.error.message : "数据读取失败，请刷新重试"}</div>}
    {exportError && <p role="alert" className="text-red-700">{exportError}</p>}
    {exportWithMembers && <p className="text-sm text-muted-foreground">Excel附带“会员期间汇总”和“会员期间明细”，消费统计期：{data?.query_start} 至 {data?.query_end}；会员筛选：{coupon === "all" ? "任一跟踪券" : `${coupon}券`}{member.trim() ? ` · 卡号包含 ${member.trim()}` : " · 全部匹配会员"}。与“会员期间汇总”标签内的筛选一致。</p>}
    {(query.isLoading || adminViewLoading || loading) && <p role="status" className="py-8 text-muted-foreground">正在读取卡券日志与销售数据…</p>}
    <Card><CardContent className="space-y-3 p-4 text-sm">
      {data && <div className="flex flex-wrap items-center gap-3"><span>本档券有效期：{data.tracking_start} 至</span>
        <select aria-label="券有效期结束日" className={selectClass} value={end || data.valid_to || ""} onChange={event => { setEnd(event.target.value); setRange(null); }}>
          <option value="">{data.status === "choose_period" ? "日志存在多种有效期，请选择" : "自动识别"}</option>
          {data.periods.map(period => <option value={period.valid_to} key={period.valid_to}>{period.valid_to}</option>)}
        </select><span>{data.scope?.label}</span>
      </div>}
      <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); applyRange(); }}>
        <label className="space-y-1" htmlFor="live-query-start"><span className="block">查询开始日期</span>
          <Input id="live-query-start" className="w-44" type="date" min={firstQueryDate} max={lastQueryDate} value={draftStart} onChange={event => setDraftStart(event.target.value)} /></label>
        <label className="space-y-1" htmlFor="live-query-end"><span className="block">查询结束日期</span>
          <Input id="live-query-end" className="w-44" type="date" min={firstQueryDate} max={lastQueryDate} value={draftEnd} onChange={event => setDraftEnd(event.target.value)} /></label>
        <Button type="submit" disabled={!!rangeError || query.isFetching || adminViewLoading || loading}>查询</Button>
        <Button type="button" variant="outline" disabled={query.isFetching} onClick={resetRange}>本档至今</Button>
      </form>
      {rangeError && <p role="alert" className="text-red-700">{rangeError}</p>}
      {ready && <><p>使用统计：{data.query_start} 至 {data.query_end}；核销、退券、连带销售及部门/柜组按所选日期统计。</p>
        <p>发放为截至 {data.query_end} 的本档累计，含提前发券；“持券人今日轨迹”查看所选期间用券持券人在今天的消费。</p>
        <p className="text-muted-foreground">读取时间：{data.generated_at?.replace("T", " ").slice(0, 19)} · 可见券日志最新业务日：{data.latest_visible_coupon_date || "暂无"} · 可见销售最新时间：{data.latest_visible_sale || "暂无"}</p>
        <p className="text-xs text-muted-foreground">刷新读取已同步的数据，不代表ERP即时推送；最新业务时间不是同步完成时间。</p></>}
      {data?.status === "no_period" && <p>尚未找到从9月18日开始有效的跟踪券日志，请待数据同步后刷新。不会用其他档期替代。</p>}
    </CardContent></Card>
    {ready && <>
      {!full && <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">已按账号数据权限过滤。整店发券资产数和金额不展示；跨部门小票只显示可见商品行，券额按商品销售收入绝对值比例分摊（估算归属）。</div>}
      {!!((data.quality?.unmatched_flow_count || 0) + (data.quality?.missing_issue_flow_count || 0) + (data.quality?.missing_sales_flow_count || 0)) && <div role="status" className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        待核对：{data.quality?.unmatched_flow_count} 条券流水未唯一匹配小票，{data.quality?.missing_issue_flow_count} 条券流水缺少初始发券记录，{data.quality?.missing_sales_flow_count} 条券流水的小票缺少商品明细。券额与连带销售覆盖范围可能不同，请勿视为完整对账。
      </div>}
      {!showingDepartments && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[[full ? "本档累计发券金额" : "本范围核销券额", money(sum(rows, full ? "issued_amount" : "redeemed_amount")), full ? "含提前发券，按初始发券记录" : "商品行比例分摊"],
          ["净用券额", money(sum(rows, "net_coupon_amount")), "核销券额 − 退券额（均冲正后）"],
          ["净连带销售", money(sum(rows, "linked_sales")), "用券关联销售 − 已关联实际退货"],
          ["用券持券人数", fmt(data.distinct_used_members), `${fmt(data.distinct_use_tickets)} 张核销小票 · 跨券去重`],
        ].map(([label, value, note]) => <Card key={label}><CardHeader className="pb-2"><CardTitle className="text-sm font-normal">{label}</CardTitle></CardHeader><CardContent><p className="text-2xl font-semibold tabular-nums">{value}</p><p className="mt-2 text-xs text-muted-foreground">{note}</p></CardContent></Card>)}
      </div>}
      <Tabs value={activeTab} onValueChange={value => { setActiveTab(value as LiveTab); setDepartmentCoupon(null); setSelectedDepartment(null); }} className="min-w-0"><TabsList className="h-auto max-w-full flex-wrap"><TabsTrigger value="overview">发放与使用</TabsTrigger><TabsTrigger value="tickets">销售退货明细</TabsTrigger><TabsTrigger value="trajectory">持券人今日轨迹</TabsTrigger><TabsTrigger value="members">会员期间汇总</TabsTrigger></TabsList>
        <TabsContent ref={overviewRef} value="overview" className="min-w-0 scroll-mt-40 space-y-5">
          {departmentCoupon ? <Card className="min-w-0"><CardHeader className="space-y-3">
            {selectedDepartment
              ? <Button variant="outline" className="w-fit" onClick={returnToDepartments}><ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />返回{departmentCoupon}券部门列表</Button>
              : <Button variant="outline" className="w-fit" onClick={returnToSummary}><ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />返回卡券汇总</Button>}
            <h2 ref={departmentHeadingRef} tabIndex={-1} className="text-lg font-semibold focus:outline-none">{selectedDepartment
              ? `${departmentCoupon}券 · ${selectedDepartment.name} · 柜组使用情况`
              : `${departmentCoupon}券各部门使用情况`}</h2>
            <p className="text-sm text-muted-foreground">{data.scope?.label} · {data.query_start} 至 {data.query_end} · 金额单位：元</p>
          </CardHeader><CardContent className="min-w-0 space-y-3">
            {selectedDepartment ? <>
              <Records key={JSON.stringify([departmentCoupon, selectedDepartment])} rows={groupRows} columns={groupColumns}
                emptyMessage={data.groups ? `当前权限范围内，该部门暂无${departmentCoupon}券柜组使用记录` : "柜组数据尚未返回，请刷新数据"} />
              <p className="text-xs text-muted-foreground">仅展示{selectedDepartment.name}内获授权且有{departmentCoupon}券记录的柜组；分摊口径与部门页一致，退货按原用券小票关联扣减。</p>
            </> : <>
              <p className="text-sm text-muted-foreground">点击部门或所在行，查看该部门的柜组使用情况。</p>
              <Records key={departmentCoupon} rows={departmentRows} columns={departmentColumns.filter(([key]) => key !== "coupon_type")}
                onDepartmentClick={openGroups} emptyMessage={`当前权限范围内，暂无${departmentCoupon}券部门使用记录`} />
              <p className="text-xs text-muted-foreground">仅展示{departmentCoupon}券在当前权限范围内有记录的部门；跨部门小票券额仍按商品销售收入绝对值比例分摊。</p>
            </>}
          </CardContent></Card> : <>
          <Card className="min-w-0"><CardHeader><CardTitle className="text-base">卡券汇总</CardTitle><p className="text-sm text-muted-foreground">点击券种或所在行，查看该券各部门使用情况。</p></CardHeader><CardContent className="min-w-0 space-y-3"><Records rows={rows} columns={couponColumns} onCouponClick={openDepartments} /><p className="text-xs text-muted-foreground">发券按资产去重；核销人数、小票数跨券可能重叠，不能直接相加。净连带销售是关联金额，不等于销售增长。</p></CardContent></Card>
          <Card><CardHeader><CardTitle className="text-base">每日使用与关联销售（元）</CardTitle></CardHeader><CardContent>
            {data.daily?.length ? <div className="h-72 min-w-0"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.daily} margin={{ top: 8, right: 12, left: 12, bottom: 8 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="day" /><YAxis tickFormatter={value => Number(value).toLocaleString("zh-CN")} /><Tooltip formatter={value => money(Number(value))} /><Legend /><Bar dataKey="net_coupon_amount" name="净用券额" fill="#0d9488" /><Bar dataKey="linked_sales" name="净连带销售" fill="#2563eb" /></BarChart></ResponsiveContainer></div> : <p className="py-8 text-center text-muted-foreground">暂无可绘制的使用数据</p>}
          </CardContent></Card>
          </>}
        </TabsContent>
        <TabsContent value="tickets" className="min-w-0 space-y-4"><div className="flex flex-wrap items-center gap-3"><label htmlFor="live-ticket-coupon">券种</label><select id="live-ticket-coupon" className={selectClass} value={ticketCoupon} onChange={event => setTicketCoupon(event.target.value)}><option value="all">全部跟踪券</option>{LIVE_COUPON_TYPES.map(c => <option key={c}>{c}</option>)}</select></div>
          <p className="text-sm text-muted-foreground">统计 {data.query_start} 至 {data.query_end} 的销售和退货。同票多券按跟踪券有效核销金额分摊；实际退货通过原小票关联扣减，即使原销售在查询开始日期之前也会追溯，不以是否退券为准。本档结束后的退货不计入本页，也不串入下一档。</p>
          <Records rows={ticketRows} columns={ticketColumns} />
        </TabsContent>
        <TabsContent value="trajectory" className="min-w-0 space-y-4"><div className="flex flex-wrap items-center gap-3"><label htmlFor="live-holder-coupon">所选期间用过</label><select id="live-holder-coupon" className={selectClass} value={coupon} onChange={event => setCoupon(event.target.value)}><option value="all">任一跟踪券</option>{LIVE_COUPON_TYPES.map(c => <option value={c} key={c}>{c} 券</option>)}</select><Input className="w-60" aria-label="查找持券会员卡" placeholder="查找持券会员卡" value={member} onChange={event => setMember(event.target.value)} /></div>
          <p className="text-sm text-muted-foreground">查看这些持券人在今天（{data.today}）的购物会员消费，以及使用本人券关联的小票。只展示权限范围内的记录；会员不一致是待核查线索，不直接认定代付。多人关联同票会重复展示，请勿直接加总本表。</p>
          <Records rows={trajectory} columns={trajectoryColumns} />
        </TabsContent>
        <TabsContent ref={memberPanelRef} value="members" className="min-w-0 scroll-mt-40 space-y-4">
          <div className="flex flex-wrap items-center gap-3"><label htmlFor="live-member-coupon">所选期间用过</label>
            <select id="live-member-coupon" className={selectClass} value={coupon} onChange={event => setCoupon(event.target.value)}>
              <option value="all">任一跟踪券</option>{LIVE_COUPON_TYPES.map(c => <option value={c} key={c}>{c} 券</option>)}
            </select><Input className="w-60" aria-label="筛选汇总持券会员卡" placeholder="查找持券会员卡" value={member} onChange={event => setMember(event.target.value)} />
            <Button variant="outline" disabled={exportDisabled} onClick={exportCurrent}>
              <Download className="mr-2 h-4 w-4" />{selectedHolder ? "导出该会员汇总及明细" : "导出会员汇总及明细"}</Button></div>
          <p className="text-sm text-muted-foreground">{data.scope?.label} · 消费统计期：{data.query_start} 至 {data.query_end}（含首尾日期）。人群为所选期间用过所选券的持券人。本人合计按该期间购物会员卡归属，含该期间实际退货负数；与持券卡不一致或未登记会员的小票单列，不计入本人合计。</p>
          <p className="text-sm text-muted-foreground">“其他消费”是本人小票中未关联{coupon === "all" ? "任一跟踪券" : `${coupon}券`}的消费，仍可能使用其他券；退货按原小票分类。点击销售金额或会员行查看明细。</p>
          {!membersReady ? <p role="status" className="rounded-md border p-6 text-muted-foreground">所选期间会员数据尚未返回，请刷新数据并确认后端已更新；不会用今日数据替代或将未查询数据显示为零。</p>
            : selectedHolder ? <Card className="min-w-0"><CardHeader className="space-y-3">
              <Button variant="outline" className="w-fit" onClick={returnToMembers}><ArrowLeft className="mr-2 h-4 w-4" />返回会员汇总</Button>
              <h2 ref={memberHeadingRef} tabIndex={-1} className="text-lg font-semibold focus:outline-none">会员 {selectedHolder} · {data.query_start} 至 {data.query_end} 消费明细</h2>
              <p className="text-sm">所选期间本人合计销售：{money(currentHolder?.period_own_sales)} · 其中其他消费：{money(currentHolder?.period_other_sales)}</p>
            </CardHeader><CardContent className="min-w-0 space-y-4">
              <div className="flex flex-wrap items-center gap-3"><label htmlFor="live-member-detail-mode">明细范围</label>
                <select id="live-member-detail-mode" className={selectClass} value={holderMode} onChange={event => setHolderMode(event.target.value as HolderDetailMode)}>
                  {Object.entries(holderDetailLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select></div>
              <Records key={`${selectedHolder}:${holderMode}`} rows={memberDetails} columns={holderDetailColumns}
                emptyMessage="该会员在当前权限及明细筛选下，所选期间暂无可见记录" />
            </CardContent></Card> : <Records key={`${coupon}:${member}`} rows={holderRows} columns={holderColumns} onHolderClick={openHolder}
              emptyMessage="所选期间及当前权限范围内，暂无符合筛选的用券持券人" />}
          <p className="text-xs text-muted-foreground">会员汇总导出包含全部匹配会员及所选期间明细；进入单个会员后，导出该会员汇总和当前明细范围。金额仅代表已同步的可见商品行，不扩大账号权限。</p>
        </TabsContent>
      </Tabs>
      <details className="rounded-md border p-4 text-sm"><summary className="cursor-pointer font-medium">数据与计算口径</summary><div className="mt-3 space-y-2 text-muted-foreground">
        <p>来源：ERP卡券日志 tktcardfqlog、销售小票 salehead / salegoodslist、组织与品牌主档。最初发券确定来源，后续核销、退券只影响金额。</p>
        <p>核销券额 = O − U；退券额 = P − V；净用券额 = 核销券额 − 退券额。金额均以日志绝对值计算，冲正单独扣除。</p>
        <p>净连带销售按小票商品行销售收入计算；退货沿原小票归属。购物会员与持券会员分开，未登记会员的小票不推断为本人购物。未能关联的原单不擅自分配。</p>
        <p>沿用“活动建档与分析”的查看功能权限，数据范围由后端逐行校验。当前页面不读取活动建档表、不写业务数据、不做同星期对比。</p>
      </div></details>
    </>}
  </div>;
}
