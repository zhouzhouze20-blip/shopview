import { ArrowLeft, Search } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import {
  getAmountMismatchInvoices,
  getManualAssociationInvoices,
  getPaymentBills,
} from "@/lib/etl-data"
import { TablePagination } from "@/components/table-pagination"
import { ManualInvoiceAssociation } from "@/components/manual-invoice-association"
import { QuerySelect } from "@/components/query-select"

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

export default async function AmountMismatchPage({
  searchParams,
}: {
  searchParams: Promise<{
    mismatchPage?: string
    unlinkedPage?: string
    supplierName?: string
    yearMonth?: string
  }>
}) {
  const params = await searchParams
  const [mismatchPage, candidateDocumentPage, manualInvoicePage] = await Promise.all([
    getAmountMismatchInvoices(
      params.mismatchPage,
      undefined,
      params.supplierName,
      params.yearMonth
    ),
    getPaymentBills(1, 500, params.supplierName, undefined, params.yearMonth),
    getManualAssociationInvoices(
      params.unlinkedPage,
      undefined,
      params.supplierName,
      params.yearMonth
    ),
  ])
  const mismatchInvoices = mismatchPage.items
  const candidateDocuments = candidateDocumentPage.items
  const manualInvoices = manualInvoicePage.items

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
            金额不一致处理
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            展示匹配记录中 DIFF_AMOUNT 不为 0 的发票和候选付款单。
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="py-4">
          <div className="flex flex-wrap items-center gap-3">
            <form
              action="/invoices/amount-mismatch"
              className="flex flex-wrap items-center gap-3"
            >
              {params.yearMonth && params.yearMonth !== "all" ? (
                <input type="hidden" name="yearMonth" value={params.yearMonth} />
              ) : null}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  name="supplierName"
                  placeholder="按销方或买方名称筛选"
                  defaultValue={params.supplierName ?? ""}
                  className="w-72 pl-9"
                />
              </div>
              <Button type="submit" variant="outline">
                筛选
              </Button>
              <Button asChild variant="ghost">
                <Link href="/invoices/amount-mismatch">清空</Link>
              </Button>
            </form>
            <QuerySelect
              name="yearMonth"
              value={params.yearMonth ?? "all"}
              placeholder="开票年月"
              className="w-[7.5rem]"
              options={yearMonthSelectOptions()}
              clearParamsOnChange={["page", "mismatchPage", "unlinkedPage"]}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <CardTitle className="text-base font-medium">
            金额不一致记录
          </CardTitle>
          <Badge variant="secondary">{mismatchPage.total} 条记录</Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="h-10 px-2 font-medium">发票号码</th>
                  <th className="h-10 px-2 font-medium">销方名称</th>
                  <th className="h-10 px-2 font-medium">买方名称</th>
                  <th className="h-10 px-2 font-medium">匹配付款单</th>
                  <th className="h-10 px-2 text-right font-medium">价税合计</th>
                  <th className="h-10 px-2 text-center font-medium">匹配度</th>
                </tr>
              </thead>
              <tbody>
                {mismatchInvoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-border">
                    <td className="px-2 py-3 font-medium">{invoice.invoiceNo}</td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.sellerName}>
                      {invoice.sellerName}
                    </td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.buyerName}>
                      {invoice.buyerName}
                    </td>
                    <td className="px-2 py-3 text-primary">
                      {invoice.matchedDoc}
                    </td>
                    <td className="px-2 py-3 text-right font-medium">
                      ¥{invoice.totalAmount.toLocaleString()}
                    </td>
                    <td className="px-2 py-3 text-center">
                      <Badge variant="outline">{invoice.matchScore}%</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <TablePagination
            page={mismatchPage.page}
            totalPages={mismatchPage.totalPages}
            total={mismatchPage.total}
            pageSize={mismatchPage.pageSize}
            basePath="/invoices/amount-mismatch"
            pageParam="mismatchPage"
            query={{
              supplierName: params.supplierName,
              yearMonth: params.yearMonth,
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="text-base font-medium">
              发票人工关联
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              可选择金额不一致或未关联发票，重新指定付款单并写入人工确认匹配。
            </p>
          </div>
          <Badge variant="secondary">{manualInvoices.length} 张可处理</Badge>
        </CardHeader>
        <CardContent>
          <ManualInvoiceAssociation
            invoices={manualInvoices}
            paymentBills={candidateDocuments}
          />
          <TablePagination
            page={manualInvoicePage.page}
            totalPages={manualInvoicePage.totalPages}
            total={manualInvoicePage.total}
            pageSize={manualInvoicePage.pageSize}
            basePath="/invoices/amount-mismatch"
            pageParam="unlinkedPage"
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
