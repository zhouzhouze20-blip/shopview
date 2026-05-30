import { FileStack, Filter, Link2, Search } from "lucide-react"
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
import { StatCard } from "@/components/stat-card"
import { getPaymentBills, getPaymentBillSummary } from "@/lib/etl-data"
import { TablePagination } from "@/components/table-pagination"
import { PaymentBillRowMenu } from "@/components/document-actions"
import { QuerySelect } from "@/components/query-select"

const statusMap = {
  completed: { label: "已关联", variant: "default" as const },
  partial: { label: "部分关联", variant: "secondary" as const },
  pending: { label: "待关联", variant: "outline" as const },
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

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string
    supplierName?: string
    status?: string
    yearMonth?: string
  }>
}) {
  const params = await searchParams
  const [documentPage, summary] = await Promise.all([
    getPaymentBills(
      params.page,
      undefined,
      params.supplierName,
      params.status,
      params.yearMonth
    ),
    getPaymentBillSummary(params.supplierName, params.yearMonth),
  ])
  const documents = documentPage.items
  const stats = [
    {
      title: "付款单",
      value: summary.total,
      icon: <FileStack className="h-5 w-5" />,
      variant: "default" as const,
    },
    {
      title: "已关联",
      value: summary.completed + summary.partial,
      icon: <Link2 className="h-5 w-5" />,
      variant: "success" as const,
    },
    {
      title: "待关联",
      value: summary.pending,
      icon: <Link2 className="h-5 w-5" />,
      variant: "warning" as const,
    },
    {
      title: "总金额",
      value: `¥${summary.totalAmount.toLocaleString()}`,
      icon: <FileStack className="h-5 w-5" />,
      variant: "default" as const,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">业务单据</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          当前接入 ETLKP.PAYMENT_BILL 付款单，并统计已关联发票数量。
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
            <CardTitle className="text-base font-medium">付款单列表</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <form className="flex items-center gap-2" action="/documents">
                {params.status && params.status !== "all" ? (
                  <input type="hidden" name="status" value={params.status} />
                ) : null}
                {params.yearMonth && params.yearMonth !== "all" ? (
                  <input type="hidden" name="yearMonth" value={params.yearMonth} />
                ) : null}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="supplierName"
                    placeholder="供应商/单据号"
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
              <QuerySelect
                name="status"
                value={params.status ?? "all"}
                placeholder="关联状态"
                className="w-28"
                options={[
                  { value: "all", label: "全部状态" },
                  { value: "completed", label: "已关联" },
                  { value: "partial", label: "部分关联" },
                  { value: "pending", label: "待关联" },
                ]}
              />
              <Button asChild variant="outline" size="icon">
                <a href="/documents" aria-label="清空筛选">
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
                  <TableHead>来源系统</TableHead>
                  <TableHead>单据类型</TableHead>
                  <TableHead>单据编号</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead>业务日期</TableHead>
                  <TableHead className="text-right">单据金额</TableHead>
                  <TableHead className="text-center">已关联发票</TableHead>
                  <TableHead className="text-center">已关联流水</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <Badge variant="default">{doc.source}</Badge>
                    </TableCell>
                    <TableCell>{doc.docType}</TableCell>
                    <TableCell className="font-medium">{doc.docNo}</TableCell>
                    <TableCell className="max-w-40 truncate" title={doc.partner}>
                      {doc.partner}
                    </TableCell>
                    <TableCell>{doc.businessDate}</TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{doc.amount.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-center">
                      {doc.linkedInvoices > 0 ? (
                        <Badge variant="default">{doc.linkedInvoices}</Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <span className="text-muted-foreground">-</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusMap[doc.status].variant}>
                        {statusMap[doc.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <PaymentBillRowMenu document={doc} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <TablePagination
            page={documentPage.page}
            totalPages={documentPage.totalPages}
            total={documentPage.total}
            pageSize={documentPage.pageSize}
            basePath="/documents"
            query={{
              supplierName: params.supplierName,
              status: params.status,
              yearMonth: params.yearMonth,
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
