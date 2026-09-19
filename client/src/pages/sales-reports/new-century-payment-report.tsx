import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Search } from "lucide-react";
import { apiGet, apiRequest } from "@/lib/api";
import { scheduleObjectUrlRevoke } from "@/lib/od0002-report";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const codes = ["0328", "0329", "0330", "0331", "0332", "0333"];
const columns = [
  ["rq", "日期"], ["mkt", "门店"], ["bmname", "部门"], ["gz", "柜组编码"],
  ["gzname", "柜组名称"], ["paycode", "支付编码"], ["pname", "支付名称"],
  ["money", "支付金额"], ["bl", "折算收入比例"], ["ml", "毛利"], ["xssr", "销售收入"],
] as const;
type Row = Record<(typeof columns)[number][0], string | number | null>;
type Report = { rows: Row[]; totals: Record<"money" | "ml" | "xssr", number>; note: string; scope_description: string };
const amounts = new Set(["money", "ml", "xssr"]);
function format(key: string, value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (amounts.has(key) || key === "bl") return Number(value).toLocaleString("zh-CN", { minimumFractionDigits: key === "bl" ? 4 : 2, maximumFractionDigits: key === "money" ? 2 : 4 });
  return String(value);
}

export default function NewCenturyPaymentReportPage() {
  const [start, setStart] = useState("2026-07-29");
  const [end, setEnd] = useState("2026-08-28");
  const [department, setDepartment] = useState("");
  const [group, setGroup] = useState("");
  const [selected, setSelected] = useState(codes);
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const query = useQuery<Report>({ queryKey: ["new-century-payment-report", submitted], enabled: !!submitted,
    queryFn: () => apiGet(`/api/sales/reports/new-century-payments?${submitted}`) });
  const report = query.data;
  const invalid = !start || !end || start > end || !selected.length || (Date.parse(end) - Date.parse(start)) / 86400000 > 365;
  function submit() {
    const p = new URLSearchParams({ start_date: start, end_date: end });
    if (department.trim()) p.set("department_id", department.trim());
    if (group.trim()) p.set("group_code", group.trim());
    selected.forEach(code => p.append("pay_codes", code));
    setPage(0); setExportError("");
    if (submitted === p.toString()) void query.refetch();
    else setSubmitted(p.toString());
  }
  async function download() {
    setExporting(true); setExportError("");
    let url: string | undefined;
    let a: HTMLAnchorElement | undefined;
    try {
      const response = await apiRequest(`/api/sales/reports/new-century-payments/export?${submitted}`);
      url = URL.createObjectURL(await response.blob());
      a = document.createElement("a"); a.href = url;
      const p = new URLSearchParams(submitted);
      a.download = `新世纪支付方式销售毛利_${p.get("start_date")}_${p.get("end_date")}.xlsx`;
      document.body.appendChild(a); a.click();
    } catch (e) { setExportError(e instanceof Error ? e.message : "导出失败"); }
    finally { a?.remove(); if (url) scheduleObjectUrlRevoke(url); setExporting(false); }
  }
  return <div className="space-y-5 p-4 md:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h1 className="text-2xl font-semibold">新世纪支付方式销售毛利报表</h1><p className="mt-1 text-sm text-muted-foreground">常州新世纪商城 · 603 · 金额单位：元</p></div>
      <Button variant="outline" disabled={!report || exporting || query.isFetching} onClick={download}><Download className="mr-2 h-4 w-4" />{exporting ? "正在导出…" : "导出 Excel"}</Button>
    </div>
    <Card><CardContent className="space-y-4 pt-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div><Label htmlFor="payment-start">开始日期</Label><Input id="payment-start" type="date" value={start} onChange={e => setStart(e.target.value)} /></div>
        <div><Label htmlFor="payment-end">结束日期（包含当天）</Label><Input id="payment-end" type="date" value={end} onChange={e => setEnd(e.target.value)} /></div>
        <div><Label htmlFor="payment-dept">部门编码</Label><Input id="payment-dept" placeholder="全部部门" value={department} onChange={e => setDepartment(e.target.value)} /></div>
        <div><Label htmlFor="payment-group">柜组编码</Label><Input id="payment-group" placeholder="全部柜组" value={group} onChange={e => setGroup(e.target.value)} /></div>
        <Button className="self-end" disabled={invalid || query.isFetching} onClick={submit}><Search className="mr-2 h-4 w-4" />{query.isFetching ? "查询中…" : "查询"}</Button>
      </div>
      <fieldset className="flex flex-wrap gap-4"><legend className="mb-2 text-sm font-medium">支付方式</legend>{codes.map(code => <label key={code} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={selected.includes(code)} onChange={e => setSelected(old => e.target.checked ? [...old, code] : old.filter(x => x !== code))} />{code}</label>)}</fieldset>
      {invalid && <p className="text-sm text-red-600">请选择1至366天的有效日期范围，并至少选择一种支付方式。</p>}
    </CardContent></Card>
    {query.isError && <p role="alert" className="text-red-600">{query.error instanceof Error ? query.error.message : "查询失败"}</p>}
    {exportError && <p role="alert" className="text-red-600">{exportError}</p>}
    {!submitted && <p className="py-10 text-center text-muted-foreground">已填入原报表日期，点击查询加载数据。</p>}
    {report && <>
      <p className="text-sm text-muted-foreground">查询结果：{new URLSearchParams(submitted).get("start_date")} 至 {new URLSearchParams(submitted).get("end_date")} · 支付方式 {new URLSearchParams(submitted).getAll("pay_codes").join("、")}</p>
      <div className="grid gap-3 sm:grid-cols-3">{([['money', '支付金额'], ['ml', '毛利'], ['xssr', '销售收入']] as const).map(([key, label]) => <Card key={key}><CardContent className="pt-4"><div className="text-sm text-muted-foreground">{label}合计</div><div className="mt-2 text-2xl font-semibold tabular-nums">{format(key, report.totals[key])}</div></CardContent></Card>)}</div>
      <p className="text-sm text-muted-foreground">{report.note}</p>
      {report.scope_description && <p className="text-xs text-muted-foreground">数据范围：{report.scope_description}</p>}
      <Card><Table><TableHeader><TableRow>{columns.map(([key, label]) => <TableHead key={key} className={`whitespace-nowrap ${amounts.has(key) || key === 'bl' ? 'text-right' : ''}`}>{label}</TableHead>)}</TableRow></TableHeader>
        <TableBody>{report.rows.slice(page * 100, (page + 1) * 100).map((row, index) => <TableRow key={page * 100 + index}>{columns.map(([key]) => <TableCell key={key} className={`whitespace-nowrap ${amounts.has(key) || key === 'bl' ? 'text-right tabular-nums' : ''}`}>{format(key, row[key])}</TableCell>)}</TableRow>)}
          {!report.rows.length && <TableRow><TableCell colSpan={11} className="py-10 text-center text-muted-foreground">当前条件下暂无数据</TableCell></TableRow>}
        </TableBody></Table>
        <div className="flex items-center justify-between gap-2 border-t p-3 text-sm"><span>共 {report.rows.length} 行 · 合计与导出包含全部查询结果</span><div className="flex items-center gap-3"><Button variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button><span>{page + 1} / {Math.max(1, Math.ceil(report.rows.length / 100))}</span><Button variant="outline" disabled={(page + 1) * 100 >= report.rows.length} onClick={() => setPage(page + 1)}>下一页</Button></div></div>
      </Card>
    </>}
  </div>;
}
