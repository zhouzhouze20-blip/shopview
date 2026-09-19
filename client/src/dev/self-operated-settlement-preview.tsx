import { createRoot } from "react-dom/client";
import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MobileSelfOperatedSales } from "@/components/mobile-self-operated-sales";
import "@/index.css";
const amounts = { sales: 100000, supplier_cost: 51600, venue_fee: 15000, expected_receipt: 85000, gross_profit: 33400 };
const store = { ...amounts, code: "CLOTHING", name: "购物中心小帆船", channel: "PBCZ6001", coverage: "complete", row_count: 100, quantity: 100, ticket_count: 80, stores: [], imported_start: "2026-08-29", imported_end: "2026-09-07" };
window.fetch = async input => {
  const url = new URL(String(input), location.origin);
  const yesterday = url.searchParams.get("end_date") === "2026-09-06";
  const scale = yesterday ? .9 : 1;
  const scaled = Object.fromEntries(Object.entries(amounts).map(([key, value]) => [key, value * scale]));
  const data = url.pathname.endsWith("discount-settlement") ? {
    coverage: "complete", rows: [
      { label: "折扣 ≥85%", rate: .5, sales: 50000 * scale, remittance: 25000 * scale, our_settlement: 25000 * scale, sales_share: .5 },
      { label: "70% ≤折扣 <85%", rate: .52, sales: 30000 * scale, remittance: 15600 * scale, our_settlement: 14400 * scale, sales_share: .3 },
      { label: "折扣 <70%", rate: .55, sales: 20000 * scale, remittance: 11000 * scale, our_settlement: 9000 * scale, sales_share: .2 },
    ], totals: { sales: 100000 * scale, remittance: 51600 * scale, our_settlement: 48400 * scale, sales_share: 1 },
  } : { totals: scaled, sections: [{ ...store, ...scaled, name: "自营服装", stores: [{ ...store, ...scaled }] }] };
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
};
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
function Preview() {
  const [endDate, setEndDate] = useState("2026-09-07");
  return <main className="mx-auto min-h-screen max-w-[420px] bg-slate-100 pb-8">
    <header className="bg-slate-950 px-5 py-6 text-white"><div className="text-xs tracking-widest text-teal-200">SHOPVIEW · 模拟数据预览</div><h1 className="mt-2 text-xl font-semibold">自营公司销售</h1></header>
    <div className="space-y-4 p-3"><div className="rounded-xl bg-amber-50 p-3 text-xs leading-5 text-amber-800">以下金额仅用于预览。点击“财务月含券销售”查看三档折扣结算，也可点击公司名称进入单店。</div>
      <div className="flex gap-2 text-sm"><button className="rounded-lg border bg-white px-3 py-2" onClick={() => setEndDate("2026-09-07")}>本日</button><button className="rounded-lg border bg-white px-3 py-2" onClick={() => setEndDate("2026-09-06")}>29日到昨天</button></div>
      <p className="text-xs text-slate-500">财务月 2026-08-29 至 {endDate}</p>
      <MobileSelfOperatedSales startDate={endDate === "2026-09-07" ? endDate : "2026-08-29"} endDate={endDate} onUseImportedDates={() => {}} />
    </div>
  </main>;
}
createRoot(document.getElementById("root")!).render(<QueryClientProvider client={client}><Preview /></QueryClientProvider>);
