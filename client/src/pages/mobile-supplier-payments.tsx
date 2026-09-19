import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FileText,
  Home,
  Loader2,
  Search,
  ShieldCheck,
  Store,
  WalletCards,
} from "lucide-react";
import { useLocation } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import type {
  JointPaymentDetailResponse,
  JointPaymentItem,
  JointPaymentListResponse,
} from "@/hooks/useJointPaymentConfirmation";
import { apiGet } from "@/lib/api";
import { localDateFromToday } from "@/lib/financialMonth";
import { canAccessModule } from "@/lib/module-permissions";

const PAGE_SIZE = 30;

type PaymentFilterOptions = {
  stores: Array<{ store_code: string; store_name: string }>;
  departments: Array<{ store_code: string; department_code: string; department_name: string }>;
};

const money = (value: unknown) => new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).format(Number(value || 0));

const number = (value: unknown) => new Intl.NumberFormat("zh-CN", {
  maximumFractionDigits: 0,
}).format(Number(value || 0));

const shortDate = (value: unknown) => value ? String(value).slice(0, 10) : "—";
const textValue = (value: unknown) => value == null || value === "" ? "—" : String(value);

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "查询失败，请稍后重试";
}

function statusBadge(item: JointPaymentItem) {
  return item.status === "Y" ? (
    <Badge className="border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-50">已审核</Badge>
  ) : item.supplier_confirmed ? (
    <Badge className="border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-50">已填报确认</Badge>
  ) : (
    <Badge className="border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-50">待审核</Badge>
  );
}

export default function MobileSupplierPaymentsPage() {
  const { menuUser } = useAuth();
  const [, setLocation] = useLocation();
  const previewParams = new URLSearchParams(window.location.search);
  const isPreview = previewParams.get("preview") === "1";
  const isLivePreview = isPreview && previewParams.get("data") === "live";
  const isFormalSnapshot = previewParams.get("data") === "formal";
  const previewSupplierCode = previewParams.get("supplier") || "20624";
  const hasAccess = canAccessModule(menuUser, "mobile-supplier-payments");
  const [statusCode, setStatusCode] = useState(previewParams.get("status") || "ALL");
  const [financialMonthDraft, setFinancialMonthDraft] = useState(() => localDateFromToday().slice(0, 7));
  const [financialMonth, setFinancialMonth] = useState(financialMonthDraft);
  const [monthPickerOpen, setMonthPickerOpen] = useState(false);
  const [monthPickerYear, setMonthPickerYear] = useState(Number(financialMonthDraft.slice(0, 4)));
  const [keywordDraft, setKeywordDraft] = useState("");
  const [keyword, setKeyword] = useState("");
  const [storeDraft, setStoreDraft] = useState("ALL");
  const [departmentDraft, setDepartmentDraft] = useState("ALL");
  const [businessFilters, setBusinessFilters] = useState({ store: "ALL", department: "ALL" });
  const [page, setPage] = useState(1);
  const [selectedBill, setSelectedBill] = useState<string | null>(null);
  const [filterError, setFilterError] = useState("");

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-supplier-payments",
    moduleName: "手机端供应商付款单",
    clientType: "mobile",
    enabled: hasAccess,
  });

  const optionsQuery = useQuery({
    queryKey: ["mobile-supplier-payment-options", menuUser?.user_id],
    queryFn: () => apiGet<PaymentFilterOptions>("/api/erp-settlements/mobile/supplier-payments/options"),
    enabled: hasAccess,
    staleTime: 5 * 60_000,
  });
  const departmentOptions = useMemo(() => {
    const options = (optionsQuery.data?.departments ?? []).filter(
      (item) => storeDraft === "ALL" || item.store_code === storeDraft,
    );
    return Array.from(new Map(options.map((item) => [item.department_code, item])).values());
  }, [optionsQuery.data, storeDraft]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (statusCode !== "ALL") params.set("payment_status", statusCode);
    params.set("financial_month", financialMonth);
    if (businessFilters.store !== "ALL") params.set("market", businessFilters.store);
    if (businessFilters.department !== "ALL") params.set("department_code", businessFilters.department);
    if (keyword) {
      params.set(/^\d+$/.test(keyword) ? "supplier_code" : "supplier_name", keyword);
    }
    return params.toString();
  }, [businessFilters, financialMonth, keyword, page, statusCode]);

  const paymentsQuery = useQuery({
    queryKey: ["mobile-supplier-payments", queryString],
    queryFn: () => apiGet<JointPaymentListResponse>(`/api/erp-settlements/mobile/supplier-payments?${queryString}`),
    enabled: hasAccess,
    staleTime: 30_000,
  });

  const detailQuery = useQuery({
    queryKey: ["mobile-supplier-payment-detail", selectedBill, businessFilters.department],
    queryFn: () => apiGet<JointPaymentDetailResponse>(
      `/api/erp-settlements/mobile/supplier-payments/${encodeURIComponent(selectedBill || "")}${businessFilters.department === "ALL" ? "" : `?${new URLSearchParams({ department_code: businessFilters.department })}`}`,
    ),
    enabled: hasAccess && Boolean(selectedBill),
    staleTime: 30_000,
  });

  const applyFilters = () => {
    if (!/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(financialMonthDraft) || financialMonthDraft.startsWith("0000")) {
      setFilterError("请选择有效的财务月");
      return;
    }
    const nextKeyword = keywordDraft.trim();
    const queryIsUnchanged = financialMonth === financialMonthDraft
      && keyword === nextKeyword
      && businessFilters.store === storeDraft
      && businessFilters.department === departmentDraft
      && page === 1;
    setFilterError("");
    setFinancialMonth(financialMonthDraft);
    setKeyword(nextKeyword);
    setBusinessFilters({ store: storeDraft, department: departmentDraft });
    setPage(1);
    if (queryIsUnchanged) void paymentsQuery.refetch();
    void recordQuery({
      query_type: "supplier_payment",
      payment_status: statusCode,
      financial_month: financialMonthDraft,
      market: storeDraft === "ALL" ? "" : storeDraft,
      department_code: departmentDraft === "ALL" ? "" : departmentDraft,
    });
  };

  if (!hasAccess) {
    return (
      <main className="grid min-h-[100dvh] place-items-center bg-slate-100 p-5">
        <Card className="w-full max-w-md rounded-3xl border-0 shadow-lg">
          <CardContent className="p-7 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <h1 className="mt-4 text-lg font-semibold">暂无供应商付款单权限</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">请联系管理员开通手机端供应商付款单权限，并配置当前账号的查询业务范围。</p>
            <Button variant="outline" className="mt-5" onClick={() => setLocation("/mobile")}>
              <Home className="mr-2 h-4 w-4" />返回首页
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const summary = paymentsQuery.data?.summary;
  const items = paymentsQuery.data?.items ?? [];
  const total = paymentsQuery.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-slate-950">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 px-4 pb-4 pt-[max(.75rem,env(safe-area-inset-top))] text-white shadow-lg">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={() => setLocation("/mobile")} aria-label="返回手机首页">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="text-center">
            <div className="text-[10px] tracking-[0.16em] text-emerald-200">SUPPLIER PAYMENT</div>
            <h1 className="text-base font-semibold">供应商付款单</h1>
          </div>
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={() => setLocation("/mobile")} aria-label="返回手机首页">
            <Home className="h-5 w-5" />
          </Button>
        </div>

        <div className="mt-3 rounded-2xl bg-white/10 p-3 backdrop-blur">
          <div className="mb-2 grid grid-cols-2 gap-2">
            <div className="min-w-0">
              <label htmlFor="mobile-payment-store" className="text-[10px] text-slate-300">门店</label>
              <Select value={storeDraft} onValueChange={(value) => { setStoreDraft(value); setDepartmentDraft("ALL"); }} disabled={optionsQuery.isLoading || optionsQuery.isError}>
                <SelectTrigger id="mobile-payment-store" className="mt-1 h-9 w-full min-w-0 border-white/20 bg-white text-xs text-slate-900"><SelectValue placeholder="全部门店" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部门店</SelectItem>
                  {(optionsQuery.data?.stores ?? []).map((store) => <SelectItem key={store.store_code} value={store.store_code}>{store.store_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-0">
              <label htmlFor="mobile-payment-department" className="text-[10px] text-slate-300">部门</label>
              <Select value={departmentDraft} onValueChange={setDepartmentDraft} disabled={optionsQuery.isLoading || optionsQuery.isError}>
                <SelectTrigger id="mobile-payment-department" className="mt-1 h-9 w-full min-w-0 border-white/20 bg-white text-xs text-slate-900"><SelectValue placeholder="全部部门" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部部门</SelectItem>
                  {departmentOptions.map((department) => <SelectItem key={department.department_code} value={department.department_code}>{department.department_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          {optionsQuery.isError ? <p className="mb-2 text-xs text-rose-200">门店、部门加载失败，<button type="button" className="underline" onClick={() => void optionsQuery.refetch()}>点击重试</button></p> : null}
          <div>
            <label htmlFor="mobile-payment-month" className="text-[10px] text-slate-300">财务月</label>
            <Popover open={monthPickerOpen} onOpenChange={(open) => { setMonthPickerOpen(open); if (open) setMonthPickerYear(Number(financialMonthDraft.slice(0, 4))); }}>
              <PopoverTrigger asChild>
                <Button id="mobile-payment-month" type="button" variant="outline" className="mt-1 h-9 w-full justify-between border-white/20 bg-white text-xs font-normal text-slate-900" aria-describedby="mobile-payment-month-help">
                  {financialMonthDraft.slice(0, 4)} 年 {Number(financialMonthDraft.slice(5))} 月
                  <CalendarDays className="h-4 w-4 text-slate-500" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="start" className="w-64 bg-white p-3 text-slate-900" aria-label="选择财务月">
                <div className="mb-2 flex items-center justify-between">
                  <Button type="button" variant="ghost" size="icon" className="h-8 w-8" aria-label="上一年" disabled={monthPickerYear <= 1} onClick={() => setMonthPickerYear((year) => year - 1)}><ChevronLeft className="h-4 w-4" /></Button>
                  <span className="text-sm font-semibold" aria-live="polite">{monthPickerYear} 年</span>
                  <Button type="button" variant="ghost" size="icon" className="h-8 w-8" aria-label="下一年" disabled={monthPickerYear >= 9999} onClick={() => setMonthPickerYear((year) => year + 1)}><ChevronRight className="h-4 w-4" /></Button>
                </div>
                <div className="grid grid-cols-3 gap-1">
                  {Array.from({ length: 12 }, (_, index) => {
                    const month = `${String(monthPickerYear).padStart(4, "0")}-${String(index + 1).padStart(2, "0")}`;
                    const selected = financialMonthDraft === month;
                    return <Button key={month} type="button" variant="ghost" aria-pressed={selected} className={`h-9 text-xs ${selected ? "bg-emerald-600 text-white hover:bg-emerald-700 hover:text-white" : "text-slate-700"}`} onClick={() => { setFinancialMonthDraft(month); setMonthPickerOpen(false); }}>{index + 1} 月</Button>;
                  })}
                </div>
              </PopoverContent>
            </Popover>
            <p id="mobile-payment-month-help" className="mt-1 text-[10px] text-slate-300">按生成月份归属，月底 29—31 日仍计入当月</p>
          </div>
          <form className="mt-2 flex gap-2" onSubmit={(event) => { event.preventDefault(); applyFilters(); }}>
            <div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><Input className="h-9 bg-white pl-9 text-slate-900" value={keywordDraft} onChange={(event) => setKeywordDraft(event.target.value)} placeholder="供应商号（精确）或名称（模糊）" /></div>
            <Button type="submit" size="sm" className="h-9 bg-emerald-600 hover:bg-emerald-500">查询</Button>
          </form>
          {filterError ? <p className="mt-2 text-xs text-rose-200">{filterError}</p> : null}
        </div>
      </header>

      <div className="mx-auto max-w-xl space-y-3 px-3 pt-3">
        {isPreview ? (
          <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-xs font-medium text-sky-800 shadow-sm">
            {isLivePreview
              ? "正式数据只读预览 · 全部业务范围 · 供应商确认状态每小时同步"
              : isFormalSnapshot
              ? `正式数据只读快照 · 供应商 ${previewSupplierCode} · 查询时间 2026-08-26 · 不写入正式库`
              : "测试预览 · 当前为模拟数据，不连接正式数据库"}
          </div>
        ) : null}
        <Card className="rounded-3xl border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-2">
              <PaymentStageCard
                label="已生成" tone="amber" wide icon={<Clock3 className="h-4 w-4" />}
                suppliers={summary?.total_generated_supplier_count} count={summary?.total_generated_count} amount={summary?.total_generated_amount}
                ready={Boolean(summary) && !paymentsQuery.isError} selected={statusCode === "ALL"}
                onClick={() => { setStatusCode("ALL"); setPage(1); }}
              />
              <PaymentStageCard
                label="已填报" tone="sky" icon={<FileText className="h-4 w-4" />}
                suppliers={summary?.supplier_confirmed_supplier_count} count={summary?.supplier_confirmed_count} amount={summary?.supplier_confirmed_amount}
                ready={Boolean(summary?.supplier_confirmation_available) && !paymentsQuery.isError} selected={statusCode === "C"}
                onClick={() => { setStatusCode("C"); setPage(1); }}
              />
              <PaymentStageCard
                label="未填报" tone="slate" icon={<Clock3 className="h-4 w-4" />}
                suppliers={summary?.supplier_unreported_supplier_count} count={summary?.supplier_unreported_count} amount={summary?.supplier_unreported_amount}
                ready={Boolean(summary?.supplier_confirmation_available) && !paymentsQuery.isError} selected={statusCode === "N"}
                onClick={() => { setStatusCode("N"); setPage(1); }}
              />
              <PaymentStageCard
                label="已审核" tone="emerald" icon={<CheckCircle2 className="h-4 w-4" />}
                suppliers={summary?.audited_supplier_count} count={summary?.audited_count} amount={summary?.audited_amount}
                ready={Boolean(summary) && !paymentsQuery.isError} selected={statusCode === "Y"}
                onClick={() => { setStatusCode("Y"); setPage(1); }}
              />
              <PaymentStageCard
                label="未审核" tone="amber" icon={<Clock3 className="h-4 w-4" />}
                suppliers={summary?.generated_supplier_count} count={summary?.generated_count} amount={summary?.generated_amount}
                ready={Boolean(summary) && !paymentsQuery.isError} selected={statusCode === "M"}
                onClick={() => { setStatusCode("M"); setPage(1); }}
              />
            </div>
            <p className="mt-3 text-[10px] leading-4 text-slate-500">{financialMonth} · 按生成月份归属；已填报指供应商已确认。各项家数分别去重，金额按可见付款金额统计。</p>
            {summary && !summary.supplier_confirmation_available ? <p className="mt-1 text-[10px] text-amber-700">供应商确认数据暂不可用，请稍后重试。</p> : null}
            <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400"><span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3" />{isFormalSnapshot ? `仅含供应商 ${previewSupplierCode}` : "按查询业务范围显示"}</span><span>{isFormalSnapshot ? "数据为查询时点快照" : "跨范围单据仅计可见部分"}</span></div>
          </CardContent>
        </Card>

        <Card className="rounded-3xl border-0 shadow-sm"><CardContent className="p-3">
          <Select value={statusCode} onValueChange={(value) => { setStatusCode(value); setPage(1); }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">生成的付款单（全部）</SelectItem><SelectItem value="C" disabled={!summary?.supplier_confirmation_available}>供应商已填报确认</SelectItem><SelectItem value="N" disabled={!summary?.supplier_confirmation_available}>未填报（全部）</SelectItem><SelectItem value="Y">已审核的付款单</SelectItem><SelectItem value="U" disabled={!summary?.supplier_confirmation_available}>已生成未填报</SelectItem><SelectItem value="P" disabled={!summary?.supplier_confirmation_available}>已填报未审核</SelectItem><SelectItem value="M">待审核（全部）</SelectItem></SelectContent></Select>
        </CardContent></Card>

        <div className="flex items-center justify-between px-1"><div><div className="text-sm font-semibold">付款单</div><div className="text-[10px] text-slate-500">共 {number(total)} 单，点击查看结算构成</div></div><WalletCards className="h-5 w-5 text-emerald-700" /></div>

        {paymentsQuery.isLoading ? (
          <div className="flex items-center justify-center rounded-3xl bg-white py-16 text-sm text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在读取付款单…</div>
        ) : paymentsQuery.isError ? (
          <Card className="rounded-3xl border-rose-200 bg-rose-50"><CardContent className="p-5 text-sm leading-6 text-rose-700">{errorText(paymentsQuery.error)}</CardContent></Card>
        ) : items.length ? (
          <div className="space-y-2">
            {items.map((item) => (
              <button key={item.payment_bill_no} type="button" className="w-full rounded-3xl bg-white p-4 text-left shadow-sm transition active:scale-[0.99]" onClick={() => setSelectedBill(item.payment_bill_no)} aria-label={`查看付款单 ${item.payment_bill_no} 的结算明细`}>
                <div className="flex items-start justify-between gap-3"><div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{item.supplier_name || item.supplier_code || "未命名供应商"}</div><div className="mt-1 font-mono text-[11px] text-slate-400">{item.payment_bill_no}</div></div><div className="flex shrink-0 items-center gap-2">{statusBadge(item)}<ChevronRight className="h-4 w-4 text-slate-300" /></div></div>
                <div className="mt-3 grid grid-cols-[1fr_auto] items-end gap-3"><div className="space-y-1 text-[10px] text-slate-500"><div className="flex items-center gap-1"><Store className="h-3 w-3" />{item.department_names || item.department_codes || item.market_code || "—"}</div><div className="flex items-center gap-1"><CalendarDays className="h-3 w-3" />生成 {shortDate(item.inputdate)} · {number(item.settlement_count)} 张结算单</div></div><div className="text-right"><div className="text-[9px] text-slate-400">可见付款金额</div><div className="mt-0.5 whitespace-nowrap font-mono text-lg font-bold tabular-nums text-emerald-700">{money(item.payment_amount)}</div></div></div>
              </button>
            ))}
            <div className="flex items-center justify-between py-2"><Button variant="outline" size="sm" disabled={page <= 1 || paymentsQuery.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</Button><span className="text-xs text-slate-400">第 {page} / {pageCount} 页</span><Button variant="outline" size="sm" disabled={page >= pageCount || paymentsQuery.isFetching} onClick={() => setPage((value) => Math.min(pageCount, value + 1))}>下一页</Button></div>
          </div>
        ) : (
          <div className="rounded-3xl bg-white px-6 py-16 text-center text-sm leading-6 text-slate-400">当前条件下没有查询业务范围内的供应商付款单<br /><span className="text-xs">请检查当前账号的查询业务范围或筛选条件</span></div>
        )}
      </div>

      <Sheet open={Boolean(selectedBill)} onOpenChange={(open) => { if (!open) setSelectedBill(null); }}>
        <SheetContent side="bottom" className="z-[60] h-[92dvh] overflow-hidden rounded-t-3xl bg-white p-0 text-slate-950">
          <SheetHeader className="border-b px-5 py-4 pr-12 text-left"><SheetTitle>付款单明细</SheetTitle><SheetDescription>{selectedBill || "—"} · {isFormalSnapshot ? "正式数据只读快照" : "仅显示当前账号查询业务范围"}{businessFilters.department !== "ALL" ? " · 已按部门筛选" : ""}</SheetDescription></SheetHeader>
          <div className="h-[calc(92dvh-5.5rem)] overflow-y-auto px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
            {detailQuery.isLoading ? <div className="flex justify-center py-16 text-sm text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载结算明细…</div> : detailQuery.isError ? <div className="mt-5 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">{errorText(detailQuery.error)}</div> : detailQuery.data ? <PaymentDetail data={detailQuery.data} /> : null}
          </div>
        </SheetContent>
      </Sheet>
    </main>
  );
}

function PaymentStageCard({ label, tone, icon, suppliers, count, amount, ready, selected, onClick, wide = false }: {
  label: string; tone: "amber" | "sky" | "emerald" | "slate"; icon: React.ReactNode; wide?: boolean;
  suppliers?: number | null; count?: number | null; amount?: number | null;
  ready: boolean; selected: boolean; onClick: () => void;
}) {
  const colors = {
    slate: "bg-slate-100 text-slate-700 ring-slate-400",
    amber: "bg-amber-50 text-amber-800 ring-amber-300",
    sky: "bg-sky-50 text-sky-800 ring-sky-300",
    emerald: "bg-emerald-50 text-emerald-800 ring-emerald-300",
  };
  const available = ready && suppliers != null && count != null && amount != null;
  return <button type="button" disabled={!available} onClick={onClick} aria-pressed={selected}
    className={`w-full min-w-0 rounded-2xl p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 ${colors[tone]} ${wide ? "col-span-2" : ""} ${selected ? "ring-2" : ""}`}>
    <div className="flex items-center gap-1.5 text-xs font-medium">{icon}{label}</div>
    <div className={`mt-2 ${wide ? "flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1" : "space-y-1"}`}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 tabular-nums">
        <span className="text-xl font-bold">{available ? number(suppliers) : "—"}<span className="ml-1 text-xs font-medium">家</span></span>
        <span className="text-xs opacity-75">{available ? number(count) : "—"} 单</span>
      </div>
      <div className={`whitespace-nowrap font-mono font-bold tabular-nums ${wide ? "text-lg" : "text-[11px] min-[380px]:text-sm"}`}>{available ? money(amount) : "—"}</div>
    </div>
  </button>;
}

function PaymentDetail({ data }: { data: JointPaymentDetailResponse }) {
  const head = data.head;
  const charges = data.charges ?? [];
  const ticketReductions = charges.filter((charge) => String(charge.person1 || "").trim().toUpperCase() === "Y");
  const expenses = charges.filter((charge) => String(charge.person1 || "N").trim().toUpperCase() !== "Y");
  return (
    <div className="mt-5 space-y-3">
      <div className="rounded-3xl bg-emerald-50 p-4">
        <div className="flex items-start justify-between gap-3"><div><div className="text-xs text-emerald-700">{head.supplier_name || head.supplier_code || "未命名供应商"}</div><div className="mt-1 font-mono text-[11px] text-emerald-600">{head.payment_bill_no}</div></div>{statusBadge(head)}</div>
        <div className="mt-4 text-[10px] text-emerald-600">实际应付（当前可见）</div>
        <div className="mt-1 font-mono text-2xl font-bold text-emerald-800">{money(head.payment_amount)}</div>
        <div className="mt-4 grid grid-cols-2 gap-2 border-t border-emerald-200 pt-3">
          <AmountMetric label="销售收入" value={head.sales_revenue} />
          <AmountMetric label="应开票金额" value={head.invoiced_amount} />
          <AmountMetric label="票减" value={head.ticket_reduction_amount} tone="ticket" />
          <AmountMetric label="费用" value={head.expense_amount} tone="expense" />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-emerald-700"><div>生成日期 {shortDate(head.inputdate)}</div><div>审核日期 {shortDate(head.auditdate)}</div><div>付款日期 {shortDate(head.payment_date)}</div><div>结算单 {number(head.settlement_count)} 张</div><div>柜组 {number(head.group_count)} 个</div></div>
      </div>

      <div className="flex items-center justify-between px-1"><div className="text-sm font-semibold">收入构成</div><div className="text-[10px] text-slate-400">{data.lines.length} 行</div></div>
      {data.lines.map((line, index) => (
        <Card key={`${textValue(line.row_no)}-${index}`} className="rounded-2xl shadow-none">
          <CardContent className="p-3">
            <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="truncate text-sm font-semibold">{textValue(line.group_name)}</div><div className="mt-1 font-mono text-[10px] text-slate-400">{textValue(line.group_code)}</div></div><div className="shrink-0 text-right"><div className="text-[9px] text-slate-400">销售收入</div><div className="font-mono text-sm font-bold text-emerald-700">{money(line.sales_revenue)}</div></div></div>
            <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl bg-slate-50 px-3 py-2 text-[10px]"><div className="text-slate-500">应开票金额<div className="mt-0.5 font-mono text-xs font-semibold text-slate-800">{money(line.invoiced_amount)}</div></div><div className="text-right text-slate-500">实际应付<div className="mt-0.5 font-mono text-xs font-semibold text-emerald-700">{money(line.payment_amount)}</div></div><div className="text-amber-700">票减<div className="mt-0.5 font-mono text-xs font-semibold">{money(line.fee_amount_1)}</div></div><div className="text-right text-rose-600">费用<div className="mt-0.5 font-mono text-xs font-semibold">{money(line.fee_amount_2)}</div></div></div>
            <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 border-t pt-3 text-[10px] text-slate-500"><div className="truncate">结算单 {textValue(line.settlement_bill_no)}</div><div className="truncate">合同 {textValue(line.contract_no)}</div><div className="col-span-2">{shortDate(line.period_start)} 至 {shortDate(line.period_end)}</div></div>
          </CardContent>
        </Card>
      ))}
      {!data.lines.length ? <div className="rounded-2xl bg-slate-50 py-12 text-center text-sm text-slate-400"><FileText className="mx-auto mb-2 h-5 w-5" />没有可见结算批次</div> : null}

      <ChargeSection title="票减明细" tone="ticket" total={head.ticket_reduction_amount} detailTotal={head.ticket_reduction_detail_amount} matches={head.ticket_reduction_detail_matches} charges={ticketReductions} emptyText="当前查询业务范围没有票减明细" />
      <ChargeSection title="费用明细" tone="expense" total={head.expense_amount} detailTotal={head.expense_detail_amount} matches={head.expense_detail_matches} charges={expenses} emptyText="当前查询业务范围没有非票减费用明细" />
    </div>
  );
}

function ChargeSection({ title, total, detailTotal, matches, charges, emptyText, tone }: { title: string; total: unknown; detailTotal: unknown; matches: boolean | undefined; charges: Array<Record<string, unknown>>; emptyText: string; tone: "ticket" | "expense" }) {
  const color = tone === "ticket" ? "text-amber-700" : "text-rose-600";
  const border = tone === "ticket" ? "border-amber-100" : "border-rose-100";
  return <section className="space-y-2 pt-2">
    <div className="flex items-center justify-between px-1"><div><div className="text-sm font-semibold">{title}</div><div className="text-[10px] text-slate-400">付款汇总口径 · 按查询业务范围显示</div></div><div className={`font-mono text-sm font-bold ${color}`}>{money(total)}</div></div>
    {matches === false ? <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[10px] leading-4 text-amber-800">关联明细合计 {money(detailTotal)}，与付款汇总存在历史差异；页面以付款汇总金额为准，明细仅供参考。</div> : null}
    {charges.map((charge, index) => <Card key={`${textValue(charge.sscbillno)}-${textValue(charge.sscrowno)}-${index}`} className={`rounded-2xl ${border} shadow-none`}><CardContent className="p-3"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="text-sm font-semibold leading-5">{textValue(charge.expense_name_display ?? charge.sscname)}</div><div className="mt-1 text-[10px] text-slate-400">{textValue(charge.counter_display ?? charge.sscmfid)}</div></div><div className={`shrink-0 font-mono text-sm font-bold ${color}`}>{money(charge.sscmoney)}</div></div><div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 border-t pt-3 text-[10px] text-slate-500"><span>{textValue(charge.person1_label ?? charge.person1)}</span><span>发生月 {textValue(charge.sscfsmon)}</span><span>{shortDate(charge.sscfsdate)}</span><span>{textValue(charge.sscflag_label ?? charge.sscflag)}</span></div></CardContent></Card>)}
    {!charges.length ? <div className="rounded-2xl bg-slate-50 py-8 text-center text-sm text-slate-400">{emptyText}</div> : null}
  </section>;
}

function AmountMetric({ label, value, tone = "income" }: { label: string; value: unknown; tone?: "income" | "ticket" | "expense" }) {
  const color = tone === "expense" ? "text-rose-600" : tone === "ticket" ? "text-amber-700" : "text-emerald-800";
  return <div className="min-w-0"><div className="text-[9px] text-emerald-600">{label}</div><div className={`mt-1 truncate font-mono text-[11px] font-bold ${color}`}>{money(value)}</div></div>;
}
