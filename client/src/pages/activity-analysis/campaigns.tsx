import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, Plus, RefreshCw } from "lucide-react";
import { apiGet, apiPost, apiRequest } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  type Campaign, type CampaignReport, type CampaignRow, type CampaignColumn, type CampaignSalesLift,
  couponColumns, memberColumns, ticketColumns, ruleColumns, levelColumns, brandColumns,
  exportCampaignWorkbook, filterCampaigns, qualityLabels,
  assetColumns, flowColumns, brandDetailColumns, postReturnColumns,
} from "@/lib/coupon-campaign";

const root = "/api/activity-analysis/campaigns";
const fmt = (v: unknown) => typeof v === "number" ? v.toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : typeof v === "boolean" ? (v ? "是" : "否") : String(v ?? "—");
const money = (v: number | undefined) => typeof v === "number" ? `¥${v.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}` : "—";
const percent = (v: number | undefined) => typeof v === "number" ? `${v >= 0 ? "+" : ""}${v.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}%` : "—";
const errorText = (e: unknown) => e instanceof Error ? e.message : "请求未完成";
const selectClass = "h-10 rounded-md border border-input bg-background px-3 text-sm";

function DataTable({ rows, columns, onMember, onAsset, onBill }: { rows: CampaignRow[]; columns: CampaignColumn[]; onMember?: (member: string) => void; onAsset?: (row: CampaignRow) => void; onBill?: (bill: string) => void }) {
  const [page, setPage] = useState(0);
  const maxPage = Math.max(0, Math.ceil(rows.length / 100) - 1);
  const shownPage = Math.min(page, maxPage);
  return <div className="space-y-3">
    <div className="overflow-x-auto rounded-md border"><Table><TableHeader><TableRow>
      {columns.map(([k, label]) => <TableHead className="whitespace-nowrap" key={k}>{label}</TableHead>)}
    </TableRow></TableHeader><TableBody>
      {rows.slice(shownPage * 100, shownPage * 100 + 100).map((r, i) => <TableRow key={i}>
        {columns.map(([k]) => <TableCell className="whitespace-nowrap tabular-nums" key={k}>
          {k === "member_no" && onMember ? <button className="text-blue-700 underline" onClick={() => onMember(String(r[k]))}>{fmt(r[k])}</button>
            : k === "asset_id" && onAsset ? <button className="text-blue-700 underline" onClick={() => onAsset(r)}>{fmt(r[k])}</button>
            : k === "billno" && onBill && r[k] ? <button className="text-blue-700 underline" onClick={() => onBill(String(r[k]))}>{fmt(r[k])}</button> : fmt(r[k])}
        </TableCell>)}
      </TableRow>)}
      {!rows.length && <TableRow><TableCell colSpan={columns.length} className="h-24 text-center">暂无数据</TableCell></TableRow>}
    </TableBody></Table></div>
    <div className="flex items-center justify-between text-sm text-muted-foreground"><span>共 {rows.length} 行；每页 100 行，导出包含全部明细</span>
      <div className="flex items-center gap-2"><Button variant="outline" size="sm" disabled={!shownPage} onClick={() => setPage(shownPage - 1)}>上一页</Button>
        {shownPage + 1} / {maxPage + 1}<Button variant="outline" size="sm" disabled={shownPage >= maxPage} onClick={() => setPage(shownPage + 1)}>下一页</Button></div>
    </div>
  </div>;
}

function SalesLiftPanel({ lift }: { lift: CampaignSalesLift }) {
  if (!lift || lift.status !== "estimated") {
    return <Card><CardContent className="p-6"><p className="font-medium">暂不能生成销售增长试算</p>
      <p className="mt-2 text-sm text-muted-foreground">{lift?.reason || "未返回试算结果"}</p></CardContent></Card>;
  }
  const positive = (lift.estimated_increment || 0) >= 0;
  const activityPeriod = lift.activity_start_date && lift.activity_end_date
    ? `${lift.activity_start_date} 至 ${lift.activity_end_date}` : "未记录";
  const baselinePeriods = (lift.baseline_periods || [])
    .map(period => `前${period.week_no}周 ${period.start_date} 至 ${period.end_date}`)
    .join("；");
  return <div className="space-y-4">
    <div role="status" className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
      <p>这是参考估算，不是结算结果，也不能单独证明活动因果增量。当前按冻结收券范围、前 {lift.baseline_weeks} 周同星期及同部门非参与柜组校准。</p>
      <p className="mt-2"><span className="font-medium">活动期：</span>{activityPeriod}</p>
      <p className="mt-1"><span className="font-medium">历史同星期基准日期：</span>{baselinePeriods || "未记录"}{baselinePeriods ? `（${lift.baseline_weeks}组日期取平均）` : ""}</p>
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {[
        ["参与范围活动期净销售", money(lift.actual_sales), `${lift.day_count}天 · ${lift.treatment_group_count}个参与柜组`],
        ["历史同星期基准", money(lift.same_weekday_baseline_sales), `未经校准 ${percent(lift.raw_change_rate)}`],
        ["校准后预计销售", money(lift.expected_sales), `对照范围变化 ${percent(lift.control_change_rate)}`],
        ["估算净增量", money(lift.estimated_increment), `估算增长率 ${percent(lift.estimated_growth_rate)}`],
      ].map(([label, value, note], index) => <Card key={label}><CardHeader className="pb-2"><CardTitle className="text-sm font-normal">{label}</CardTitle></CardHeader>
        <CardContent><p className={`text-2xl font-semibold tabular-nums ${index === 3 ? (positive ? "text-emerald-700" : "text-red-700") : ""}`}>{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{note}</p></CardContent></Card>)}
    </div>
    <Card><CardHeader><CardTitle className="text-base">试算过程</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
      <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>范围</TableHead><TableHead className="text-right">历史同星期基准</TableHead><TableHead className="text-right">活动期实际</TableHead><TableHead className="text-right">变化</TableHead></TableRow></TableHeader>
        <TableBody><TableRow><TableCell>参与收券范围</TableCell><TableCell className="text-right tabular-nums">{money(lift.same_weekday_baseline_sales)}</TableCell><TableCell className="text-right tabular-nums">{money(lift.actual_sales)}</TableCell><TableCell className="text-right tabular-nums">{percent(lift.raw_change_rate)}</TableCell></TableRow>
          <TableRow><TableCell>同部门非参与柜组</TableCell><TableCell className="text-right tabular-nums">{money(lift.control_baseline_sales)}</TableCell><TableCell className="text-right tabular-nums">{money(lift.control_actual_sales)}</TableCell><TableCell className="text-right tabular-nums">{percent(lift.control_change_rate)}</TableCell></TableRow></TableBody></Table></div>
      <p className="text-muted-foreground">预计销售 = 参与范围历史同星期基准 × 对照范围活动期/历史基准；估算净增量 = 参与范围实际净销售 − 预计销售。</p>
      <p className="text-muted-foreground">范围覆盖 {lift.department_count} 个部门；对照柜组 {lift.control_group_count} 个；参与柜组部门映射 {lift.mapped_treatment_group_count}/{lift.treatment_group_count}。</p>
    </CardContent></Card>
    <Card><CardHeader><CardTitle className="text-base">限制条件</CardTitle></CardHeader><CardContent><ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
      {(lift.caveats || []).map(item => <li key={item}>{item}</li>)}
    </ul></CardContent></Card>
  </div>;
}

export default function CouponCampaignsPage() {
  const { toast } = useToast();
  const client = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [memberFilter, setMemberFilter] = useState("");
  const [ticketMember, setTicketMember] = useState("");
  const [ticketBill, setTicketBill] = useState("");
  const [assetFilter, setAssetFilter] = useState("");
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [confirmationTarget, setConfirmationTarget] = useState<{ id: string; fingerprint: string; version: number; count: number } | null>(null);
  const [confirmationNote, setConfirmationNote] = useState("");
  const [mismatchOnly, setMismatchOnly] = useState(false);
  const [tab, setTab] = useState("coupons");
  const [campaignFilters, setCampaignFilters] = useState({ store_code: "", name: "", start_date: "", end_date: "" });
  const [form, setForm] = useState({ name: "", store_code: "", start_date: "", end_date: "", coupon_types: "B,E,H,M", erp_activity_id: "", notes: "" });
  const options = useQuery<{ stores: { store_code: string; store_name: string }[]; can_manage: boolean }>({ queryKey: [root, "options"], queryFn: () => apiGet(`${root}/options`) });
  const campaigns = useQuery<Campaign[]>({ queryKey: [root], queryFn: () => apiGet(root) });
  const filteredCampaigns = useMemo(
    () => campaignFilters.start_date && campaignFilters.end_date && campaignFilters.start_date > campaignFilters.end_date
      ? [] : filterCampaigns(campaigns.data || [], campaignFilters),
    [campaigns.data, campaignFilters],
  );
  const selected = (campaigns.data || []).find(c => String(c.id) === selectedId);
  const reportQuery = useQuery<CampaignReport>({ queryKey: [root, selectedId, "report"], queryFn: () => apiGet(`${root}/${selectedId}/report`), enabled: Boolean(selected), retry: false });
  const report = reportQuery.data;
  const rules = selected?.rule_snapshot;
  const anyError = options.error || campaigns.error || reportQuery.error;
  async function create() {
    setBusy(true);
    try {
      const payload = { ...form, coupon_types: form.coupon_types.split(/[,，、\s]+/).filter(Boolean) };
      const saved: Campaign = editingId
        ? await (await apiRequest(`${root}/${editingId}`, { method: "PUT", body: JSON.stringify(payload) })).json()
        : await apiPost<Campaign>(root, payload);
      await client.invalidateQueries({ queryKey: [root] });
      setCampaignFilters({ store_code: "", name: "", start_date: "", end_date: "" });
      setSelectedId(String(saved.id)); setCreateOpen(false);
      toast({ title: editingId ? "活动说明已更新" : "活动已建档", description: "归属字段已固定；可读取ERP规则并查看报告。" });
    } catch (e) { toast({ title: "建档失败", description: errorText(e), variant: "destructive" }); }
    finally { setBusy(false); }
  }
  async function refreshRules() {
    setBusy(true);
    try {
      await apiPost(`${root}/${selectedId}/erp-rules/refresh`, {});
      await client.invalidateQueries({ queryKey: [root] });
      toast({ title: "ERP规则快照已更新" });
    } catch (e) { toast({ title: "ERP规则未更新", description: errorText(e), variant: "destructive" }); }
    finally { setBusy(false); }
  }
  async function confirmOwnership() {
    if (!confirmationTarget) return;
    setBusy(true);
    try {
      await apiPost(`${root}/${confirmationTarget.id}/ownership/confirm`, {
        fingerprint: confirmationTarget.fingerprint, expected_version: confirmationTarget.version, note: confirmationNote.trim(),
      });
      setConfirmationOpen(false); setConfirmationNote("");
      await client.invalidateQueries({ queryKey: [root, confirmationTarget.id, "report"] });
      toast({ title: "券资产归属已确认并留痕" });
    } catch (e) { toast({ title: "归属未确认", description: errorText(e), variant: "destructive" }); }
    finally { setBusy(false); }
  }
  function showBill(bill: string) { setTicketBill(bill); setTicketMember(""); setMismatchOnly(false); setTab("tickets"); }
  const members = (report?.members || []).filter(r => String(r.member_no).includes(memberFilter));
  const tickets = (report?.tickets || []).filter(r => (!ticketBill || r.billno === ticketBill) && (!ticketMember || r.member_no === ticketMember) && (!mismatchOnly || r.member_match !== "一致"));
  const flows = (report?.coupon_flows || []).filter(r => !assetFilter || `${r.coupon_type}:${r.asset_id}` === assetFilter);
  const hasQuality = Object.values(report?.quality || {}).some(v => v > 0);
  function updateCampaignFilter(key: keyof typeof campaignFilters, value: string) {
    setCampaignFilters(previous => ({ ...previous, [key]: value }));
    setSelectedId("");
  }
  return <div className="space-y-6 p-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-semibold">活动建档与分析</h1>
      <p className="mt-1 text-sm text-muted-foreground">固定活动归属 · 持券人分析 · 销售退货独立核算</p></div>
      {options.data?.can_manage && <div className="flex gap-2">
        {selected && <Button variant="outline" onClick={() => { setEditingId(selected.id); setForm({ name: selected.name, store_code: selected.store_code, start_date: selected.start_date, end_date: selected.end_date, coupon_types: selected.coupon_types.join(","), erp_activity_id: selected.erp_activity_id, notes: selected.notes }); setCreateOpen(true); }}>编辑说明/ERP编号</Button>}
        <Button onClick={() => { setEditingId(null); setForm({ name: "", store_code: "", start_date: "", end_date: "", coupon_types: "B,E,H,M", erp_activity_id: "", notes: "" }); setCreateOpen(true); }}><Plus className="mr-2 h-4 w-4" />新建活动</Button>
      </div>}
    </div>
    <Card><CardContent className="space-y-4 p-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-2"><Label htmlFor="campaign-filter-store">门店</Label><select id="campaign-filter-store" className={`${selectClass} block w-full`} value={campaignFilters.store_code} onChange={e => updateCampaignFilter("store_code", e.target.value)}>
          <option value="">全部门店</option>{options.data?.stores.map(store => <option key={store.store_code} value={store.store_code}>{store.store_name}（{store.store_code}）</option>)}</select></div>
        <div className="space-y-2"><Label htmlFor="campaign-filter-name">活动名称</Label><Input id="campaign-filter-name" value={campaignFilters.name} onChange={e => updateCampaignFilter("name", e.target.value)} placeholder="输入活动名称" /></div>
        <div className="space-y-2"><Label htmlFor="campaign-filter-start">开始时间</Label><Input id="campaign-filter-start" type="date" value={campaignFilters.start_date} onInput={e => updateCampaignFilter("start_date", e.currentTarget.value)} onChange={e => updateCampaignFilter("start_date", e.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="campaign-filter-end">结束时间</Label><Input id="campaign-filter-end" type="date" value={campaignFilters.end_date} onInput={e => updateCampaignFilter("end_date", e.currentTarget.value)} onChange={e => updateCampaignFilter("end_date", e.target.value)} /></div>
      </div>
      <div className="flex flex-wrap items-end gap-4"><div className="min-w-72 flex-1 space-y-2"><Label htmlFor="campaign-select">已建档活动（{filteredCampaigns.length}）</Label>
        <select id="campaign-select" className={`${selectClass} block w-full`} value={selectedId} onChange={e => { setSelectedId(e.target.value); setTicketMember(""); setMemberFilter(""); setTicketBill(""); setAssetFilter(""); }}>
          <option value="">{filteredCampaigns.length ? "请选择活动" : "当前条件下无活动"}</option>{filteredCampaigns.map(c => <option key={c.id} value={c.id}>{c.name} · {c.store_code} · {c.start_date}～{c.end_date}</option>)}
        </select></div>
        <Button variant="outline" onClick={() => { setCampaignFilters({ store_code: "", name: "", start_date: "", end_date: "" }); setSelectedId(""); }}>清空筛选</Button>
        <Button variant="outline" disabled={!selected || reportQuery.isFetching} onClick={() => reportQuery.refetch()}><RefreshCw className="mr-2 h-4 w-4" />刷新报告</Button>
        <Button variant="outline" disabled={!report || reportQuery.isFetching || Boolean(reportQuery.error)} onClick={() => report && exportCampaignWorkbook(report)}><Download className="mr-2 h-4 w-4" />导出Excel</Button>
      </div>
      {campaignFilters.start_date && campaignFilters.end_date && campaignFilters.start_date > campaignFilters.end_date
        ? <p className="text-xs text-red-600">结束时间不能早于开始时间。</p>
        : <p className="text-xs text-muted-foreground">开始、结束时间按活动档期落入所选区间筛选。</p>}
    </CardContent></Card>
    {anyError && <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-red-700">{errorText(anyError)}</div>}
    {!selected && !campaigns.isLoading && <Card><CardContent className="p-8 text-center text-muted-foreground">先新建或选择活动。按门店、券种和初始有效期生成候选范围，人工确认后固定券资产集合。</CardContent></Card>}
    {reportQuery.isFetching && <p className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />正在关联发券、核销、小票退货及会员数据…</p>}
    {selected && <p className="text-sm text-muted-foreground">门店 {selected.store_code} · {selected.start_date} 至 {selected.end_date} · 券种 {selected.coupon_types.join("、")} · ERP档期 {selected.erp_activity_id || "未关联"}</p>}
    {report && <>
      {report.ownership && <Card><CardHeader><CardTitle className="text-base">券资产归属 · {report.ownership.status_label}</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
        <p>候选 {report.ownership.candidate_assets} 张 · 本报告纳入 {report.ownership.report_assets} 张 · 确认版本 V{report.ownership.version}</p>
        <p className="text-muted-foreground">{report.ownership.basis} {report.ownership.change_basis}</p>
        <p>源日志未填写ERP档期：{report.ownership.missing_erp_period} 张；指向其他档期：{report.ownership.conflicting_erp_period} 张。</p>
        {report.ownership.version > 0 && <p>待确认新增 {report.ownership.unconfirmed_added} 张 · 已确认但本次缺失 {report.ownership.confirmed_missing} 张。最近确认：{report.ownership.confirmed_at} · 操作人ID {report.ownership.confirmed_by} · {report.ownership.note}</p>}
        {!report.ownership.storage_ready && <p className="text-amber-800">归属留痕表尚未安装，当前仅供核对；部署数据库迁移后可人工确认。</p>}
        <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setTab("assets")}>核对候选券资产</Button>
          {options.data?.can_manage && report.ownership.can_confirm && report.ownership.status !== "confirmed" && <Button disabled={busy || reportQuery.isFetching || Boolean(reportQuery.error)} onClick={() => { const o = report.ownership!; setConfirmationTarget({ id: selectedId, fingerprint: o.fingerprint, version: o.version, count: o.candidate_assets }); setConfirmationNote(""); setConfirmationOpen(true); }}>人工确认本档归属</Button>}</div>
      </CardContent></Card>}
      {report.member_source && <div className="rounded-md border p-4 text-sm"><p>当前会员画像：{report.member_source.source}；匹配 {report.member_source.matched} 人，待核查 {report.member_source.unresolved} 人。</p>
        {report.member_source.reason && <p className="text-amber-800">{report.member_source.reason}</p>}
        <p className="mt-1 text-muted-foreground">{report.member_source.history_basis} “档期内注册”不代表首购或活动带来的新客。</p></div>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
        ["领券人数", "issued_members"], ["核销人数", "used_members"], ["净连带销售", "net_linked_sales"], ["净券金额", "net_coupon_amount"],
      ].map(([label, key]) => <Card key={key}><CardHeader className="pb-2"><CardTitle className="text-sm font-normal">{label}</CardTitle></CardHeader><CardContent className="text-2xl font-semibold tabular-nums">{fmt(report.summary[key])}</CardContent></Card>)}</div>
      {hasQuality && <div role="status" className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">存在待核对的关联或非标准操作，报告不能直接当作最终结算结果。请查看“口径与质量”。</div>}
      <Tabs value={tab} onValueChange={setTab}><TabsList className="h-auto flex-wrap">
        <TabsTrigger value="coupons">券种汇总</TabsTrigger><TabsTrigger value="lift">销售增长试算</TabsTrigger><TabsTrigger value="levels">会员分层</TabsTrigger><TabsTrigger value="members">会员明细</TabsTrigger>
        <TabsTrigger value="tickets">关联小票/代付线索</TabsTrigger><TabsTrigger value="brands">连带品牌</TabsTrigger><TabsTrigger value="rules">ERP规则</TabsTrigger><TabsTrigger value="quality">口径与质量</TabsTrigger>
        <TabsTrigger value="assets">券资产归属</TabsTrigger><TabsTrigger value="flows">券流水</TabsTrigger><TabsTrigger value="post-returns">活动后退货</TabsTrigger>
      </TabsList>
      <TabsContent value="coupons"><DataTable rows={report.coupons} columns={couponColumns} /></TabsContent>
      <TabsContent value="lift"><SalesLiftPanel lift={report.sales_lift} /></TabsContent>
      <TabsContent value="levels"><DataTable rows={report.member_levels} columns={levelColumns} /></TabsContent>
      <TabsContent value="members" className="space-y-3"><Input aria-label="搜索持券会员号" placeholder="搜索持券会员号；点击会员号查看关联小票" value={memberFilter} onChange={e => setMemberFilter(e.target.value)} />
        <DataTable rows={members} columns={memberColumns} onMember={m => { setTicketMember(m); setTicketBill(""); setMismatchOnly(false); setTab("tickets"); }} /></TabsContent>
      <TabsContent value="tickets" className="space-y-3"><div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={mismatchOnly} onChange={e => setMismatchOnly(e.target.checked)} />只看会员不一致/未登记</label>
        {ticketMember && <Button variant="outline" size="sm" onClick={() => setTicketMember("")}>清除会员筛选：{ticketMember}</Button>}
        {ticketBill && <Button variant="outline" size="sm" onClick={() => setTicketBill("")}>清除小票筛选：{ticketBill}</Button>}</div>
        <p className="text-sm text-muted-foreground">会员不一致仅为核查线索，不等于违规。退货按原小票扣减销售，不要求同时有退券日志。</p>
        <DataTable rows={tickets} columns={ticketColumns} />
        {ticketBill && <><p className="text-sm">本票品牌/供应商销售分摊（不是券费用分摊）</p><DataTable rows={(report.brand_details || []).filter(r => r.billno === ticketBill)} columns={brandDetailColumns} /></>}</TabsContent>
      <TabsContent value="brands" className="space-y-4"><DataTable rows={report.brands} columns={brandColumns} />
        <p className="text-sm text-muted-foreground">以下追溯到小票、品牌和供应商；按整票连带销售分摊，不代表可收券商品或品牌承担费用。</p>
        <DataTable rows={report.brand_details || []} columns={brandDetailColumns} onBill={showBill} /></TabsContent>
      <TabsContent value="assets" className="space-y-3"><p className="text-sm text-muted-foreground">点击券资产序号查看本活动期后续流水。初始发券依据在本表；候选范围须先由业务核对，不能仅凭ERP编号确认。</p>
        <DataTable rows={report.assets || []} columns={assetColumns} onAsset={r => { setAssetFilter(`${r.coupon_type}:${r.asset_id}`); setTab("flows"); }} /></TabsContent>
      <TabsContent value="flows" className="space-y-3"><p className="text-sm text-muted-foreground">仅显示纳入本报告资产的活动期后续流水；O为核销、P为退券，U/V分别为核销/退券冲正。金额为绝对值，不能直接相加。点击小票序号追溯连带销售。</p>
        {assetFilter && <Button variant="outline" onClick={() => setAssetFilter("")}>清除券资产筛选：{assetFilter}</Button>}
        <DataTable rows={flows} columns={flowColumns} onBill={showBill} /></TabsContent>
      <TabsContent value="post-returns" className="space-y-3">{report.post_activity_returns ? <>
        <Card><CardContent className="space-y-2 p-5"><p>截至 {report.post_activity_returns.observed_through} · 活动后退货 {report.post_activity_returns.return_tickets} 张 · 退货销售收入 {money(report.post_activity_returns.return_sales)}</p>
          <p>活动期净连带销售加已观察退货后的参考值：{money(report.post_activity_returns.reference_net_sales)}</p>
          <p className="text-sm text-muted-foreground">{report.post_activity_returns.basis} {report.post_activity_returns.caveat}</p></CardContent></Card>
        <DataTable rows={report.post_activity_returns.details} columns={postReturnColumns} />
      </> : <p>尚未返回活动后退货观察数据。</p>}</TabsContent>
      <TabsContent value="rules" className="space-y-3"><div className="flex flex-wrap items-center gap-3"><p className="text-sm">快照：{rules?.fetched_at || "尚未读取"}</p>
        {options.data?.can_manage && <Button variant="outline" disabled={busy || !selected?.erp_activity_id} onClick={refreshRules}>从ODS读取规则快照</Button>}</div>
        <p className="text-sm text-muted-foreground">规则来自柜位库已校验的PAPI同步批次；此按钮不触发ERP同步。ODS采集时间：{rules?.source_synced_at || "未记录"}；批次：{rules?.ods_batch_id || "未读取"}</p>
        <p className="text-sm text-muted-foreground">已审核商品收券规则摘要；模式1=商品、2=组合。零收券金额及覆盖优先级待核实，不作逐笔违规判定。</p>
        <DataTable rows={rules?.rows || []} columns={ruleColumns} /></TabsContent>
      <TabsContent value="quality" className="space-y-4"><ul className="list-disc space-y-2 pl-5 text-sm">{report.definitions.map(d => <li key={d}>{d}</li>)}</ul>
        <DataTable rows={Object.entries(report.quality).map(([key, value]) => ({ label: qualityLabels[key] || key, count: value }))} columns={[["label", "核对项"], ["count", "数量"]]} />
        <p className="text-sm text-muted-foreground">生成时间 {report.generated_at}；金额来自当前同步数据，ERP规则是读取时点快照。</p></TabsContent>
      </Tabs>
    </>}
    <Dialog open={confirmationOpen} onOpenChange={setConfirmationOpen}><DialogContent><DialogHeader><DialogTitle>人工确认券资产归属</DialogTitle></DialogHeader>
      <p className="text-sm">将已预览的 {confirmationTarget?.count} 张候选券资产保存为新版本。请先核对券种、有效期及发券依据；ERP编号不是自动归属证据。数据或版本发生变化时将拒绝提交，需刷新重核。</p>
      <Label htmlFor="ownership-note">核对依据（至少5字）</Label><Input id="ownership-note" value={confirmationNote} maxLength={2000} onChange={e => setConfirmationNote(e.target.value)} placeholder="填写发券批次或业务核对依据" />
      <Button disabled={busy || confirmationNote.trim().length < 5 || reportQuery.isFetching || Boolean(reportQuery.error)} onClick={confirmOwnership}>{busy ? "保存中…" : "确认归属并留痕"}</Button>
    </DialogContent></Dialog>
    <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogContent className="max-w-xl"><DialogHeader><DialogTitle>{editingId ? "编辑活动说明及ERP关联" : "新建活动"}</DialogTitle></DialogHeader>
      <div className="grid gap-4"><p className="text-sm text-muted-foreground">保存后门店、档期和券种固定，避免后续退货归入下一档。相同门店/券种不能重复覆盖同一日期。</p>
        <div className="space-y-1"><Label htmlFor="campaign-name">活动名称</Label><Input id="campaign-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="如：中心七夕四券活动" /></div>
        <div className="space-y-1"><Label htmlFor="campaign-store">门店</Label><select disabled={Boolean(editingId)} id="campaign-store" className={`${selectClass} w-full`} value={form.store_code} onChange={e => setForm({ ...form, store_code: e.target.value })}>
          <option value="">请选择门店</option>{options.data?.stores.map(s => <option value={s.store_code} key={s.store_code}>{s.store_name}（{s.store_code}）</option>)}</select></div>
        <div className="grid grid-cols-2 gap-3">{(["start_date", "end_date"] as const).map((k, i) => <div key={k} className="space-y-1"><Label htmlFor={`campaign-${k}`}>{i ? "结束日期" : "开始日期"}</Label><Input disabled={Boolean(editingId)} id={`campaign-${k}`} type="date" value={form[k]} onInput={e => { const value = e.currentTarget.value; setForm(previous => ({ ...previous, [k]: value })); }} onChange={e => { const value = e.target.value; setForm(previous => ({ ...previous, [k]: value })); }} /></div>)}</div>
        <div className="grid grid-cols-2 gap-3"><div className="space-y-1"><Label htmlFor="campaign-types">券种（逗号分隔）</Label><Input disabled={Boolean(editingId)} id="campaign-types" value={form.coupon_types} onChange={e => setForm({ ...form, coupon_types: e.target.value })} /></div>
          <div className="space-y-1"><Label htmlFor="campaign-erp">ERP档期编码</Label><Input id="campaign-erp" value={form.erp_activity_id} onChange={e => setForm({ ...form, erp_activity_id: e.target.value })} placeholder="如：2205" /></div></div>
        <div className="space-y-1"><Label htmlFor="campaign-notes">活动说明</Label><Input id="campaign-notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></div>
        <Button disabled={busy || !form.name.trim() || !form.store_code || !form.start_date || !form.end_date} onClick={create}>{busy ? "保存中…" : editingId ? "保存说明及关联" : "确认建档"}</Button>
      </div>
    </DialogContent></Dialog>
  </div>;
}
