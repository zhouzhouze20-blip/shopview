import { ArrowLeft, CheckCircle2, FileSpreadsheet, Search } from "lucide-react"
import Link from "next/link"
import { getConfirmedMatchedInvoices } from "@/lib/etl-data"
import { InvoiceRowMenu } from "@/components/invoice-actions"
import { QuerySelect } from "@/components/query-select"
import { StatCard } from "@/components/stat-card"
import { TablePagination } from "@/components/table-pagination"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function money(value: number) {
  return `¥${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function yearMonthSelectOptions(monthsBack = 36) {
  const options: { value: string; label: string }[] = [
    { value: "all", label: "全部年月" },
  ]
  const start = new Date()
  for (let i = 0; i < monthsBack; i++) {
    const d = new Date(start.getFullYear(), start.getMonth() - i, 1)
    const y = d.getFullYear()
    const m = d.getMonth() + 1
    const value = `${y}-${String(m).padStart(2, "0")}`
    options.push({ value, label: `${y}年${m}月` })
  }
  return options
}

export default async function ConfirmedInvoiceReportPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string
    supplierName?: string
    yearMonth?: string
  }>
}) {
  const params = await searchParams
  const invoicePage = await getConfirmedMatchedInvoices(
    params.page,
    undefined,
    params.supplierName,
    params.yearMonth
  )
  const invoices = invoicePage.items
  const pageTotalAmount = invoices.reduce(
    (sum, invoice) => sum + invoice.totalAmount,
    0
  )
  const pageTaxAmount = invoices.reduce(
    (sum, invoice) => sum + invoice.taxAmount,
    0
  )
  const exportParams = new URLSearchParams()
  if (params.supplierName) exportParams.set("supplierName", params.supplierName)
  if (params.yearMonth && params.yearMonth !== "all") {
    exportParams.set("yearMonth", params.yearMonth)
  }
  const exportHref = `/api/invoices/confirmed-report/export${
    exportParams.size > 0 ? `?${exportParams.toString()}` : ""
  }`

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/invoices">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">
            匹配确认报表
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            展示已匹配、已确认且金额无差异的发票数据，年月筛选按业务单据日期统计。
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="确认记录"
          value={invoicePage.total}
          icon={<CheckCircle2 className="h-5 w-5" />}
          variant="success"
        />
        <StatCard
          title="本页税额"
          value={money(pageTaxAmount)}
          icon={<FileSpreadsheet className="h-5 w-5" />}
          variant="default"
        />
        <StatCard
          title="本页价税合计"
          value={money(pageTotalAmount)}
          icon={<FileSpreadsheet className="h-5 w-5" />}
          variant="default"
        />
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <CardTitle className="text-base font-medium">
                已确认明细
              </CardTitle>
              <Badge variant="secondary">{invoicePage.total} 条记录</Badge>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <form
                className="flex items-center gap-2"
                action="/invoices/confirmed-report"
              >
                {params.yearMonth && params.yearMonth !== "all" ? (
                  <input type="hidden" name="yearMonth" value={params.yearMonth} />
                ) : null}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="supplierName"
                    placeholder="销方/购方/发票号/单据号"
                    defaultValue={params.supplierName ?? ""}
                    className="w-64 pl-9"
                  />
                </div>
                <Button type="submit" variant="outline">
                  筛选
                </Button>
              </form>
              <QuerySelect
                name="yearMonth"
                value={params.yearMonth ?? "all"}
                placeholder="业务年月"
                className="w-[7.5rem]"
                options={yearMonthSelectOptions()}
              />
              <Button asChild variant="outline">
                <a href={exportHref}>
                  <FileSpreadsheet className="h-4 w-4" />
                  导出表格
                </a>
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>发票号码</TableHead>
                <TableHead>销方名称</TableHead>
                <TableHead>购方名称</TableHead>
                <TableHead>开票日期</TableHead>
                <TableHead>业务单据日期</TableHead>
                <TableHead className="text-right">不含税金额</TableHead>
                <TableHead className="text-right">税额</TableHead>
                <TableHead className="text-right">价税合计</TableHead>
                <TableHead>匹配单据</TableHead>
                <TableHead>单据来源</TableHead>
                <TableHead>来源系统</TableHead>
                <TableHead>确认状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell className="font-medium">
                    {invoice.invoiceNo}
                  </TableCell>
                  <TableCell className="max-w-48 truncate" title={invoice.sellerName}>
                    {invoice.sellerName}
                  </TableCell>
                  <TableCell className="max-w-48 truncate" title={invoice.buyerName}>
                    {invoice.buyerName}
                  </TableCell>
                  <TableCell>{invoice.invoiceDate}</TableCell>
                  <TableCell>{invoice.matchedDocDate}</TableCell>
                  <TableCell className="text-right">
                    {money(invoice.amount)}
                  </TableCell>
                  <TableCell className="text-right">
                    {money(invoice.taxAmount)}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {money(invoice.totalAmount)}
                  </TableCell>
                  <TableCell className="max-w-48 truncate text-primary" title={invoice.matchedDoc}>
                    {invoice.matchedDoc}
                  </TableCell>
                  <TableCell>{invoice.documentSource}</TableCell>
                  <TableCell>{invoice.source}</TableCell>
                  <TableCell>
                    <Badge variant="default">已确认</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <InvoiceRowMenu invoice={invoice} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            page={invoicePage.page}
            totalPages={invoicePage.totalPages}
            total={invoicePage.total}
            pageSize={invoicePage.pageSize}
            basePath="/invoices/confirmed-report"
            query={{
              supplierName: params.supplierName,
              yearMonth: params.yearMonth,
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
