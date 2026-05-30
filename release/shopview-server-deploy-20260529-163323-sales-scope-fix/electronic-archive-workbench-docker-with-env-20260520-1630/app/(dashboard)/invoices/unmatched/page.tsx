import { ArrowLeft, Search } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { getUnmatchedInvoices } from "@/lib/etl-data"
import { TablePagination } from "@/components/table-pagination"
import { UnmatchedInvoicesTable } from "@/components/invoice-actions"
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

export default async function UnmatchedInvoicesPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; supplierName?: string; yearMonth?: string }>
}) {
  const params = await searchParams
  const invoicePage = await getUnmatchedInvoices(
    params.page,
    undefined,
    params.supplierName,
    params.yearMonth
  )
  const invoices = invoicePage.items

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
            未匹配发票确认
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            展示 INVOICE_HEADER 中尚未关联付款单的发票。
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4 pb-4">
          <CardTitle className="text-base font-medium">未匹配发票列表</CardTitle>
          <div className="flex items-center gap-3">
            <form className="flex items-center gap-2" action="/invoices/unmatched">
              {params.yearMonth && params.yearMonth !== "all" ? (
                <input type="hidden" name="yearMonth" value={params.yearMonth} />
              ) : null}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  name="supplierName"
                  placeholder="按销方或买方名称筛选"
                  defaultValue={params.supplierName ?? ""}
                  className="w-56 pl-9"
                />
              </div>
              <Button type="submit" variant="outline">
                筛选
              </Button>
            </form>
            <QuerySelect
              name="yearMonth"
              value={params.yearMonth ?? "all"}
              placeholder="开票年月"
              className="w-[7.5rem]"
              options={yearMonthSelectOptions()}
            />
            <Badge variant="secondary">{invoicePage.total} 张待处理</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <UnmatchedInvoicesTable invoices={invoices} />
          <TablePagination
            page={invoicePage.page}
            totalPages={invoicePage.totalPages}
            total={invoicePage.total}
            pageSize={invoicePage.pageSize}
            basePath="/invoices/unmatched"
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
