import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiRequest } from '@/lib/api';
import { scheduleObjectUrlRevoke } from '@/lib/od0002-report';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

type Options = { stores: { store_code: string; store_name: string }[]; departments: { department_code: string; department_name: string }[]; months: string[] };
type Row = Record<string, string | number | null>;
type Report = { rows: Row[]; brands: Row[]; brand_note: string; count: number; note: string; filters: { store_code: string; department_code: string | null; financial_month: string } };
const detailColumns: readonly (readonly [string, string])[] = [
  ['department_name', '部门'], ['financial_month', '财务年月'], ['group_code', '柜组编码'],
  ['group_name', '柜组名称'], ['supplier_code', '供应商编码'], ['supplier_name', '供应商'],
  ['operation_method', '经营方式'], ['sales_quantity', '销售数量'], ['sales_revenue', '销售收入'],
  ['sales_cost_ex_tax', '不含税销售成本'], ['ending_quantity', '期末库存数量'],
  ['ending_cost_ex_tax', '期末不含税成本'], ['average_cost_ex_tax', '不含税平均库存'],
  ['turnover_days', '周转天数'], ['turnover_rate', '周转率'], ['stock_sales_ratio', '期末存销比'],
  ['stock_cover_days', '期末库存覆盖天数'], ['as_of_date', '统计截止'], ['data_status', '数据状态'],
] as const;
const brandColumns: readonly (readonly [string, string])[] = [...detailColumns.filter(([key]) => !['supplier_code', 'supplier_name', 'operation_method'].includes(key)).map(([key, title]) => [key, key === 'group_name' ? '品牌柜组' : title] as const), ['supplier_count', '供应商数'], ['exception_count', '异常明细数']];
const numeric = new Set(detailColumns.slice(7, 17).map(([key]) => String(key)));
numeric.add('supplier_count'); numeric.add('exception_count');
function format(key: string, value: Row[string]) {
  if (value == null) return '—';
  if (['supplier_count', 'exception_count'].includes(key)) return Number(value).toLocaleString('zh-CN');
  if (key === 'operation_method') return ({ '1': '经销', '2': '成本代销' } as Record<string, string>)[String(value)] || String(value);
  const precision = Math.abs(Number(value)) > 0 && Math.abs(Number(value)) < 0.01 ? 4 : 2;
  return numeric.has(key) ? Number(value).toLocaleString('zh-CN', { maximumFractionDigits: precision, minimumFractionDigits: precision }) : String(value);
}

export default function InventoryTurnoverPage() {
  const [tab, setTab] = useState('brands');
  const [selectedBrand, setSelectedBrand] = useState<Row | null>(null);
  const [store, setStore] = useState('');
  const [department, setDepartment] = useState('');
  const [month, setMonth] = useState('');
  const [submitted, setSubmitted] = useState('');
  const [page, setPage] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const options = useQuery<Options>({ queryKey: ['inventory-turnover-options', store, department],
    queryFn: () => apiGet(`/api/inventory-turnover/options?${new URLSearchParams({ store_code: store, department_code: department })}`) });
  const report = useQuery<Report>({ queryKey: ['inventory-turnover', submitted], enabled: !!submitted,
    queryFn: () => apiGet(`/api/inventory-turnover?${submitted}`) });
  function reset() { setSelectedBrand(null); setSubmitted(''); setPage(0); setExportError(''); }
  function search() {
    const params = new URLSearchParams({ store_code: store, financial_month: month });
    if (department) params.set('department_code', department);
    setSelectedBrand(null); setPage(0); setExportError('');
    if (params.toString() === submitted) void report.refetch(); else setSubmitted(params.toString());
  }
  async function download() {
    setExporting(true); setExportError(''); let url: string | undefined; let a: HTMLAnchorElement | undefined;
    try {
      const response = await apiRequest(`/api/inventory-turnover/export?${submitted}`);
      url = URL.createObjectURL(await response.blob()); a = document.createElement('a'); a.href = url;
      a.download = `商品周转财务月报_${store}_${month}.xlsx`; document.body.appendChild(a); a.click();
    } catch (error) { setExportError(error instanceof Error ? error.message : '导出失败'); }
    finally { a?.remove(); if (url) scheduleObjectUrlRevoke(url); setExporting(false); }
  }
  const rows = (tab === 'brands' ? report.data?.brands : report.data?.rows) || [];
  const columns = tab === 'brands' ? brandColumns : detailColumns;
  const supplierRows = (report.data?.rows || []).filter(row => row.group_code === selectedBrand?.group_code && row.department_code === selectedBrand?.department_code);
  const selectStyle = 'mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm';
  return <div className="space-y-5 p-4 md:p-6">
    <div className="flex items-center justify-between gap-4"><div><h1 className="text-2xl font-semibold">商品周转财务月报</h1><p className="mt-1 text-sm text-muted-foreground">经销、成本代销 · 金额单位：元 · 库存与销售成本统一不含税</p></div>
      <Button variant="outline" disabled={!submitted || !rows.length || report.isFetching || exporting} onClick={download}>{exporting ? '导出中…' : '导出 Excel'}</Button></div>
    <Card><CardContent className="grid gap-4 pt-5 sm:grid-cols-4">
      <div><Label htmlFor="turnover-store">门店</Label><select id="turnover-store" className={selectStyle} value={store} onChange={e => { setStore(e.target.value); setDepartment(''); setMonth(''); reset(); }}><option value="">请选择门店</option>{options.data?.stores.map(x => <option key={x.store_code} value={x.store_code}>{x.store_name}</option>)}</select></div>
      <div><Label htmlFor="turnover-department">部门</Label><select id="turnover-department" className={selectStyle} value={department} disabled={!store || options.isFetching} onChange={e => { setDepartment(e.target.value); setMonth(''); reset(); }}><option value="">全部授权部门</option>{options.data?.departments.filter(x => x.department_code).map(x => <option key={x.department_code} value={x.department_code}>{x.department_name}</option>)}</select></div>
      <div><Label htmlFor="turnover-month">财务年月</Label><select id="turnover-month" className={selectStyle} value={month} disabled={!store || options.isFetching} onChange={e => { setMonth(e.target.value); reset(); }}><option value="">请选择财务年月</option>{options.data?.months.map(x => <option key={x} value={x}>{x}</option>)}</select></div>
      <Button className="self-end" disabled={!store || !month || options.isFetching || report.isFetching} onClick={search}>{report.isFetching ? '查询中…' : '查询报表'}</Button>
    </CardContent></Card>
    {(options.isError || report.isError || exportError) && <p role="alert" className="text-red-600">{exportError || (options.error || report.error)?.message || '加载失败，请重试'}</p>}
    {!submitted && <p className="py-8 text-center text-muted-foreground">按门店、部门、财务年月选择后查询。仅显示已生成且有权限的数据。</p>}
    {!!submitted && report.data && <>
      <Tabs value={tab} onValueChange={value => { setTab(value); setPage(0); }}><TabsList><TabsTrigger value="brands">按品牌周转率汇总（{report.data.brands.length}）</TabsTrigger><TabsTrigger value="details">供应商明细（{report.data.count}）</TabsTrigger></TabsList></Tabs>
      <p className="text-sm text-muted-foreground">{tab === 'brands' && report.data.brand_note}{report.data.note}</p>
      {tab === 'brands' && <p className="text-sm text-muted-foreground">点击品牌名称，在侧栏查看供应商明细。异常明细仍纳入汇总，缺失金额不会被当作零。</p>}
      {rows.length > 0 && <p className="text-sm">财务期间：{String(rows[0].period_start)} 至 {String(rows[0].period_end)} · 统计截止：{String(rows[0].as_of_date)} · 更新：{new Date(String(rows[0].updated_at)).toLocaleString('zh-CN')} · {rows.filter(x => x.data_status !== '正常').length} 条需关注</p>}
      <Card><Table><TableHeader><TableRow>{columns.map(([key, label]) => <TableHead key={key} className={`whitespace-nowrap ${numeric.has(key) ? 'text-right' : ''}`}>{label}</TableHead>)}</TableRow></TableHeader>
        <TableBody>{rows.slice(page * 100, (page + 1) * 100).map(row => <TableRow key={`${row.group_code}-${row.supplier_code}-${row.operation_method}`}>
          {columns.map(([key]) => <TableCell key={key} className={`whitespace-nowrap ${numeric.has(key) ? 'text-right tabular-nums' : ''} ${key === 'data_status' && row[key] !== '正常' ? 'text-amber-700' : ''}`}>{tab === 'brands' && key === 'group_name' ? <Button variant="link" className="h-auto p-0" onClick={() => setSelectedBrand(row)}>{String(row[key] || row.group_code)}</Button> : format(key, row[key])}</TableCell>)}
        </TableRow>)}{!rows.length && <TableRow><TableCell colSpan={columns.length} className="py-10 text-center">当前条件下暂无已生成数据</TableCell></TableRow>}</TableBody></Table>
        <div className="flex items-center justify-between border-t p-3 text-sm"><span>共 {rows.length} 行 · 比率不直接求和 · 导出包含全部结果</span><div className="flex items-center gap-3"><Button variant="outline" disabled={page === 0} onClick={() => setPage(page - 1)}>上一页</Button><span>{page + 1}/{Math.max(1, Math.ceil(rows.length / 100))}</span><Button variant="outline" disabled={(page + 1) * 100 >= rows.length} onClick={() => setPage(page + 1)}>下一页</Button></div></div>
      </Card>
    </>}
    <Sheet open={!!selectedBrand} onOpenChange={open => { if (!open) setSelectedBrand(null); }}>
      <SheetContent className="w-[96vw] overflow-y-auto sm:max-w-[90vw]">
        <SheetHeader><SheetTitle>{String(selectedBrand?.group_name || '')} · 供应商明细</SheetTitle><SheetDescription>{month} · {String(selectedBrand?.department_name || '')} · 不含税成本口径 · 共 {supplierRows.length} 行</SheetDescription></SheetHeader>
        <div className="mt-6 min-w-0"><Table><TableHeader><TableRow>{detailColumns.map(([key, title]) => <TableHead key={key} className="whitespace-nowrap">{title}</TableHead>)}</TableRow></TableHeader><TableBody>{supplierRows.map(row => <TableRow key={`${row.group_code}-${row.supplier_code}-${row.operation_method}`}>{detailColumns.map(([key]) => <TableCell key={key} className={`whitespace-nowrap ${numeric.has(key) ? 'text-right tabular-nums' : ''}`}>{format(key, row[key])}</TableCell>)}</TableRow>)}</TableBody></Table></div>
      </SheetContent>
    </Sheet>
  </div>;
}
