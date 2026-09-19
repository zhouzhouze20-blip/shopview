import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { isAdminUser } from "@/lib/module-permissions";
import { matchingTotals } from "@/lib/cosmetics-payment-matching";
import { Button } from "@/components/ui/button";
import { Command, CommandInput, CommandList, CommandItem, CommandEmpty } from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type Document = { source_key: string; version: string; number: string; date: string; amount: string; code?: string; remark?: string; group_names?: string; groups?: string[]; settlement_status?: string; document_type_name?: string; supplier_code?: string; supplier_name?: string };
type Match = { supplier_code?: string; number: string; invoice_amount: string; receipt_amount: string; difference: string; created_at?: string; invoices: Document[]; receipts: Document[] };
type Candidates = { group_options?: { code: string; name: string }[]; settlement_sync?: { source_at: string; stale: boolean }; invoices: Document[]; receipts: Document[]; groups: string[]; buyer_name: string; note: string };
const ROOT = "/api/cosmetics-payment-matching";
const money = (value: string) => Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 6 });
const control = "h-10 rounded-md border border-input bg-background px-3 text-sm w-full";
const initialMonth = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit" }).format(new Date());

function Documents({ rows, selected, onToggle, disabled, receipts = false }: {
  rows: Document[]; selected?: Record<string, Document>; onToggle?: (row: Document) => void; disabled?: boolean; receipts?: boolean;
}) {
  return <Table><TableHeader><TableRow>
    {onToggle && <TableHead className="w-12 whitespace-nowrap">选择</TableHead>}
    <TableHead>{receipts ? "验收/退厂单号" : "发票号码"}</TableHead><TableHead>日期</TableHead>
    {receipts && <><TableHead>柜组</TableHead><TableHead>结算状态</TableHead></>}<TableHead className="text-right">{receipts ? "含税金额（含负数）" : "价税合计"}</TableHead>
  </TableRow></TableHeader><TableBody>
    {rows.map(row => <TableRow key={row.source_key} data-state={selected?.[row.source_key] ? "selected" : undefined}>
      {onToggle && <TableCell><input type="checkbox" aria-label={`选择${row.number}`} checked={Boolean(selected?.[row.source_key])} disabled={disabled} onChange={() => onToggle(row)} className="h-4 w-4" /></TableCell>}
      <TableCell className="font-mono text-xs">{row.number}{receipts && <div className="font-sans text-muted-foreground">{row.document_type_name || "验收单"}</div>}{row.code && <div className="text-muted-foreground">代码 {row.code}</div>}{!receipts && row.remark && <div className="mt-1 max-w-sm whitespace-pre-wrap break-words font-sans text-muted-foreground">备注：{row.remark}</div>}</TableCell>
      <TableCell className="whitespace-nowrap">{row.date}</TableCell>
      {receipts && <><TableCell className="text-xs">{row.group_names}</TableCell><TableCell className="text-xs whitespace-nowrap">{row.settlement_status ?? "—"}</TableCell></>}
      <TableCell className="text-right whitespace-nowrap tabular-nums">{money(row.amount)}</TableCell>
    </TableRow>)}
    {rows.length === 0 && <TableRow><TableCell colSpan={receipts ? 6 : 4} className="py-10 text-center text-muted-foreground">没有符合条件的单据</TableCell></TableRow>}
  </TableBody></Table>;
}

export default function CosmeticsPaymentMatchingPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [store, setStore] = useState("601");
  const [month, setMonth] = useState(initialMonth);
  const [keyword, setKeyword] = useState("");
  const [supplierLabel, setSupplierLabel] = useState("");
  const [supplierOpen, setSupplierOpen] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  useEffect(() => { const timer = setTimeout(() => setSearchKeyword(keyword.trim()), 300); return () => clearTimeout(timer); }, [keyword]);
  const [supplier, setSupplier] = useState("");
  const [group, setGroup] = useState("");
  const [remarkKeyword, setRemarkKeyword] = useState("");
  useEffect(() => setRemarkKeyword(""), [store, supplier]);
  const [dates, setDates] = useState({ from: "", to: "" });
  const [appliedDates, setAppliedDates] = useState(dates);
  const [left, setLeft] = useState<Record<string, Document>>({});
  const [right, setRight] = useState<Record<string, Document>>({});
  const [detail, setDetail] = useState<Match | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [tab, setTab] = useState<"new" | "history">("new");
  const [message, setMessage] = useState("");
  const canCreate = isAdminUser(user) || user?.permission_codes?.includes("settlement.cosmetics_matching.create");
  const clearSelection = () => { setLeft({}); setRight({}); setMessage(""); };
  const suppliers = useQuery({ queryKey: [ROOT, "suppliers", store, searchKeyword], queryFn: () => apiGet<{items: {code: string; name: string}[]; has_more: boolean}>(`${ROOT}/suppliers?${new URLSearchParams({store, keyword: searchKeyword})}`) });
  const params = new URLSearchParams({ store, supplier });
  if (appliedDates.from) params.set("date_from", appliedDates.from);
  if (appliedDates.to) params.set("date_to", appliedDates.to);
  const candidates = useQuery({ queryKey: [ROOT, "candidates", store, supplier, appliedDates], enabled: Boolean(supplier), staleTime: 0,
    queryFn: () => apiGet<Candidates>(`${ROOT}/candidates?${params}`) });
  const history = useQuery({ queryKey: [ROOT, "history", store, supplier, month], enabled: Boolean(supplier) && tab === "history", staleTime: 0,
    queryFn: () => apiGet<{items: Match[]}>(`${ROOT}/history?${new URLSearchParams({store, supplier, payment_month: month})}`) });
  const save = useMutation({ mutationFn: () => apiPost<Match>(ROOT, { store, supplier, payment_month: month,
    invoices: Object.values(left).map(({source_key, version}) => ({source_key, version})),
    receipts: Object.values(right).map(({source_key, version}) => ({source_key, version})) }),
    onSuccess: result => { clearSelection(); setConfirm(false); setDetail(result); setMessage(`已生成配票单 ${result.number}`); void queryClient.invalidateQueries({queryKey: [ROOT]}); },
    onError: error => { setConfirm(false); setMessage(error.message); }
  });
  const toggle = (setter: typeof setLeft) => (row: Document) => setter(previous => { const next = {...previous}; if (next[row.source_key]) delete next[row.source_key]; else next[row.source_key] = row; return next; });
  const totals = matchingTotals(Object.values(left).map(r => r.amount), Object.values(right).map(r => r.amount));
  const invoiceRows = (candidates.data?.invoices ?? []).filter(row => !remarkKeyword.trim() || (row.remark ?? "").toLocaleLowerCase().includes(remarkKeyword.trim().toLocaleLowerCase()));
  const receiptRows = (candidates.data?.receipts ?? []).filter(row => !group || row.groups?.includes(group));
  const busy = save.isPending;
  const error = suppliers.error || candidates.error || (tab === "history" && history.error);
  return <div className="space-y-5 p-4 md:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-semibold">化妆品付款配票</h1><p className="mt-1 text-sm text-muted-foreground">跨月勾选发票与验收/退厂单，两侧含税金额差额不超过 1 元即可配票。</p></div>
      <Button variant="outline" disabled={busy || candidates.isFetching} onClick={() => { clearSelection(); void queryClient.invalidateQueries({queryKey: [ROOT]}); }}><RefreshCw className="mr-2 h-4 w-4" />刷新并清空勾选</Button></div>
    <Card><CardContent className="pt-5"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <label className="flex min-w-0 flex-col gap-2 text-sm"><span>门店</span><select aria-label="门店" className={control} disabled={busy} value={store} onChange={e => { setStore(e.target.value); setSupplier(""); setSupplierLabel(""); setKeyword(""); setSupplierOpen(false); setGroup(""); clearSelection(); }}><option value="601">常州购物中心</option><option value="602">常州百货大楼</option><option value="603">常州新世纪商城</option></select></label>
      <label className="flex min-w-0 flex-col gap-2 text-sm"><span>付款月份</span><Input aria-label="付款月份" type="month" value={month} disabled={busy} onChange={e => setMonth(e.target.value)} /></label>
      <div className="flex min-w-0 flex-col gap-2 text-sm sm:col-span-2 relative" onBlur={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setSupplierOpen(false); }}>
        <label htmlFor="matching-supplier">供应商</label>
        <Command shouldFilter={false} className="h-10 overflow-visible rounded-md border border-input [&_[cmdk-input-wrapper]]:h-full [&_[cmdk-input-wrapper]]:border-b-0" onKeyDown={e => { if(e.key === "Escape") setSupplierOpen(false); }}>
          <CommandInput className="h-full py-2" id="matching-supplier" aria-label="供应商" placeholder="输入供应商号或名称，模糊查询并选择" disabled={busy}
            value={supplier ? supplierLabel : keyword} onFocus={() => setSupplierOpen(true)}
            onValueChange={value => { setKeyword(value); setSupplier(""); setSupplierLabel(""); setGroup(""); clearSelection(); setSupplierOpen(true); }} />
          {supplierOpen && <CommandList className="absolute top-full left-0 right-0 z-40 mt-1 rounded-md border bg-white text-slate-900 shadow-lg" onMouseDown={e => e.preventDefault()}>
            {suppliers.isFetching || keyword.trim() !== searchKeyword ? <div className="p-3 text-muted-foreground">正在查询供应商…</div> : <>
              <CommandEmpty>{suppliers.isError ? "供应商查询失败，请重试" : "未找到匹配的供应商"}</CommandEmpty>
              {suppliers.data?.items.map(row => <CommandItem key={row.code} value={row.code} onSelect={() => {setSupplier(row.code);setSupplierLabel(`${row.code} · ${row.name}`);setGroup("");clearSelection();setSupplierOpen(false);}}>{row.code} · {row.name}</CommandItem>)}
            </>}
          </CommandList>}
        </Command>
      </div>
    </div>{suppliers.data?.has_more && <p className="mt-3 text-sm text-muted-foreground">仅列出前100家供应商，请输入名称或编码缩小范围。</p>}
    <p className="mt-3 text-sm text-muted-foreground">付款月份用于归档，不限制发票和验收/退厂单月份。购物中心与百货大楼共用购方抬头，发票跨店防重复。</p></CardContent></Card>
    <div className="flex gap-2"><Button variant={tab === "new" ? "default" : "outline"} onClick={() => setTab("new")}>新建配票单</Button><Button variant={tab === "history" ? "default" : "outline"} onClick={() => setTab("history")}>本付款月配票记录</Button></div>
    {error && <div role="alert" className="rounded-md border border-destructive p-3 text-sm text-destructive">{error.message}</div>}
    {message && <div role="status" className="rounded-md border p-3 text-sm">{message}</div>}
    {!supplier && <Card><CardContent className="py-12 text-center text-muted-foreground">选择供应商后，加载待配发票和验收/退厂单。</CardContent></Card>}
    {supplier && tab === "new" && <>
      <div className="flex flex-wrap items-end gap-3"><label className="text-sm">单据日期从<Input aria-label="单据日期从" type="date" value={dates.from} disabled={busy} onChange={e => setDates({...dates,from:e.target.value})} /></label><label className="text-sm">至<Input aria-label="单据日期至" type="date" value={dates.to} disabled={busy} onChange={e => setDates({...dates,to:e.target.value})} /></label><Button variant="outline" disabled={busy} onClick={() => {clearSelection();setAppliedDates({...dates});}}>筛选并清空勾选</Button><span className="text-xs text-muted-foreground">日期可留空，支持跨两个月、三个月选择。</span></div>
      {candidates.isFetching && <p role="status" className="text-sm">正在加载单据…</p>}
      {candidates.data && !candidates.isError && <>
        {candidates.data.settlement_sync && <p role="status" className={candidates.data.settlement_sync.stale ? "text-sm text-orange-700" : "text-xs text-muted-foreground"}>结算数据更新时间：{new Date(candidates.data.settlement_sync.source_at).toLocaleString("zh-CN", {timeZone: "Asia/Shanghai"})}（每15分钟同步）{candidates.data.settlement_sync.stale ? " · 已超过1小时未更新，可查看，暂不能生成配票单" : ""}</p>}
        <p className="text-xs text-muted-foreground">购方：{candidates.data.buyer_name}。{candidates.data.note}</p>
        <div className="grid items-start gap-4 xl:grid-cols-2">
          <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle className="text-lg">待配发票 <span className="text-sm font-normal text-muted-foreground">{invoiceRows.length} / {candidates.data.invoices.length} 张 · 已选 {Object.keys(left).length} 张</span></CardTitle><Input aria-label="搜索发票备注" placeholder="搜索发票备注，如：迪奥" value={remarkKeyword} onChange={e => setRemarkKeyword(e.target.value)} disabled={busy} className="h-10 w-full sm:w-64" /></div><p className="text-xs text-muted-foreground">按备注包含文字筛选；切换搜索保留已勾选发票，底部合计包含全部勾选，负数单据自动抵减。</p></CardHeader><CardContent className="max-h-[480px] overflow-auto px-2"><Documents rows={invoiceRows} selected={left} onToggle={toggle(setLeft)} disabled={busy || candidates.isFetching} /></CardContent></Card>
          <Card><CardHeader><CardTitle className="text-lg">待配验收/退厂单（未关联结算单） <span className="text-sm font-normal text-muted-foreground">已选 {Object.keys(right).length} 张</span></CardTitle><select aria-label="筛选柜组" className={control} value={group} disabled={busy} onChange={e => setGroup(e.target.value)}><option value="">全部柜组</option>{(candidates.data.group_options ?? candidates.data.groups.map(code => ({code, name: ""}))).map(({code, name}) => <option key={code} value={code}>{name ? `${code} · ${name}` : code}</option>)}</select><p className="text-xs text-muted-foreground">切换柜组保留已勾选单据，底部合计包含全部勾选，负数单据自动抵减。</p></CardHeader><CardContent className="max-h-[480px] overflow-auto px-2"><Documents receipts rows={receiptRows} selected={right} onToggle={toggle(setRight)} disabled={busy || candidates.isFetching} /></CardContent></Card>
        </div>
      </>}
      <Card className="sticky bottom-2 z-30 isolate shadow-lg" style={{ backgroundColor: "#ffffff", opacity: 1 }}><CardContent className="flex flex-wrap items-center justify-between gap-4 py-4"><div className="flex flex-wrap gap-6"><div className="text-sm">发票合计（{Object.keys(left).length}张）<div className="text-xl font-semibold tabular-nums">¥{money(totals.invoiceAmount)}</div></div><div className="text-sm">验收/退厂单合计（{Object.keys(right).length}张）<div className="text-xl font-semibold tabular-nums">¥{money(totals.receiptAmount)}</div></div><div className="text-sm">差额（发票－验收/退厂净额）<div className={`text-xl font-semibold tabular-nums ${totals.eligible ? "text-green-700" : "text-orange-700"}`}>¥{money(totals.difference)}</div></div></div><Button disabled={!canCreate || candidates.data?.settlement_sync?.stale || !totals.eligible || !/^\d{4}-(0[1-9]|1[0-2])$/.test(month) || busy || candidates.isFetching || candidates.isError} onClick={() => setConfirm(true)}><CheckCircle2 className="mr-2 h-4 w-4" />{busy ? "正在生成…" : "生成配票单"}</Button></CardContent></Card>
      {!canCreate && <p className="text-sm text-muted-foreground">当前账号仅有查看权限，生成配票单需要单独授权。</p>}
    </>}
    {supplier && tab === "history" && <Card><CardHeader><CardTitle className="text-lg">{month} 配票记录</CardTitle></CardHeader><CardContent>{history.isFetching ? <p>正在加载…</p> : <Table><TableHeader><TableRow><TableHead>配票单号</TableHead><TableHead>供应商</TableHead><TableHead>柜组</TableHead><TableHead>发票金额</TableHead><TableHead>验收金额</TableHead><TableHead>差额</TableHead><TableHead>明细</TableHead></TableRow></TableHeader><TableBody>{history.data?.items.map(row => <TableRow key={row.number}><TableCell>{row.number}</TableCell><TableCell className="min-w-[180px]">{[row.supplier_code || row.receipts[0]?.supplier_code, row.receipts.find(receipt => receipt.supplier_name)?.supplier_name].filter(Boolean).join(" · ") || "—"}</TableCell><TableCell className="min-w-[180px]">{Array.from(new Set(row.receipts.flatMap(receipt => receipt.group_names ? receipt.group_names.split("、") : receipt.groups ?? []))).join("、") || "—"}</TableCell><TableCell>{money(row.invoice_amount)}</TableCell><TableCell>{money(row.receipt_amount)}</TableCell><TableCell>{money(row.difference)}</TableCell><TableCell><Button variant="outline" size="sm" onClick={() => setDetail(row)}>查看绑定明细</Button></TableCell></TableRow>)}{!history.data?.items.length && <TableRow><TableCell colSpan={7} className="py-8 text-center">本付款月没有可查看的配票单</TableCell></TableRow>}</TableBody></Table>}</CardContent></Card>}
    <Dialog open={confirm} onOpenChange={value => {if (!busy) setConfirm(value);}}><DialogContent><DialogHeader><DialogTitle>确认生成配票单</DialogTitle><DialogDescription>付款月份 {month}，发票 {Object.keys(left).length} 张、验收/退厂单 {Object.keys(right).length} 张。保存后这些单据将被占用，不能重复配票。</DialogDescription></DialogHeader><div className="text-sm">发票 ¥{money(totals.invoiceAmount)} · 验收 ¥{money(totals.receiptAmount)} · 差额 ¥{money(totals.difference)}</div><Button disabled={busy} onClick={() => save.mutate()}>{busy ? "正在生成…" : "确认生成"}</Button></DialogContent></Dialog>
    <Dialog open={Boolean(detail)} onOpenChange={open => {if (!open) setDetail(null);}}><DialogContent className="max-h-[85vh] max-w-5xl overflow-auto"><DialogHeader><DialogTitle>配票单 {detail?.number}</DialogTitle><DialogDescription>已完成单据绑定；此记录不代表实际付款。差额 ¥{money(detail?.difference ?? "0")}</DialogDescription></DialogHeader><h3 className="font-medium">绑定发票（{detail?.invoices.length}张）</h3><Documents rows={detail?.invoices ?? []} /><h3 className="font-medium">绑定验收/退厂单（{detail?.receipts.length}张）</h3><Documents receipts rows={detail?.receipts ?? []} /></DialogContent></Dialog>
  </div>;
}
