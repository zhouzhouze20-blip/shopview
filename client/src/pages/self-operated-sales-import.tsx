import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet, Upload, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { apiGet, apiRequest } from "@/lib/api";
import { MobileSelfOperatedSales } from "@/components/mobile-self-operated-sales";

type Result = { status: string; sha256?: string; import_id?: number; row_count: number; return_rows: number;
  sales: string; venue_fee: string; expected_receipt: string; supplier_cost: string; gross_profit: string };
type History = { id: number; source_file: string; start_date: string; end_date: string; imported_at: string;
  imported_by: string | null; row_count: number; sales: number };
const amount = (value: string | number) => Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
function errorMessage(error: unknown) {
  const message = error instanceof Error ? error.message : "上传失败，请重试";
  const index = message.indexOf("{");
  if (index >= 0) { try { const detail = JSON.parse(message.slice(index)).detail; if (typeof detail === "string") return detail; } catch {} }
  return message;
}

export default function SelfOperatedSalesImportPage() {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(today);
  const [file, setFile] = useState<File | null>(null);
  const [complete, setComplete] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const client = useQueryClient();
  const history = useQuery({ queryKey: ["self-operated-imports"], queryFn: () => apiGet<History[]>("/api/self-operated-sales/imports") });
  const reset = () => { setResult(null); setError(""); setComplete(false); };
  async function submit(commit: boolean) {
    if (!file || !start || !end || start > end) { setError("请选择Excel文件及有效的查询日期范围。"); return; }
    if (!complete) { setError("请确认上传的是指定日期的完整报表。"); return; }
    setBusy(true); setError("");
    try {
      const form = new FormData();
      form.append("file", file); form.append("start_date", start); form.append("end_date", end);
      form.append("commit", String(commit)); form.append("expected_sha256", result?.sha256 || "");
      const subject = localStorage.getItem("shopview_admin_view_user_id");
      const response = await apiRequest("/api/self-operated-sales/upload", { method: "POST", body: form,
        headers: subject ? { "X-ShopView-Admin-View-User-Id": subject } : {} });
      setResult(await response.json());
      if (commit) await Promise.all([
        client.invalidateQueries({ queryKey: ["self-operated-imports"] }),
        client.invalidateQueries({ queryKey: ["self-operated-sales"] }),
        client.invalidateQueries({ queryKey: ["self-operated-details"] }),
      ]);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
    <div><h1 className="flex items-center gap-2 text-xl font-semibold"><FileSpreadsheet className="h-6 w-6 text-teal-700" />自营销售导入</h1>
      <p className="mt-2 text-sm text-slate-500">自营公司 / 自营服装 · 上传丽晶“店铺零售报表”，导入后供手机销售看板查看。</p></div>
    <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
      <section className="space-y-4 rounded-2xl border bg-white p-5">
        <h2 className="font-semibold">上传服装销售报表</h2>
        <p className="text-sm leading-6 text-slate-600">日期必须与源系统导出时的“单据日期”一致。同一日期再次上传会更新该区间，不会重复累计；区间外数据保留。</p>
        <div className="grid grid-cols-2 gap-3"><div><Label htmlFor="self-sales-start">查询开始日期</Label><Input id="self-sales-start" type="date" value={start} disabled={busy} onChange={e => { setStart(e.target.value); reset(); }} /></div>
          <div><Label htmlFor="self-sales-end">查询结束日期</Label><Input id="self-sales-end" type="date" value={end} disabled={busy} onChange={e => { setEnd(e.target.value); reset(); }} /></div></div>
        <div className="space-y-2"><Label htmlFor="self-sales-file">Excel文件（.xlsx，最多15MB）</Label><Input id="self-sales-file" type="file" accept=".xlsx" disabled={busy} onChange={e => { setFile(e.target.files?.[0] || null); reset(); }} /></div>
        <label className="flex items-start gap-2 text-sm leading-6"><Checkbox className="mt-1" checked={complete} disabled={busy} onCheckedChange={value => setComplete(value === true)} /><span>这是所选日期内 PBCZ6001 店铺的完整报表，包含销售和退货，未按商品、会员或销售方式额外筛选。</span></label>
        {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
        <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy || !file || !complete} onClick={() => void submit(false)}>{busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileSpreadsheet className="mr-2 h-4 w-4" />}校验并预览</Button>
          <Button disabled={busy || !complete || result?.status !== "preview"} onClick={() => void submit(true)}><Upload className="mr-2 h-4 w-4" />确认导入</Button></div>
        {result && <div className="space-y-3 rounded-xl bg-slate-50 p-4">
          <p className="font-medium text-teal-800" role="status">{result.status === "imported" ? `导入成功 · 批次 ${result.import_id}` : "校验通过，尚未写入数据库"}</p>
          <p className="text-xs text-slate-500">{result.row_count} 条明细，含 {result.return_rows} 条退货</p>
          <dl className="grid grid-cols-2 gap-3 text-sm">{([ ["计收额", result.sales], ["场地扣款15%", result.venue_fee], ["预计回款", result.expected_receipt], ["甲方结算成本", result.supplier_cost], ["毛利（扣场地后）", result.gross_profit] ]).map(([label, value]) => <div key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 font-semibold">¥{amount(value)}</dd></div>)}</dl>
        </div>}
        <p className="text-xs leading-5 text-slate-500">销售取计收额，甲方成本按计收折扣对应50% / 52% / 55%计算，场地扣款15%。未扣人工等其他费用；餐饮数据暂未接入。</p>
      </section>
      <section className="space-y-3"><h2 className="font-semibold">手机端呈现</h2><p className="text-xs text-slate-500">点击自营公司可查看板块和销售明细，使用上方日期范围。</p><MobileSelfOperatedSales startDate={start} endDate={end} onUseImportedDates={(from, to) => { setStart(from); setEnd(to); reset(); }} /></section>
    </div>
    <section className="rounded-2xl border bg-white p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">最近30次导入</h2><Button variant="ghost" size="sm" onClick={() => void history.refetch()}><RefreshCw className="mr-2 h-4 w-4" />刷新</Button></div>
      {history.isError ? <p role="alert" className="text-sm text-rose-700">{errorMessage(history.error)}</p> : history.isPending ? <p className="text-sm text-slate-500">正在读取导入记录…</p> : <div className="overflow-x-auto"><table className="w-full whitespace-nowrap text-left text-sm"><thead className="border-b text-xs text-slate-500"><tr>{["批次", "文件", "日期范围", "明细数", "计收额", "导入人", "导入时间"].map(item => <th className="px-3 py-2" key={item}>{item}</th>)}</tr></thead><tbody>{history.data.map(row => <tr key={row.id} className="border-b last:border-0"><td className="px-3 py-3">{row.id}</td><td className="max-w-64 truncate px-3" title={row.source_file}>{row.source_file}</td><td className="px-3">{row.start_date} 至 {row.end_date}</td><td className="px-3">{row.row_count}</td><td className="px-3">{amount(row.sales)}</td><td className="px-3">{row.imported_by || "命令行导入"}</td><td className="px-3">{new Date(row.imported_at).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false })}</td></tr>)}</tbody></table>{!history.data.length && <p className="py-5 text-sm text-slate-500">暂无导入记录。</p>}</div>}
    </section>
  </div>;
}
