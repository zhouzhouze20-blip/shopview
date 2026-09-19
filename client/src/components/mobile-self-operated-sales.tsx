import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { buildMobileFinancialMonthDates } from "@/lib/mobile-sales-financial-month";

type Amounts = { sales: number; venue_fee: number; expected_receipt: number; supplier_cost: number; gross_profit: number };
type Section = Amounts & {
  code: string; name: string; channel?: string; coverage: "complete" | "partial" | "not_imported";
  row_count: number; quantity: number; ticket_count: number; stores: Section[];
  imported_start: string | null; imported_end: string | null;
};
type Summary = { sections: Section[]; totals: Amounts };
type Detail = Amounts & { id: number; product: string; product_name: string; quantity: number;
  tag_price: number | string | null; original_bill: string; sale_type: string; discount: number; supplier_rate: number };
type Ticket = Amounts & { business_date: string; bill: string; quantity: number; rows: Detail[] };
const money = (value: number) => Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const available = (rows?: Section[]) => rows?.some(row => row.coverage !== "not_imported");

function Metrics({ daily, monthly, dayReady, monthReady, period, monthError, onMonthClick }: {
  daily?: Amounts; monthly?: Amounts; dayReady?: boolean; monthReady?: boolean; period: string; monthError?: boolean; onMonthClick?: () => void;
}) {
  return <div className="grid grid-cols-2 min-[360px]:grid-cols-4 gap-1.5 text-left">{[
    [period + "含券销售", dayReady && daily ? money(daily.sales) : "—"],
    [period + "毛利", dayReady && daily ? money(daily.gross_profit) : "—"],
    ["财务月含券销售", monthReady && monthly ? money(monthly.sales) : monthError ? "加载失败" : "—"],
    ["财务月毛利", monthReady && monthly ? money(monthly.gross_profit) : monthError ? "加载失败" : "—"],
  ].map(([label, value], index) => {
    const content = <><div className="text-[10px] leading-3 text-slate-400">{label}{index === 2 && onMonthClick && <ChevronRight className="inline h-3 w-3" />}</div><div className="mt-1 whitespace-nowrap text-[11px] leading-4 font-semibold tabular-nums text-slate-950">{value}</div></>;
    const className = `min-w-0 rounded-lg px-1.5 py-1.5 text-left ${label.startsWith("财务月") ? "bg-teal-50/60" : "bg-slate-50"}`;
    return index === 2 && onMonthClick ? <button type="button" key={label} className={className} aria-label="查看财务月折扣结算" onClick={onMonthClick}>{content}</button> : <div key={label} className={className}>{content}</div>;
  })}</div>;
}


type SettlementRow = { label: string; rate: number; sales: number; remittance: number; our_settlement: number; sales_share: number | null };
function DiscountSettlement({ startDate, endDate, channel }: { startDate: string; endDate: string; channel?: string }) {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  if (channel) params.set("channel", channel);
  const query = useQuery({ queryKey: ["self-operated-sales", "discount-settlement", startDate, endDate, channel],
    queryFn: () => apiGet<{ rows: SettlementRow[]; totals: SettlementRow; coverage: string }>(`/api/self-operated-sales/discount-settlement?${params}`) });
  if (query.isPending) return <p className="py-6 text-sm text-slate-500">正在加载折扣结算…</p>;
  if (query.isError) return <Button variant="ghost" onClick={() => void query.refetch()}>加载失败，点击重试</Button>;
  const data = query.data;
  if (data.coverage === "not_imported") return <p className="py-6 text-sm text-slate-500">该区间尚未导入销售数据。</p>;
  const share = (value: number | null) => value == null ? "—" : `${(Number(value) * 100).toFixed(2)}%`;
  return <div className="space-y-3 py-4">
    {data.coverage !== "complete" && <p className="text-xs text-amber-700">该区间仅部分数据已导入，以下为已导入数据汇总。</p>}
    {[...data.rows, { ...data.totals, label: "汇总", rate: null }].map(row => <article key={row.label} className={`rounded-xl border p-3 ${row.rate == null ? "border-teal-200 bg-teal-50" : "border-slate-200"}`}>
      <div className="flex flex-wrap items-center justify-between gap-1 text-sm font-semibold"><span>{row.label}</span>{row.rate != null && <span className="text-xs font-normal text-slate-500">我方结算比例 {((1 - Number(row.rate)) * 100).toFixed(0)}%</span>}</div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div className="min-w-0 text-slate-500">含券销售金额<div className="mt-1 break-all text-base font-semibold tabular-nums text-slate-950">¥{money(row.sales)}</div></div>
        <div className="min-w-0 text-slate-500">我方结算金额<div className="mt-1 break-all text-base font-semibold tabular-nums text-teal-700">¥{money(row.our_settlement)}</div></div>
      </div>
      <div className="mt-2 text-xs text-slate-500">销售占比 <span className="font-medium text-slate-900">{share(row.sales_share)}</span></div>
    </article>)}
    <p className="text-xs leading-5 text-slate-500">我方结算金额＝含券销售金额－甲方结算金额，甲方结算按明细逐笔四舍五入至分后汇总。该金额未扣场地、人工等费用，含退货冲减；销售占比＝该档含券销售金额÷总含券销售金额，总销售为零时显示“—”。</p>
  </div>;
}

function Tickets({ section, channel, startDate, endDate }: { section: string; channel: string; startDate: string; endDate: string }) {
  const [offset, setOffset] = useState(0);
  const query = useQuery({ queryKey: ["self-operated-sales", "tickets", section, channel, startDate, endDate, offset],
    queryFn: () => apiGet<{ tickets: Ticket[]; total: number }>(`/api/self-operated-sales/tickets?${new URLSearchParams({
      section, channel, start_date: startDate, end_date: endDate, offset: String(offset), limit: "20",
    })}`) });
  if (query.isPending) return <p className="p-3 text-xs text-slate-500">正在加载小票…</p>;
  if (query.isError) return <Button variant="ghost" onClick={() => void query.refetch()}>小票加载失败，点击重试</Button>;
  return <div className="space-y-3">
    <p className="text-xs text-slate-500">{startDate} 至 {endDate} · 共 {query.data.total} 张小票</p>
    {query.data.tickets.map(ticket => <article key={`${ticket.business_date}-${ticket.bill}`} className="overflow-hidden rounded-xl border border-slate-200">
      <div className="bg-slate-50 p-3"><div className="break-all text-xs font-semibold">{ticket.bill}</div><div className="mt-1 text-[10px] text-slate-500">{ticket.business_date} · 净销售 {Number(ticket.quantity)} 件</div>
        <div className="mt-2 flex justify-between text-xs"><span>含券销售 ¥{money(ticket.sales)}</span><span className="text-teal-700">毛利 ¥{money(ticket.gross_profit)}</span></div></div>
      <div className="divide-y divide-slate-100">{ticket.rows.map(row => <div key={row.id} className="p-3 text-xs">
        <div className="font-medium">{row.product_name || row.product} × {Number(row.quantity)}</div>
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] text-slate-600">
          <span>吊牌价 {row.tag_price == null || row.tag_price === "" || !Number.isFinite(Number(row.tag_price)) ? "—" : `¥${money(Number(row.tag_price))}`}</span>
          <span>折扣 {(Number(row.discount) * 100).toFixed(2)}%</span>
          <span>含券销售 ¥{money(row.sales)}</span>
          <span className="text-teal-700">毛利 ¥{money(row.gross_profit)}</span>
        </div>
      </div>)}</div>
    </article>)}
    {!query.data.tickets.length && <p className="text-xs text-slate-500">所选日期没有已导入的小票。</p>}
    <div className="flex justify-between"><Button variant="ghost" disabled={!offset} onClick={() => setOffset(offset - 20)}>上一页</Button><Button variant="ghost" disabled={offset + 20 >= query.data.total} onClick={() => setOffset(offset + 20)}>下一页</Button></div>
  </div>;
}

export function MobileSelfOperatedSales({ startDate, endDate, onUseImportedDates, onDrilldownChange }: {
  startDate: string; endDate: string; onUseImportedDates: (start: string, end: string) => void;
  onDrilldownChange?: (active: boolean) => void;
}) {
  const [level, setLevel] = useState<"company" | "sections" | "stores" | "tickets">("company");
  const [selected, setSelected] = useState("");
  const [channel, setChannel] = useState("");
  const [settlement, setSettlement] = useState<{ name: string; channel?: string } | null>(null);
  const month = buildMobileFinancialMonthDates(endDate);
  const useSummary = (start: string, end: string) => useQuery({
    queryKey: ["self-operated-sales", "summary", start, end],
    queryFn: () => apiGet<Summary>(`/api/self-operated-sales/summary?${new URLSearchParams({ start_date: start, end_date: end })}`), staleTime: 30000,
  });
  const query = useSummary(startDate, endDate);
  const monthQuery = useSummary(month.start_date, month.end_date);
  if (query.isPending) return <div className="rounded-xl bg-white p-3 text-xs text-slate-400">正在读取自营公司数据…</div>;
  if (query.isError) return <Button variant="ghost" onClick={() => void query.refetch()}>自营公司加载失败，点击重试</Button>;
  if (!query.data.sections.length) return null;
  const section = query.data.sections.find(item => item.code === selected);
  const monthlySection = monthQuery.data?.sections.find(item => item.code === selected);
  const store = section?.stores.find(item => item.channel === channel);
  const period = startDate === endDate ? "当日" : "本期";
  const metricProps = (daily?: Section, monthly?: Section) => ({ daily, monthly,
    dayReady: !!daily && daily.coverage !== "not_imported", monthReady: !!monthly && monthly.coverage !== "not_imported", period, monthError: monthQuery.isError });
  const navigate = (next: typeof level) => {
    setLevel(next);
    onDrilldownChange?.(next !== "company");
  };
  const back = () => navigate(level === "tickets" ? "stores" : level === "stores" ? "sections" : "company");
  const missing = (item: Section) => item.coverage !== "complete" && <div className="mt-2 text-[10px] text-amber-700">
    {item.coverage === "partial" ? "所选区间仅部分数据已导入。" : "所选日期尚未导入数据。"}
    {item.imported_start && item.imported_end && <button className="ml-1 underline" onClick={() => onUseImportedDates(item.imported_start!, item.imported_end!)}>查看已导入区间</button>}
  </div>;
  return <section className="rounded-xl border border-slate-200 bg-white px-2.5 py-2 shadow-sm" aria-label="第五家店自营公司">
    {level !== "company" && <div className="mb-2 flex items-center gap-2">
      <button aria-label="返回上一级" onClick={back}><ArrowLeft className="h-4 w-4" /></button>
      <div className="flex-1"><div className="text-sm font-semibold">{level === "stores" ? `${section?.name || "自营板块"} · 单店汇总` : level === "tickets" ? `${store?.name || channel} · 小票明细` : "自营公司"}</div><div className="mt-1 text-[10px] text-slate-500">{startDate === endDate ? startDate : `${startDate} 至 ${endDate}`} · 单位：元</div></div>
    </div>}
    {level === "company" && <div className="w-full text-left">
      <button type="button" onClick={() => navigate("sections")} className="mb-1.5 flex w-full items-center justify-between gap-2"><span className="text-sm leading-4 font-semibold text-slate-950">自营公司</span><ChevronRight className="h-4 w-4 shrink-0 text-slate-300" /></button>
      <Metrics daily={query.data.totals} monthly={monthQuery.data?.totals} dayReady={available(query.data.sections)} monthReady={available(monthQuery.data?.sections)} period={period} monthError={monthQuery.isError} onMonthClick={query.data.sections.some(item => item.code === "CLOTHING") ? () => setSettlement({ name: "自营服装" }) : undefined} />
    </div>}
    {level === "sections" && <div className="space-y-3">{query.data.sections.map(item => <div key={item.code} className="rounded-xl border border-slate-100 p-3">
      <button className="w-full text-left" onClick={() => { setSelected(item.code); navigate("stores"); }}><div className="mb-2 flex justify-between text-sm font-medium">{item.name}<ChevronRight className="h-4 w-4" /></div></button><Metrics {...metricProps(item, monthQuery.data?.sections.find(row => row.code === item.code))} onMonthClick={item.code === "CLOTHING" ? () => setSettlement({ name: item.name }) : undefined} />{missing(item)}
    </div>)}</div>}
    {level === "stores" && section && <div className="space-y-3">
      {!section.stores.length && <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">{section.name}尚未接入店铺数据。</p>}
      {section.stores.map(item => <div key={item.channel} className="rounded-xl border border-slate-100 p-3"><button className="w-full text-left" onClick={() => { setChannel(item.channel!); navigate("tickets"); }}><div className="mb-2 flex justify-between text-sm font-medium">{item.name}<ChevronRight className="h-4 w-4" /></div><div className="mb-2 text-[10px] text-slate-400">{item.channel} · {item.ticket_count} 张小票</div></button><Metrics {...metricProps(item, monthlySection?.stores.find(row => row.channel === item.channel))} onMonthClick={selected === "CLOTHING" ? () => setSettlement({ name: item.name, channel: item.channel }) : undefined} />{missing(item)}</div>)}
    </div>}
    {level === "tickets" && section && store && <Tickets key={`${selected}-${channel}-${startDate}-${endDate}`} section={selected} channel={channel} startDate={startDate} endDate={endDate} />}
    {monthQuery.isError && level !== "tickets" && <button className="mt-2 text-[10px] text-amber-700 underline" onClick={() => void monthQuery.refetch()}>重试财务月数据</button>}
    <Sheet open={settlement !== null} onOpenChange={open => { if (!open) setSettlement(null); }}>
      <SheetContent side="bottom" className="max-h-[90dvh] overflow-y-auto rounded-t-2xl bg-white p-4">
        <SheetHeader className="pr-6 text-left"><SheetTitle>{settlement?.name} · 月销售折扣结算</SheetTitle><SheetDescription>{month.start_date} 至 {month.end_date} · 单位：元</SheetDescription></SheetHeader>
        {settlement && <DiscountSettlement startDate={month.start_date} endDate={month.end_date} channel={settlement.channel} />}
      </SheetContent>
    </Sheet>
  </section>;
}
