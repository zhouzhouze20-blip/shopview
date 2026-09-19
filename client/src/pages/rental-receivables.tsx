import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, Building2, CircleDollarSign, Clock3, Download, FileWarning, Loader2, Search, WalletCards } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { downloadRentalReceivableExpenseDetails, useRentalReceivableDetail, useRentalReceivableOptions, useRentalReceivables, type RentalReceivableParams } from "@/hooks/useRentalReceivables";
import { useToast } from "@/hooks/use-toast";
import { supplierActualReceivableAmount } from "@/lib/rental-receivable-amounts";

const PAGE_SIZE = 50;

function isoDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function initialDateRange() {
  const now = new Date();
  return {
    from: `${now.getFullYear()}-01-01`,
    to: isoDate(now),
  };
}

function money(value: number) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(value) ? value : 0);
}

function dateText(value: string | null) {
  return value ? value.slice(0, 10) : "—";
}

function agingLabel(days: number) {
  if (days < 0) return "未到期";
  if (days <= 30) return "0–30 天";
  if (days <= 60) return "31–60 天";
  if (days <= 90) return "61–90 天";
  return "90 天以上";
}

function agingTone(days: number) {
  if (days > 90) return "border-red-200 bg-red-50 text-red-700";
  if (days > 60) return "border-orange-200 bg-orange-50 text-orange-700";
  if (days > 30) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function MetricCard({ title, value, note, icon }: { title: string; value: string; note: string; icon: ReactNode }) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-1 text-xl font-semibold tracking-tight text-slate-950">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{note}</p>
        </div>
        <div className="rounded-lg bg-slate-100 p-2 text-slate-600">{icon}</div>
      </CardContent>
    </Card>
  );
}

export default function RentalReceivablesPage() {
  const { toast } = useToast();
  const range = useMemo(initialDateRange, []);
  const [settleFrom, setSettleFrom] = useState(range.from);
  const [settleTo, setSettleTo] = useState(range.to);
  const [mkt, setMkt] = useState("");
  const [departmentCode, setDepartmentCode] = useState("");
  const [groupPrefix, setGroupPrefix] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedBillNo, setSelectedBillNo] = useState<string | null>(null);
  const [showAllDetailLines, setShowAllDetailLines] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [submitted, setSubmitted] = useState<RentalReceivableParams>({
    settle_from: range.from,
    settle_to: range.to,
    page: 1,
    page_size: PAGE_SIZE,
  });

  const optionsQuery = useRentalReceivableOptions();
  const query = useRentalReceivables(submitted);
  const detailQuery = useRentalReceivableDetail(selectedBillNo);
  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / PAGE_SIZE));
  const departmentOptions = useMemo(
    () => (optionsQuery.data?.departments ?? []).filter((item) => !mkt || item.store_code === mkt),
    [mkt, optionsQuery.data?.departments],
  );

  const search = () => {
    setSubmitted({
      settle_from: settleFrom,
      settle_to: settleTo,
      mkt,
      department_code: departmentCode,
      group_prefix: groupPrefix,
      keyword,
      page: 1,
      page_size: PAGE_SIZE,
    });
  };

  const changePage = (page: number) => setSubmitted((current) => ({ ...current, page }));
  const exportExpenseDetails = async () => {
    setIsExporting(true);
    try {
      const filename = await downloadRentalReceivableExpenseDetails(submitted);
      toast({ title: "费用明细已导出", description: filename });
    } catch (error) {
      toast({
        title: "费用明细导出失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };
  const summary = query.data?.summary;
  const visibleDetailLines = useMemo(
    () => showAllDetailLines
      ? (detailQuery.data?.items ?? [])
      : (detailQuery.data?.items ?? []).filter((item) => Math.abs(item.balance_amount) >= 0.005),
    [detailQuery.data?.items, showAllDetailLines],
  );

  const openDetail = (billNo: string) => {
    setShowAllDetailLines(false);
    setSelectedBillNo(billNo);
  };

  return (
    <div className="container mx-auto space-y-5 p-4" data-testid="rental-receivables-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">租赁应收未收</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          总部库租赁结算单非零未收余额，包含正、负余额；数据由 PAPI 定时同步，并按当前账号的门店、部门等业务权限过滤。
        </p>
      </div>

      <Alert className="border-sky-200 bg-sky-50/70 text-sky-950">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>口径说明</AlertTitle>
        <AlertDescription>
          应收未收以结算明细余额为准，是否生成收款单不作为整张结算单的剔除依据。
          原结算金额保留源值符号；应收未收汇总全部非 <code>00-*</code> 项目，并保留正负号。销售返款明细继续展示，但不计入应收未收。
          供应商实际应收金额按“应收未收 − 销售返款”计算展示。
          本页按富基“应收应付单据明细查询”的未收口径保留正、负非零余额；仅统计已有租赁结算单，不含空账单号明细。
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">查询条件</CardTitle>
          <CardDescription>默认查询本年结算截止日范围；页面查询本地 ODS，最多每页 {PAGE_SIZE} 条。</CardDescription>
        </CardHeader>
        <CardContent className="grid items-end gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-[repeat(6,minmax(0,1fr))_auto]">
          <div className="space-y-2">
            <Label htmlFor="rr-from">结算截止日起</Label>
            <Input id="rr-from" type="date" value={settleFrom} onChange={(event) => setSettleFrom(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rr-to">结算截止日止</Label>
            <Input id="rr-to" type="date" value={settleTo} onChange={(event) => setSettleTo(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rr-mkt">门店</Label>
            <Select value={mkt || "__all__"} onValueChange={(value) => { setMkt(value === "__all__" ? "" : value); setDepartmentCode(""); }}>
              <SelectTrigger id="rr-mkt"><SelectValue placeholder={optionsQuery.isLoading ? "加载中…" : "全部门店"} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部门店</SelectItem>
                {(optionsQuery.data?.stores ?? []).map((store) => (
                  <SelectItem key={store.store_code} value={store.store_code}>{store.store_name}（{store.store_code}）</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="rr-department">部门</Label>
            <Select value={departmentCode || "__all__"} onValueChange={(value) => setDepartmentCode(value === "__all__" ? "" : value)}>
              <SelectTrigger id="rr-department"><SelectValue placeholder={optionsQuery.isLoading ? "加载中…" : "全部部门"} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部部门</SelectItem>
                {departmentOptions.map((department) => (
                  <SelectItem key={`${department.store_code}-${department.department_code}`} value={department.department_code}>
                    {department.department_name}（{department.department_code}）
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="rr-group">柜组编码开头</Label>
            <Input id="rr-group" placeholder="如 60201" value={groupPrefix} onChange={(event) => setGroupPrefix(event.target.value)} />
          </div>
          <div className="space-y-2 lg:col-span-1">
            <Label htmlFor="rr-keyword">关键词</Label>
            <Input id="rr-keyword" placeholder="单号/供应商/合同" value={keyword} onChange={(event) => setKeyword(event.target.value)} onKeyDown={(event) => event.key === "Enter" && search()} />
          </div>
          <div className="flex gap-2 sm:col-span-2 lg:col-span-2 xl:col-span-1">
            <Button className="min-w-[88px]" onClick={search} disabled={query.isFetching || !settleFrom || !settleTo}>
              {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
              查询
            </Button>
            <Button
              variant="outline"
              className="whitespace-nowrap"
              onClick={exportExpenseDetails}
              disabled={isExporting || query.isFetching || !query.data?.total}
            >
              {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              {isExporting ? "导出中…" : "导出费用明细"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {query.isError ? (
        <Alert variant="destructive">
          <FileWarning className="h-4 w-4" />
          <AlertTitle>查询失败</AlertTitle>
          <AlertDescription className="break-all">
            {query.error instanceof Error ? query.error.message : "本地 ODS 查询暂不可用"}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="应收未收" value={money(summary?.receivable_amount ?? 0)} note={`${summary?.bill_count ?? 0} 张结算单`} icon={<CircleDollarSign className="h-5 w-5" />} />
        <MetricCard title="销售返款（不计应收）" value={money(summary?.sales_refund_amount ?? 0)} note="00-* 项目仅供核对" icon={<Building2 className="h-5 w-5" />} />
        <MetricCard title="供应商实际应收金额" value={money(supplierActualReceivableAmount(summary?.receivable_amount, summary?.sales_refund_amount))} note="应收未收 − 销售返款" icon={<WalletCards className="h-5 w-5" />} />
        <MetricCard title="部分 / 异常未收" value={`${(summary?.partial_count ?? 0) + (summary?.anomaly_count ?? 0)} 张`} note={`${summary?.partial_count ?? 0} 部分 · ${summary?.anomaly_count ?? 0} 余额超原额`} icon={<Clock3 className="h-5 w-5" />} />
        <MetricCard title="90 天以上未收" value={money(summary?.over_90_amount ?? 0)} note="按结算截止日计算账龄" icon={<AlertTriangle className="h-5 w-5" />} />
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 pb-3">
          <div>
            <CardTitle className="text-base">应收未收明细</CardTitle>
            <CardDescription>
              共 {query.data?.total ?? 0} 条 · 第 {submitted.page} / {totalPages} 页
              {query.data?.source?.name ? ` · ${query.data.source.name}` : ""}
              {query.data?.source_loaded_at ? ` · 数据截至 ${query.data.source_loaded_at.replace("T", " ")}` : ""}
              {query.data?.queried_at ? ` · 查询于 ${query.data.queried_at.replace("T", " ")}` : ""}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={submitted.page <= 1 || query.isFetching} onClick={() => changePage(Math.max(1, submitted.page - 1))}>上一页</Button>
            <Button variant="outline" size="sm" disabled={submitted.page >= totalPages || query.isFetching} onClick={() => changePage(submitted.page + 1)}>下一页</Button>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <Table className="min-w-[1540px] table-fixed text-[13px]">
            <TableHeader>
              <TableRow>
                <TableHead className="h-10 w-[125px] whitespace-nowrap px-3">门店</TableHead>
                <TableHead className="h-10 w-[165px] px-3">部门</TableHead>
                <TableHead className="h-10 w-[175px] px-3">柜组</TableHead>
                <TableHead className="h-10 w-[210px] px-3">供应商</TableHead>
                <TableHead className="h-10 w-[180px] whitespace-nowrap px-3">结算期间</TableHead>
                <TableHead className="h-10 w-[145px] whitespace-nowrap px-3 text-right">应收未收</TableHead>
                <TableHead className="h-10 w-[135px] whitespace-nowrap px-3 text-right">原结算额</TableHead>
                <TableHead className="h-10 w-[105px] whitespace-nowrap px-3">未收状态</TableHead>
                <TableHead className="h-10 w-[105px] whitespace-nowrap px-3">账龄</TableHead>
                <TableHead className="h-10 w-[105px] whitespace-nowrap px-3">合同号</TableHead>
                <TableHead className="h-10 w-[190px] whitespace-nowrap px-3">结算单号</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {query.isLoading || query.isFetching ? (
                <TableRow><TableCell colSpan={11} className="py-12 text-center text-muted-foreground"><Loader2 className="mr-2 inline h-5 w-5 animate-spin" />正在查询本地 ODS…</TableCell></TableRow>
              ) : (query.data?.items ?? []).length === 0 ? (
                <TableRow><TableCell colSpan={11} className="py-12 text-center text-muted-foreground">当前条件下暂无应收未收记录</TableCell></TableRow>
              ) : (
                query.data?.items.map((row) => (
                  <TableRow key={row.bill_no}>
                    <TableCell className="px-3 py-2.5">
                      <div className="truncate font-medium" title={row.store_name || row.store_code || "—"}>{row.store_name || row.store_code || "—"}</div>
                      <div className="truncate text-xs text-muted-foreground">{row.store_code || "—"}</div>
                    </TableCell>
                    <TableCell className="px-3 py-2.5">
                      <div className="truncate font-medium" title={row.department_name || "—"}>{row.department_name || "—"}</div>
                      <div className="truncate text-xs text-muted-foreground">{row.department_code || "—"}</div>
                    </TableCell>
                    <TableCell className="px-3 py-2.5">
                      <div className="truncate font-medium" title={row.group_name || "—"}>{row.group_name || "—"}</div>
                      <div className="truncate text-xs text-muted-foreground">{row.group_code || "—"}</div>
                    </TableCell>
                    <TableCell className="px-3 py-2.5">
                      <div className="truncate font-medium" title={row.supplier_name || "—"}>{row.supplier_name || "—"}</div>
                      <div className="truncate text-xs text-muted-foreground">{row.supplier_id || "—"}</div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-3 py-2.5 text-xs">{dateText(row.settle_from)} 至 {dateText(row.settle_to)}</TableCell>
                    <TableCell className="whitespace-nowrap px-3 py-2.5 text-right">
                      <Button
                        variant="link"
                        className="h-auto p-0 font-mono font-semibold text-red-600 underline-offset-4 hover:text-red-700 hover:underline"
                        onClick={() => openDetail(row.bill_no)}
                        aria-label={`查看结算单 ${row.bill_no} 的金额组成明细`}
                      >
                        {money(row.receivable_amount)}
                      </Button>
                    </TableCell>
                    <TableCell className="whitespace-nowrap px-3 py-2.5 text-right font-mono text-xs text-slate-600">{money(row.original_amount)}</TableCell>
                    <TableCell className="px-3 py-2.5">
                      <Badge
                        variant="outline"
                        className={`whitespace-nowrap ${row.outstanding_status === "EXCEEDS_ORIGINAL"
                          ? "border-violet-200 bg-violet-50 text-violet-700"
                          : row.outstanding_status === "PARTIAL"
                            ? "border-amber-200 bg-amber-50 text-amber-700"
                            : "border-red-200 bg-red-50 text-red-700"}`}
                      >
                        {row.outstanding_status === "EXCEEDS_ORIGINAL"
                          ? "余额超原额"
                          : row.outstanding_status === "PARTIAL" ? "部分未收" : "全额未收"}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-3 py-2.5"><Badge variant="outline" className={`whitespace-nowrap ${agingTone(row.aging_days)}`}>{agingLabel(row.aging_days)}{row.aging_days >= 0 ? ` · ${row.aging_days}天` : ""}</Badge></TableCell>
                    <TableCell className="truncate whitespace-nowrap px-3 py-2.5" title={row.contract_no || "—"}>{row.contract_no || "—"}</TableCell>
                    <TableCell className="whitespace-nowrap px-3 py-2.5 font-mono text-xs">{row.bill_no}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={Boolean(selectedBillNo)} onOpenChange={(open) => !open && setSelectedBillNo(null)}>
        <DialogContent className="max-h-[92vh] w-[96vw] max-w-[1500px] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>应收未收金额组成</DialogTitle>
            <DialogDescription>
              {detailQuery.data
                ? `${detailQuery.data.bill.bill_no} · ${detailQuery.data.bill.store_name || detailQuery.data.bill.store_code || "—"} · ${detailQuery.data.bill.department_name || "—"} · ${detailQuery.data.bill.group_name || detailQuery.data.bill.group_code || "—"}`
                : selectedBillNo || "正在加载结算单"}
            </DialogDescription>
          </DialogHeader>

          {detailQuery.isLoading ? (
            <div className="py-16 text-center text-muted-foreground"><Loader2 className="mr-2 inline h-5 w-5 animate-spin" />正在读取结算组成明细…</div>
          ) : detailQuery.isError ? (
            <Alert variant="destructive">
              <FileWarning className="h-4 w-4" />
              <AlertTitle>明细读取失败</AlertTitle>
              <AlertDescription>{detailQuery.error instanceof Error ? detailQuery.error.message : "无法读取结算明细"}</AlertDescription>
            </Alert>
          ) : detailQuery.data ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs text-muted-foreground">原结算额合计</p><p className="mt-1 font-mono text-lg font-semibold">{money(detailQuery.data.totals.original_amount)}</p></div>
                <div className="rounded-lg border border-sky-200 bg-sky-50 p-3"><p className="text-xs text-sky-700">销售返款（不计应收）</p><p className="mt-1 font-mono text-lg font-semibold text-sky-800">{money(detailQuery.data.totals.sales_refund_amount)}</p></div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-3"><p className="text-xs text-red-700">应收未收合计</p><p className="mt-1 font-mono text-lg font-semibold text-red-700">{money(detailQuery.data.totals.receivable_amount)}</p></div>
                <div className="rounded-lg border border-violet-200 bg-violet-50 p-3"><p className="text-xs text-violet-700">供应商实际应收金额</p><p className="mt-1 font-mono text-lg font-semibold text-violet-800">{money(supplierActualReceivableAmount(detailQuery.data.totals.receivable_amount, detailQuery.data.totals.sales_refund_amount))}</p></div>
                <div className="rounded-lg border bg-slate-50 p-3"><p className="text-xs text-muted-foreground">组成行数</p><p className="mt-1 text-lg font-semibold">{detailQuery.data.nonzero_count} 条非零 · 共 {detailQuery.data.detail_count} 条</p></div>
              </div>

              <Alert className="border-sky-200 bg-sky-50/70 text-sky-950">
                <CircleDollarSign className="h-4 w-4" />
                <AlertTitle>金额关系</AlertTitle>
                <AlertDescription>应收影响汇总全部非 <code>00-*</code> 项目，并保留明细余额的正负号；只有 <code>00-*</code> 销售返款不计入。应收影响合计应与列表中的应收未收金额一致。</AlertDescription>
              </Alert>

              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm text-muted-foreground">
                  供应商：{detailQuery.data.bill.supplier_name || detailQuery.data.bill.supplier_id || "—"} · 合同：{detailQuery.data.bill.contract_no || "—"} · 结算期间：{dateText(detailQuery.data.bill.settle_from)} 至 {dateText(detailQuery.data.bill.settle_to)}
                </div>
                {detailQuery.data.detail_count > detailQuery.data.nonzero_count ? (
                  <Button variant="outline" size="sm" onClick={() => setShowAllDetailLines((value) => !value)}>
                    {showAllDetailLines ? "仅看非零余额" : `显示全部 ${detailQuery.data.detail_count} 条`}
                  </Button>
                ) : null}
              </div>

              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">行号</TableHead>
                      <TableHead className="min-w-[180px]">结算项目</TableHead>
                      <TableHead className="whitespace-nowrap">项目期间</TableHead>
                      <TableHead className="whitespace-nowrap text-right">项目金额</TableHead>
                      <TableHead className="whitespace-nowrap text-right">已收款</TableHead>
                      <TableHead className="whitespace-nowrap text-right">抵扣</TableHead>
                      <TableHead className="whitespace-nowrap text-right">明细余额</TableHead>
                      <TableHead className="whitespace-nowrap text-right">应收影响</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleDetailLines.map((item) => (
                      <TableRow key={item.row_no}>
                        <TableCell className="font-mono text-xs">{item.row_no}</TableCell>
                        <TableCell>
                          <div className="font-medium">{item.item_name}</div>
                          <div className="text-xs text-muted-foreground">{item.item_code || "—"}{item.finance_month ? ` · ${item.finance_month}` : ""}</div>
                          {item.is_sales_refund ? <Badge variant="outline" className="mt-1 border-sky-200 bg-sky-50 text-sky-700">销售返款 · 不计应收</Badge> : null}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-xs">{dateText(item.period_from)} 至 {dateText(item.period_to)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right font-mono text-xs">{money(item.amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right font-mono text-xs">{money(item.paid_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right font-mono text-xs">{money(item.deducted_amount)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right font-mono text-xs">{money(item.balance_amount)}</TableCell>
                        <TableCell className={`whitespace-nowrap text-right font-mono font-semibold ${item.receivable_component > 0.005 ? "text-red-600" : item.receivable_component < -0.005 ? "text-emerald-700" : "text-slate-500"}`}>
                          {item.is_receivable_line ? money(item.receivable_component) : "不计入"}
                        </TableCell>
                      </TableRow>
                    ))}
                    <TableRow className="bg-slate-50 font-semibold">
                      <TableCell colSpan={3}>合计</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{money(detailQuery.data.totals.original_amount)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{money(detailQuery.data.totals.paid_amount)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{money(detailQuery.data.totals.deducted_amount)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono">{money(detailQuery.data.totals.balance_amount)}</TableCell>
                      <TableCell className="whitespace-nowrap text-right font-mono text-red-600">{money(detailQuery.data.totals.receivable_amount)}</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
