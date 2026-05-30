import { ArrowLeft, Search } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { getMatchedInvoices } from "@/lib/etl-data"
import { TablePagination } from "@/components/table-pagination"
import { MatchedInvoicesTable } from "@/components/invoice-actions"
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

export default async function MatchedInvoicesPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string
    supplierName?: string
    yearMonth?: string
  }>
}) {
  const params = await searchParams
  const matchedPage = await getMatchedInvoices(
    params.page,
    undefined,
    params.supplierName,
    params.yearMonth
  )
  const matchedInvoices = matchedPage.items

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
            已匹配单据确认
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            确认系统自动匹配的发票与付款单，年月筛选按业务单据日期统计。
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-base font-medium">待确认列表</CardTitle>
            <Badge variant="secondary">
              {matchedPage.total} 张待确认
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <form className="flex items-center gap-2" action="/invoices/matched">
              {params.yearMonth && params.yearMonth !== "all" ? (
                <input type="hidden" name="yearMonth" value={params.yearMonth} />
              ) : null}
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
              name="yearMonth"
              value={params.yearMonth ?? "all"}
              placeholder="业务年月"
              className="w-[7.5rem]"
              options={yearMonthSelectOptions()}
            />
          </div>
        </CardHeader>
        <CardContent>
          <MatchedInvoicesTable invoices={matchedInvoices} />
          <TablePagination
            page={matchedPage.page}
            totalPages={matchedPage.totalPages}
            total={matchedPage.total}
            pageSize={matchedPage.pageSize}
            basePath="/invoices/matched"
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
