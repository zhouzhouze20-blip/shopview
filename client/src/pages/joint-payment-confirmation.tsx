import { useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Clock3, FileSearch, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  useJointPaymentConfirmation,
  useJointPaymentConfirmationDetail,
  useJointPaymentDepartmentOptions,
  type JointPaymentItem,
  type JointPaymentParams,
} from "@/hooks/useJointPaymentConfirmation";

const PAGE_SIZE = 20;

const money = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

const integer = (value: unknown) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(Number(value || 0));

const date = (value: unknown) => {
  if (value == null || value === "") return "—";
  return String(value).slice(0, 10);
};

const textValue = (value: unknown) => (value == null || value === "" ? "—" : String(value));

type FilterDraft = {
  status: string;
  dateFrom: string;
  dateTo: string;
  market: string;
  departmentCode: string;
  groupPrefix: string;
  keyword: string;
};

const initialFilters: FilterDraft = {
  status: "M",
  dateFrom: "",
  dateTo: "",
  market: "",
  departmentCode: "ALL",
  groupPrefix: "",
  keyword: "",
};

function toParams(filters: FilterDraft, page: number): JointPaymentParams {
  return {
    page,
    page_size: PAGE_SIZE,
    payment_status: filters.status === "ALL" ? "" : filters.status,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    market: filters.market,
    department_code: filters.departmentCode === "ALL" ? "" : filters.departmentCode,
    group_prefix: filters.groupPrefix,
    keyword: filters.keyword,
  };
}

export default function JointPaymentConfirmationPage() {
  const [draft, setDraft] = useState<FilterDraft>(initialFilters);
  const [applied, setApplied] = useState<FilterDraft>(initialFilters);
  const [page, setPage] = useState(1);
  const [selectedBill, setSelectedBill] = useState<string | null>(null);

  const query = useJointPaymentConfirmation(toParams(applied, page));
  const detailQuery = useJointPaymentConfirmationDetail(selectedBill);
  const departmentOptionsQuery = useJointPaymentDepartmentOptions();
  const summary = query.data?.summary;
  const rows = useMemo(() => query.data?.items ?? [], [query.data]);
  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const applyFilters = () => {
    setPage(1);
    setApplied({ ...draft });
  };
  const resetFilters = () => {
    setDraft(initialFilters);
    setApplied(initialFilters);
    setPage(1);
  };

  return (
    <div className="space-y-5 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">联营付款单确认</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            查看联营付款单的生成待确认与已审核状态，并追溯构成付款单的结算批次明细。
          </p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          联营按 paybatch 经营方式 4 识别；生成=M，已审核=Y
          <div className="mt-1">最新状态业务日期：{date(summary?.latest_status_date)}</div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="生成待确认"
          value={`${integer(summary?.generated_count)} 单`}
          description={money(summary?.generated_amount)}
          icon={<Clock3 className="h-5 w-5 text-amber-600" />}
          tone="amber"
        />
        <SummaryCard
          title="已审核"
          value={`${integer(summary?.audited_count)} 单`}
          description="财务收入已确认"
          icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          tone="emerald"
        />
        <SummaryCard
          title="本财务月审核金额"
          value={money(summary?.current_financial_month_audited_amount)}
          description={`${date(summary?.current_financial_month_start)}—${date(summary?.current_financial_month_end)} · 按审核日期`}
          icon={<CheckCircle2 className="h-5 w-5 text-blue-600" />}
        />
        <SummaryCard
          title="当前列表"
          value={`${integer(total)} 单`}
          description={applied.status === "M" ? "生成待确认明细" : applied.status === "Y" ? "已审核明细" : "全部状态明细"}
          icon={<FileSearch className="h-5 w-5 text-slate-600" />}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">查询条件</CardTitle>
          <CardDescription>状态日期：生成单取录入日期，已审核单取审核日期；日期留空表示查询全部历史。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 xl:items-end">
          <div>
            <Label>状态</Label>
            <Select value={draft.status} onValueChange={(value) => setDraft((prev) => ({ ...prev, status: value }))}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="M">生成待确认</SelectItem>
                <SelectItem value="Y">已审核</SelectItem>
                <SelectItem value="ALL">全部状态</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="joint-payment-date-from">状态日期起</Label>
            <Input id="joint-payment-date-from" className="mt-1" type="date" value={draft.dateFrom} onChange={(event) => setDraft((prev) => ({ ...prev, dateFrom: event.target.value }))} />
          </div>
          <div>
            <Label htmlFor="joint-payment-date-to">状态日期止</Label>
            <Input id="joint-payment-date-to" className="mt-1" type="date" value={draft.dateTo} onChange={(event) => setDraft((prev) => ({ ...prev, dateTo: event.target.value }))} />
          </div>
          <div>
            <Label htmlFor="joint-payment-market">门店</Label>
            <Input id="joint-payment-market" className="mt-1" placeholder="如 602" value={draft.market} onChange={(event) => setDraft((prev) => ({ ...prev, market: event.target.value }))} />
          </div>
          <div>
            <Label>部门</Label>
            <Select value={draft.departmentCode} onValueChange={(value) => setDraft((prev) => ({ ...prev, departmentCode: value }))}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">全部有权部门</SelectItem>
                {(departmentOptionsQuery.data?.departments ?? []).map((department) => (
                  <SelectItem key={department.department_code} value={department.department_code}>
                    {department.department_code} {department.department_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="joint-payment-group">柜组前缀</Label>
            <Input id="joint-payment-group" className="mt-1" placeholder="如 6020101" value={draft.groupPrefix} onChange={(event) => setDraft((prev) => ({ ...prev, groupPrefix: event.target.value }))} />
          </div>
          <div className="sm:col-span-2 lg:col-span-3 xl:col-span-1">
            <Label htmlFor="joint-payment-keyword">关键词</Label>
            <Input id="joint-payment-keyword" className="mt-1" placeholder="付款单/结算单/供应商" value={draft.keyword} onChange={(event) => setDraft((prev) => ({ ...prev, keyword: event.target.value }))} onKeyDown={(event) => event.key === "Enter" && applyFilters()} />
          </div>
          <div className="flex gap-2 sm:col-span-2 lg:col-span-1 xl:col-span-1">
            <Button className="flex-1" onClick={applyFilters}>查询</Button>
            <Button variant="outline" onClick={resetFilters}>重置</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
          <div>
            <CardTitle className="text-base">付款单明细</CardTitle>
            <CardDescription>金额按当前用户可见柜组的 paybatch 实付金额汇总。</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            刷新
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {query.isError ? (
            <div className="p-6 text-sm text-rose-600">{query.error instanceof Error ? query.error.message : "查询失败"}</div>
          ) : query.isLoading ? (
            <div className="flex items-center justify-center gap-2 p-10 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />正在查询付款单…</div>
          ) : rows.length === 0 ? (
            <div className="p-10 text-center text-sm text-muted-foreground">当前条件下没有联营付款单。</div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>付款单号</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>供应商</TableHead>
                    <TableHead>门店/部门</TableHead>
                    <TableHead className="text-right">付款金额</TableHead>
                    <TableHead className="text-right">结算单</TableHead>
                    <TableHead>状态日期</TableHead>
                    <TableHead>审核人</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.payment_bill_no}>
                      <TableCell className="font-mono text-xs">{row.payment_bill_no}</TableCell>
                      <TableCell><StatusBadge row={row} /></TableCell>
                      <TableCell>
                        <div className="max-w-[240px] truncate font-medium" title={row.supplier_name || ""}>{row.supplier_name || row.supplier_code || "—"}</div>
                        {row.supplier_name && row.supplier_code ? <div className="text-xs text-muted-foreground">{row.supplier_code}</div> : null}
                      </TableCell>
                      <TableCell>
                        <div>{row.market_code || "—"}</div>
                        <div className="max-w-[240px] truncate text-xs text-muted-foreground" title={`${row.department_codes || ""} ${row.department_names || ""}`}>
                          {row.department_names || row.department_codes || "—"}
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">{money(row.payment_amount)}</TableCell>
                      <TableCell className="text-right tabular-nums">{integer(row.settlement_count)}</TableCell>
                      <TableCell>{date(row.status_date)}</TableCell>
                      <TableCell>{row.status === "Y" ? row.auditor || "—" : "—"}</TableCell>
                      <TableCell className="text-right"><Button variant="ghost" size="sm" onClick={() => setSelectedBill(row.payment_bill_no)}>查看明细</Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <span className="text-muted-foreground">共 {integer(total)} 单，第 {page}/{pageCount} 页</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1 || query.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</Button>
              <Button variant="outline" size="sm" disabled={page >= pageCount || query.isFetching} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>下一页</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <PaymentDetailDialog billNo={selectedBill} onClose={() => setSelectedBill(null)} query={detailQuery} />
    </div>
  );
}

function SummaryCard({ title, value, description, icon, tone = "default" }: { title: string; value: string; description: string; icon: ReactNode; tone?: "default" | "amber" | "emerald" }) {
  return (
    <Card className={tone === "amber" ? "border-amber-200 bg-amber-50/40" : tone === "emerald" ? "border-emerald-200 bg-emerald-50/40" : ""}>
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div><div className="text-sm text-muted-foreground">{title}</div><div className="mt-1 text-xl font-semibold tabular-nums text-slate-900">{value}</div><div className="mt-1 text-xs text-muted-foreground">{description}</div></div>
        <div className="rounded-full bg-white p-2 shadow-sm">{icon}</div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ row }: { row: JointPaymentItem }) {
  return row.status === "Y" ? (
    <Badge className="whitespace-nowrap border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-50">已审核</Badge>
  ) : (
    <Badge className="whitespace-nowrap border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-50">生成待确认</Badge>
  );
}

function PaymentDetailDialog({ billNo, onClose, query }: { billNo: string | null; onClose: () => void; query: ReturnType<typeof useJointPaymentConfirmationDetail> }) {
  const head = query.data?.head;
  const lines = query.data?.lines ?? [];
  return (
    <Dialog open={Boolean(billNo)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-[96vw] overflow-y-auto lg:max-w-6xl">
        <DialogHeader>
          <DialogTitle>联营付款单明细</DialogTitle>
          <DialogDescription>{billNo || "—"} · 显示构成付款单的结算批次行</DialogDescription>
        </DialogHeader>
        {query.isLoading ? <div className="flex justify-center p-10"><Loader2 className="h-5 w-5 animate-spin" /></div> : query.isError ? <div className="p-6 text-sm text-rose-600">{query.error instanceof Error ? query.error.message : "明细查询失败"}</div> : head ? (
          <div className="space-y-4">
            <div className="grid gap-px overflow-hidden rounded-md border bg-slate-200 sm:grid-cols-2 lg:grid-cols-4">
              <Info label="付款单号" value={head.payment_bill_no} mono />
              <Info label="状态" value={head.status_label} />
              <Info label="供应商" value={head.supplier_name || head.supplier_code} />
              <Info label="门店" value={head.market_code} />
              <Info label="部门" value={head.department_names || head.department_codes} />
              <Info label="可见付款金额" value={money(head.payment_amount)} />
              <Info label="结算单数" value={`${integer(head.settlement_count)} 单`} />
              <Info label="录入" value={`${textValue(head.inputor)} / ${date(head.inputdate)}`} />
              <Info label="审核" value={head.status === "Y" ? `${textValue(head.auditor)} / ${date(head.auditdate)}` : "待审核"} />
            </div>
            <div className="overflow-x-auto rounded-md border">
              <Table>
                <TableHeader><TableRow><TableHead>行号</TableHead><TableHead>结算单号</TableHead><TableHead>来源单号</TableHead><TableHead>部门/柜组</TableHead><TableHead>合同号</TableHead><TableHead>结算期间</TableHead><TableHead className="text-right">销售收入</TableHead><TableHead className="text-right">开票金额</TableHead><TableHead className="text-right">应付金额</TableHead><TableHead className="text-right">本次付款</TableHead></TableRow></TableHeader>
                <TableBody>{lines.map((line, index) => <TableRow key={`${textValue(line.row_no)}-${index}`}><TableCell>{textValue(line.row_no)}</TableCell><TableCell className="font-mono text-xs">{textValue(line.settlement_bill_no)}</TableCell><TableCell className="font-mono text-xs">{textValue(line.source_bill_no)}</TableCell><TableCell><div>{textValue(line.department_code)} {textValue(line.department_name)}</div><div className="text-xs text-muted-foreground">{textValue(line.group_code)} {textValue(line.group_name)}</div></TableCell><TableCell>{textValue(line.contract_no)}</TableCell><TableCell className="whitespace-nowrap">{date(line.period_start)} 至 {date(line.period_end)}</TableCell><TableCell className="text-right tabular-nums">{money(line.sales_revenue)}</TableCell><TableCell className="text-right tabular-nums">{money(line.invoiced_amount)}</TableCell><TableCell className="text-right tabular-nums">{money(line.payable_amount)}</TableCell><TableCell className="text-right font-medium tabular-nums">{money(line.payment_amount)}</TableCell></TableRow>)}</TableBody>
              </Table>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function Info({ label, value, mono = false }: { label: string; value: unknown; mono?: boolean }) {
  return <div className="bg-white p-3"><div className="text-xs text-muted-foreground">{label}</div><div className={`mt-1 text-sm font-medium ${mono ? "font-mono" : ""}`}>{textValue(value)}</div></div>;
}
