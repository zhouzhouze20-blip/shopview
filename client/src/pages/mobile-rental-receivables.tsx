import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  CalendarDays,
  ChevronRight,
  CircleDollarSign,
  FileText,
  Home,
  Landmark,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Store,
  Users,
} from "lucide-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import type {
  RentalReceivableDetail,
  RentalReceivableItem,
  RentalReceivablesResponse,
} from "@/hooks/useRentalReceivables";
import { apiGet } from "@/lib/api";
import { canAccessModule } from "@/lib/module-permissions";
import { supplierActualReceivableAmount } from "@/lib/rental-receivable-amounts";

type DrillLevel = "store" | "department" | "group" | "bills";

type DrillItem = {
  code: string;
  name: string;
  bill_count: number;
  next_count: number;
  receivable_amount: number;
  original_receivable_amount: number;
  sales_refund_amount: number;
  partial_count: number;
  anomaly_count: number;
  over_90_amount: number;
  latest_settle_to: string | null;
};

type DrillResponse = {
  level: Exclude<DrillLevel, "bills">;
  items: DrillItem[];
  summary: {
    bill_count: number;
    receivable_amount: number;
    original_receivable_amount: number;
    sales_refund_amount: number;
    partial_count: number;
    anomaly_count: number;
    over_90_amount: number;
  };
  source: { name?: string };
  source_loaded_at: string;
  queried_at: string;
  permission_scoped: boolean;
};

type Selection = { code: string; name: string };

const isoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const defaultRange = () => {
  const today = new Date();
  return {
    start: `${today.getFullYear()}-01-01`,
    end: isoDate(today),
  };
};

const money = (value?: number | null) =>
  new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));

const shortDate = (value?: string | null) => (value ? value.slice(0, 10) : "—");

const levelMeta: Record<DrillLevel, { title: string; next: string; icon: typeof Store }> = {
  store: { title: "门店", next: "部门", icon: Store },
  department: { title: "部门", next: "柜组", icon: Building2 },
  group: { title: "柜组", next: "明细", icon: Users },
  bills: { title: "结算单明细", next: "金额明细", icon: FileText },
};

function errorText(error: unknown) {
  return error instanceof Error ? error.message : "查询失败，请稍后重试";
}

export default function MobileRentalReceivablesPage() {
  const { menuUser } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-rental-receivables");
  const initialRange = useMemo(defaultRange, []);
  const [draftStart, setDraftStart] = useState(initialRange.start);
  const [draftEnd, setDraftEnd] = useState(initialRange.end);
  const [range, setRange] = useState(initialRange);
  const [dateError, setDateError] = useState("");
  const [level, setLevel] = useState<DrillLevel>("store");
  const [storeSelection, setStoreSelection] = useState<Selection | null>(null);
  const [departmentSelection, setDepartmentSelection] = useState<Selection | null>(null);
  const [groupSelection, setGroupSelection] = useState<Selection | null>(null);
  const [billPage, setBillPage] = useState(1);
  const [selectedBill, setSelectedBill] = useState<RentalReceivableItem | null>(null);
  const [showAllDetails, setShowAllDetails] = useState(false);

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-rental-receivables",
    moduleName: "手机端租赁应收未收",
    clientType: "mobile",
    enabled: hasAccess,
  });

  const drillParams = useMemo(() => {
    const params = new URLSearchParams({
      level: level === "bills" ? "group" : level,
      settle_from: range.start,
      settle_to: range.end,
    });
    if (storeSelection) params.set("mkt", storeSelection.code);
    if (departmentSelection) params.set("department_code", departmentSelection.code);
    return params.toString();
  }, [departmentSelection, level, range.end, range.start, storeSelection]);

  const drillQuery = useQuery({
    queryKey: ["mobile-rental-receivables-drilldown", drillParams],
    queryFn: () => apiGet<DrillResponse>(`/api/rental-receivables/mobile/drilldown?${drillParams}`),
    enabled: hasAccess && level !== "bills",
    staleTime: 30_000,
  });

  const billParams = useMemo(() => {
    if (!storeSelection || !departmentSelection || !groupSelection) return "";
    return new URLSearchParams({
      settle_from: range.start,
      settle_to: range.end,
      mkt: storeSelection.code,
      department_code: departmentSelection.code,
      group_code: groupSelection.code,
      page: String(billPage),
      page_size: "50",
    }).toString();
  }, [billPage, departmentSelection, groupSelection, range.end, range.start, storeSelection]);

  const billsQuery = useQuery({
    queryKey: ["mobile-rental-receivables-bills", billParams],
    queryFn: () => apiGet<RentalReceivablesResponse>(`/api/rental-receivables/mobile/bills?${billParams}`),
    enabled: hasAccess && level === "bills" && Boolean(billParams),
    staleTime: 30_000,
  });

  const detailQuery = useQuery({
    queryKey: ["mobile-rental-receivables-detail", selectedBill?.bill_no],
    queryFn: () => apiGet<RentalReceivableDetail>(
      `/api/rental-receivables/mobile/bills/${encodeURIComponent(selectedBill?.bill_no || "")}/details`,
    ),
    enabled: hasAccess && Boolean(selectedBill?.bill_no),
    staleTime: 30_000,
  });

  const summary = level === "bills" ? billsQuery.data?.summary : drillQuery.data?.summary;
  const sourceLoadedAt = level === "bills" ? billsQuery.data?.source_loaded_at : drillQuery.data?.source_loaded_at;
  const loading = level === "bills" ? billsQuery.isLoading : drillQuery.isLoading;
  const queryError = level === "bills" ? billsQuery.error : drillQuery.error;

  const applyDateRange = () => {
    if (!draftStart || !draftEnd || draftStart > draftEnd) {
      setDateError("请选择有效的起止日期");
      return;
    }
    setDateError("");
    setRange({ start: draftStart, end: draftEnd });
    setLevel("store");
    setStoreSelection(null);
    setDepartmentSelection(null);
    setGroupSelection(null);
    setBillPage(1);
    void recordQuery({
      query_type: "rental_receivables",
      settle_from: draftStart,
      settle_to: draftEnd,
      query_level: "store",
    });
  };

  const moveBack = () => {
    if (level === "bills") {
      setLevel("group");
      setGroupSelection(null);
      setBillPage(1);
    } else if (level === "group") {
      setLevel("department");
      setDepartmentSelection(null);
    } else if (level === "department") {
      setLevel("store");
      setStoreSelection(null);
    } else {
      setLocation("/mobile");
    }
  };

  const selectDrillItem = (item: DrillItem) => {
    if (level === "store") {
      setStoreSelection({ code: item.code, name: item.name });
      setLevel("department");
    } else if (level === "department") {
      setDepartmentSelection({ code: item.code, name: item.name });
      setLevel("group");
    } else if (level === "group") {
      setGroupSelection({ code: item.code, name: item.name });
      setBillPage(1);
      setLevel("bills");
    }
    void recordQuery({
      query_type: "rental_receivables",
      settle_from: range.start,
      settle_to: range.end,
      query_level: levelMeta[level].next,
      selected_code: item.code,
    });
  };

  const openBill = (bill: RentalReceivableItem) => {
    setShowAllDetails(false);
    setSelectedBill(bill);
  };

  const detailItems = detailQuery.data?.items ?? [];
  const visibleDetails = showAllDetails
    ? detailItems
    : detailItems.filter((item) => Math.abs(item.balance_amount) >= 0.005);

  if (!hasAccess) {
    return (
      <main className="grid min-h-[100dvh] place-items-center bg-slate-100 p-5">
        <Card className="w-full max-w-md rounded-3xl border-0 shadow-lg">
          <CardContent className="p-7 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <h1 className="mt-4 text-lg font-semibold">暂无手机端应收未收权限</h1>
            <p className="mt-2 text-sm leading-6 text-slate-500">需同时开通手机端租赁应收权限和结算单查看权限。</p>
            <Button variant="outline" className="mt-5" onClick={() => setLocation("/mobile")}>
              <Home className="mr-2 h-4 w-4" />返回首页
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-slate-950">
      <header className="sticky top-0 z-20 bg-gradient-to-br from-slate-950 via-slate-900 to-rose-950 px-4 pb-4 pt-[max(.75rem,env(safe-area-inset-top))] text-white shadow-lg">
        <div className="flex items-center justify-between">
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={moveBack} aria-label="返回上一级">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="text-center">
            <div className="text-[10px] tracking-[0.16em] text-rose-200">租赁结算</div>
            <h1 className="text-base font-semibold">应收未收</h1>
          </div>
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={() => setLocation("/mobile")} aria-label="返回手机首页">
            <Home className="h-5 w-5" />
          </Button>
        </div>

        <div className="mt-3 grid grid-cols-[1fr_1fr_auto] gap-2 rounded-2xl bg-white/10 p-2 backdrop-blur">
          <div>
            <label htmlFor="mobile-receivable-start" className="text-[10px] text-slate-300">截止日起</label>
            <Input id="mobile-receivable-start" type="date" className="mt-1 h-9 border-white/20 bg-white text-xs text-slate-900" value={draftStart} onChange={(event) => setDraftStart(event.target.value)} />
          </div>
          <div>
            <label htmlFor="mobile-receivable-end" className="text-[10px] text-slate-300">截止日止</label>
            <Input id="mobile-receivable-end" type="date" className="mt-1 h-9 border-white/20 bg-white text-xs text-slate-900" value={draftEnd} onChange={(event) => setDraftEnd(event.target.value)} />
          </div>
          <Button size="icon" className="mt-[18px] h-9 w-9 bg-rose-500 text-white hover:bg-rose-400" onClick={applyDateRange} aria-label="查询日期范围">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        {dateError ? <p className="mt-2 text-xs text-rose-200">{dateError}</p> : null}
      </header>

      <div className="mx-auto max-w-xl space-y-3 px-3 pt-3">
        <Card className="rounded-3xl border-0 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-1 overflow-x-auto pb-1 text-xs">
              <button type="button" className="shrink-0 font-medium text-rose-700" onClick={() => { setLevel("store"); setStoreSelection(null); setDepartmentSelection(null); setGroupSelection(null); }}>门店</button>
              {storeSelection ? <><ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" /><button type="button" className="max-w-28 shrink-0 truncate font-medium text-rose-700" onClick={() => { setLevel("department"); setDepartmentSelection(null); setGroupSelection(null); }}>{storeSelection.name}</button></> : null}
              {departmentSelection ? <><ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" /><button type="button" className="max-w-28 shrink-0 truncate font-medium text-rose-700" onClick={() => { setLevel("group"); setGroupSelection(null); }}>{departmentSelection.name}</button></> : null}
              {groupSelection ? <><ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" /><span className="max-w-32 shrink-0 truncate font-medium text-slate-700">{groupSelection.name}</span></> : null}
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="col-span-2 flex items-center justify-between gap-3 rounded-2xl bg-rose-50 p-3">
                <div className="text-xs text-rose-600">应收未收</div>
                <div className="whitespace-nowrap font-mono text-xl font-bold tabular-nums text-rose-700">{money(summary?.receivable_amount)}</div>
              </div>
              <div className="col-span-2 flex items-center justify-between gap-3 rounded-2xl bg-violet-50 p-3">
                <div>
                  <div className="text-xs text-violet-700">供应商实际应收金额</div>
                  <div className="mt-0.5 text-[9px] text-violet-500">应收未收 − 销售返款</div>
                </div>
                <div className="whitespace-nowrap font-mono text-xl font-bold tabular-nums text-violet-800">{money(supplierActualReceivableAmount(summary?.receivable_amount, summary?.sales_refund_amount))}</div>
              </div>
              <div className="rounded-2xl bg-slate-100 p-3">
                <div className="text-[10px] text-slate-500">结算单</div>
                <div className="mt-1 whitespace-nowrap text-base font-bold tabular-nums">{summary?.bill_count ?? 0} 张</div>
              </div>
              <div className="rounded-2xl bg-amber-50 p-3">
                <div className="text-[10px] text-amber-700">90 天以上</div>
                <div className="mt-1 whitespace-nowrap font-mono text-sm font-bold tabular-nums text-amber-800">{money(summary?.over_90_amount)}</div>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-[10px] text-slate-400">
              <span className="inline-flex items-center gap-1"><ShieldCheck className="h-3 w-3" />已按账号权限过滤</span>
              <span>数据截至 {sourceLoadedAt ? shortDate(sourceLoadedAt) : "—"}</span>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-between gap-2 px-1">
          <div className="flex min-w-0 items-baseline gap-2">
            <div className="shrink-0 text-sm font-semibold">{levelMeta[level].title}</div>
            <div className="truncate text-[10px] text-slate-500">逐级进入{levelMeta[level].next}，每一级均校验权限</div>
          </div>
          <CalendarDays className="h-4 w-4 shrink-0 text-slate-400" />
        </div>

        {loading ? (
          <div className="flex items-center justify-center rounded-3xl bg-white py-16 text-sm text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询本地 ODS…</div>
        ) : queryError ? (
          <Card className="rounded-3xl border-rose-200 bg-rose-50"><CardContent className="p-5 text-sm leading-6 text-rose-700">{errorText(queryError)}</CardContent></Card>
        ) : level !== "bills" ? (
          drillQuery.data?.items.length ? (
            <div className="space-y-1">
              {drillQuery.data.items.map((item) => {
                const Icon = levelMeta[level].icon;
                return (
                  <button key={`${level}:${item.code}`} type="button" className="w-full rounded-2xl bg-white px-3 py-2 text-left shadow-sm transition active:scale-[0.99]" onClick={() => selectDrillItem(item)}>
                    <div className="flex items-center gap-2">
                      <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-rose-50 text-rose-700"><Icon className="h-3.5 w-3.5" /></div>
                      <div className="min-w-0 flex-1">
                        <div className="flex min-w-0 items-center gap-2">
                          <div className="truncate text-[13px] font-semibold leading-4">{item.name}</div>
                          <div className="shrink-0 font-mono text-[9px] leading-3 text-slate-400">{item.code}</div>
                        </div>
                        <div className="mt-0.5 flex min-w-0 items-center gap-1.5 leading-4">
                          <div className={`whitespace-nowrap font-mono text-[13px] font-bold tabular-nums ${item.receivable_amount < 0 ? "text-emerald-700" : "text-rose-600"}`}>{money(item.receivable_amount)}</div>
                          {item.partial_count ? <span className="truncate text-[8px] text-amber-700" title={`部分未收 ${item.partial_count} 张`}>部分 {item.partial_count}</span> : null}
                          {item.anomaly_count ? <span className="truncate text-[8px] text-red-700" title={`异常 ${item.anomaly_count} 张`}>异常 {item.anomaly_count}</span> : null}
                        </div>
                      </div>
                      <div className="w-12 shrink-0 text-right text-[9px] leading-3.5 text-slate-500"><div>{item.bill_count} 张</div><div>{item.next_count} {level === "store" ? "部门" : level === "department" ? "柜组" : "供应商"}</div></div>
                      <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                    </div>
                  </button>
                );
              })}
            </div>
          ) : <div className="rounded-3xl bg-white py-16 text-center text-sm text-slate-400">当前范围没有应收未收数据</div>
        ) : billsQuery.data?.items.length ? (
          <div className="space-y-2">
            {billsQuery.data.items.map((bill) => (
              <button key={bill.bill_no} type="button" className="w-full rounded-3xl bg-white p-4 text-left shadow-sm transition active:scale-[0.99]" onClick={() => openBill(bill)} aria-label={`查看结算单 ${bill.bill_no} 的金额明细`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0"><div className="truncate text-sm font-semibold">{bill.supplier_name || bill.supplier_id || "未命名供应商"}</div><div className="mt-1 font-mono text-[11px] text-slate-400">{bill.bill_no}</div></div>
                  <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                </div>
                <div className="mt-3 grid grid-cols-[1fr_auto] items-end gap-3">
                  <div className="text-[11px] leading-5 text-slate-500"><div>合同 {bill.contract_no || "—"}</div><div>{shortDate(bill.settle_from)} 至 {shortDate(bill.settle_to)}</div></div>
                  <div className="text-right"><div className="text-[10px] text-slate-400">应收未收</div><div className={`mt-0.5 font-mono text-lg font-bold tabular-nums ${bill.receivable_amount < 0 ? "text-emerald-700" : "text-rose-600"}`}>{money(bill.receivable_amount)}</div></div>
                </div>
              </button>
            ))}
            <div className="flex items-center justify-between py-2">
              <Button variant="outline" size="sm" disabled={billPage <= 1} onClick={() => setBillPage((value) => Math.max(1, value - 1))}>上一页</Button>
              <span className="text-xs text-slate-400">第 {billPage} / {Math.max(1, Math.ceil((billsQuery.data?.total || 0) / 50))} 页</span>
              <Button variant="outline" size="sm" disabled={billPage * 50 >= (billsQuery.data?.total || 0)} onClick={() => setBillPage((value) => value + 1)}>下一页</Button>
            </div>
          </div>
        ) : <div className="rounded-3xl bg-white py-16 text-center text-sm text-slate-400">该柜组没有应收未收结算单</div>}

        <div className="flex items-center justify-center gap-1.5 py-2 text-[10px] text-slate-400"><Landmark className="h-3.5 w-3.5" />仅统计非 00-* 项目余额，正负号按源明细保留</div>
      </div>

      <Sheet open={Boolean(selectedBill)} onOpenChange={(open) => { if (!open) setSelectedBill(null); }}>
        <SheetContent side="bottom" className="z-[60] h-[92dvh] rounded-t-3xl bg-white p-0 text-slate-950 overflow-hidden">
          <SheetHeader className="border-b px-5 py-4 pr-12 text-left">
            <SheetTitle>金额明细</SheetTitle>
            <SheetDescription>{selectedBill?.bill_no} · {selectedBill?.supplier_name || selectedBill?.supplier_id}</SheetDescription>
          </SheetHeader>

          <div className="h-[calc(92dvh-5.5rem)] overflow-y-auto px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
            {detailQuery.isLoading ? <div className="flex justify-center py-16 text-sm text-slate-500"><Loader2 className="mr-2 h-5 w-5 animate-spin" />正在加载组成明细…</div> : detailQuery.error ? <div className="mt-5 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">{errorText(detailQuery.error)}</div> : detailQuery.data ? (
              <div className="mt-5 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-2xl bg-rose-50 p-3"><div className="text-[10px] text-rose-600">应收未收合计</div><div className="mt-1 font-mono text-lg font-bold text-rose-700">{money(detailQuery.data.totals.receivable_amount)}</div></div>
                  <div className="rounded-2xl bg-sky-50 p-3"><div className="text-[10px] text-sky-700">销售返款（不计应收）</div><div className="mt-1 font-mono text-lg font-bold text-sky-800">{money(detailQuery.data.totals.sales_refund_amount)}</div></div>
                  <div className="col-span-2 flex items-center justify-between gap-3 rounded-2xl bg-violet-50 p-3"><div><div className="text-[10px] text-violet-700">供应商实际应收金额</div><div className="mt-0.5 text-[9px] text-violet-500">应收未收 − 销售返款</div></div><div className="font-mono text-lg font-bold text-violet-800">{money(supplierActualReceivableAmount(detailQuery.data.totals.receivable_amount, detailQuery.data.totals.sales_refund_amount))}</div></div>
                </div>
                <div className="flex items-center justify-between px-1"><div className="text-xs text-slate-500">{showAllDetails ? `全部 ${detailItems.length} 条` : `非零 ${visibleDetails.length} 条`}</div><Button variant="ghost" size="sm" onClick={() => setShowAllDetails((value) => !value)}>{showAllDetails ? "只看非零" : "显示全部"}</Button></div>
                {visibleDetails.map((item) => (
                  <Card key={item.row_no} className="rounded-2xl shadow-none">
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{item.item_name}</div>
                          <div className="mt-1 text-[10px] text-slate-400">{shortDate(item.period_from)} 至 {shortDate(item.period_to)}</div>
                        </div>
                        <div className={`shrink-0 font-mono text-sm font-bold ${item.balance_amount < 0 ? "text-emerald-700" : item.balance_amount > 0 ? "text-rose-600" : "text-slate-400"}`}>{money(item.balance_amount)}</div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </main>
  );
}
