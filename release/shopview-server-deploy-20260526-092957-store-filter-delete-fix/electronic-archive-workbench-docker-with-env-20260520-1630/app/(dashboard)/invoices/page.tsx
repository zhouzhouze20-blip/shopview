import {
  Archive,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Filter,
  Search,
} from "lucide-react"
import { StatCard } from "@/components/stat-card"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getInvoices, getInvoiceSummary } from "@/lib/etl-data"
import { TablePagination } from "@/components/table-pagination"
import { InvoiceRowMenu, InvoiceStatusBadge } from "@/components/invoice-actions"
import { QuerySelect } from "@/components/query-select"

export default async function InvoicesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; supplierName?: string; status?: string }>
}) {
  const params = await searchParams
  const [invoicePage, summary] = await Promise.all([
    getInvoices(params.page, undefined, params.supplierName, params.status),
    getInvoiceSummary(params.supplierName),
  ])
  const invoices = invoicePage.items
  const stats = [
    {
      title: "待确认",
      value: summary.matched,
      icon: <FileText className="h-5 w-5" />,
      variant: "warning" as const,
    },
    {
      title: "金额不一致",
      value: summary.amountMismatch,
      icon: <AlertTriangle className="h-5 w-5" />,
      variant: "error" as const,
    },
    {
      title: "未匹配",
      value: summary.unmatched,
      icon: <CheckCircle2 className="h-5 w-5" />,
      variant: "default" as const,
    },
    {
      title: "已确认",
      value: summary.archived,
      icon: <Archive className="h-5 w-5" />,
      variant: "success" as const,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">发票池</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          数据来自 ETLKP.INVOICE_HEADER、INVOICE_MATCH_RECORD_ZJB 和 PAYMENT_BILL。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            variant={stat.variant}
          />
        ))}
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base font-medium">发票列表</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <form className="flex items-center gap-2" action="/invoices">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="supplierName"
                    placeholder="销方/买方/发票号/单据号"
                    defaultValue={params.supplierName ?? ""}
                    className="w-64 pl-9"
                  />
                </div>
                <Button type="submit" variant="outline">
                  筛选
                </Button>
              </form>
              <QuerySelect
                name="status"
                value={params.status ?? "all"}
                placeholder="匹配状态"
                className="w-32"
                options={[
                  { value: "all", label: "全部状态" },
                  { value: "matched", label: "待确认" },
                  { value: "amount_mismatch", label: "金额不一致" },
                  { value: "unmatched", label: "未匹配" },
                  { value: "archived", label: "已确认" },
                ]}
              />
              <Button asChild variant="outline" size="icon">
                <a href="/invoices" aria-label="清空筛选">
                <Filter className="h-4 w-4" />
                </a>
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>发票号码</TableHead>
                  <TableHead>销方名称</TableHead>
                  <TableHead>购方名称</TableHead>
                  <TableHead>开票日期</TableHead>
                  <TableHead className="text-right">发票金额</TableHead>
                  <TableHead className="text-right">税额</TableHead>
                  <TableHead className="text-right">价税合计</TableHead>
                  <TableHead>匹配状态</TableHead>
                  <TableHead>匹配付款单</TableHead>
                  <TableHead>来源系统</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-medium">
                      {invoice.invoiceNo}
                    </TableCell>
                    <TableCell className="max-w-40 truncate" title={invoice.sellerName}>
                      {invoice.sellerName}
                    </TableCell>
                    <TableCell className="max-w-40 truncate" title={invoice.buyerName}>
                      {invoice.buyerName}
                    </TableCell>
                    <TableCell>{invoice.invoiceDate}</TableCell>
                    <TableCell className="text-right">
                      ¥{invoice.amount.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      ¥{invoice.taxAmount.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{invoice.totalAmount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <InvoiceStatusBadge status={invoice.matchStatus} />
                    </TableCell>
                    <TableCell className="max-w-44 truncate text-primary" title={invoice.matchedDoc}>
                      {invoice.matchedDoc}
                    </TableCell>
                    <TableCell>{invoice.source}</TableCell>
                    <TableCell className="text-right">
                      <InvoiceRowMenu invoice={invoice} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <TablePagination
            page={invoicePage.page}
            totalPages={invoicePage.totalPages}
            total={invoicePage.total}
            pageSize={invoicePage.pageSize}
            basePath="/invoices"
            query={{ supplierName: params.supplierName, status: params.status }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
