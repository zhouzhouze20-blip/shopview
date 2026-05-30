import { ArrowLeft, Filter, Search } from "lucide-react"
import Link from "next/link"
import { firstQueryString, getOaBills, type OaBillItem } from "@/lib/etl-data"
import { OaDocumentDetail } from "@/components/oa-document-detail"
import { QuerySelect } from "@/components/query-select"
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

const statusMap: Record<
  OaBillItem["status"],
  { label: string; variant: "default" | "secondary" | "outline" }
> = {
  completed: { label: "已完成", variant: "default" },
  partial: { label: "已关联待确认", variant: "secondary" },
  pending: { label: "待关联", variant: "outline" },
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

export default async function OADocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string | string[]
    keyword?: string | string[]
    docType?: string | string[]
    yearMonth?: string | string[]
  }>
}) {
  const raw = await searchParams
  const params = {
    page: firstQueryString(raw.page),
    keyword: firstQueryString(raw.keyword),
    docType: firstQueryString(raw.docType),
    yearMonth: firstQueryString(raw.yearMonth),
  }
  const oaPage = await getOaBills(
    params.page,
    undefined,
    params.keyword,
    params.docType,
    params.yearMonth
  )
  const oaDocuments = oaPage.items

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/documents">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">OA单据</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            数据来自 ETLKP.OA_BILL，发票关联统计使用 INVOICE_MATCH_RECORD_ZJB。
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <CardTitle className="text-base font-medium">OA单据列表</CardTitle>
              <Badge variant="secondary">{oaPage.total} 条记录</Badge>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <form className="flex flex-wrap items-center gap-2" action="/documents/oa">
                {params.docType && params.docType !== "all" ? (
                  <input type="hidden" name="docType" value={params.docType} />
                ) : null}
                {params.yearMonth && params.yearMonth !== "all" ? (
                  <input type="hidden" name="yearMonth" value={params.yearMonth} />
                ) : null}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    name="keyword"
                    placeholder="搜索单据号/申请人/供应商/部门"
                    defaultValue={params.keyword ?? ""}
                    className="w-72 pl-9"
                  />
                </div>
                <Button type="submit" variant="outline">
                  筛选
                </Button>
                <Button asChild variant="outline" size="icon">
                  <Link href="/documents/oa" aria-label="清空筛选">
                    <Filter className="h-4 w-4" />
                  </Link>
                </Button>
              </form>
              <QuerySelect
                name="docType"
                value={params.docType ?? "all"}
                placeholder="单据类型"
                className="w-28"
                options={[
                  { value: "all", label: "全部类型" },
                  { value: "expense", label: "费用类" },
                  { value: "payment", label: "发票入账" },
                  { value: "project", label: "项目类" },
                  { value: "maintenance", label: "维保维修" },
                  { value: "hr", label: "人事专用" },
                  { value: "asset", label: "固定资产" },
                ]}
              />
              <QuerySelect
                name="yearMonth"
                value={params.yearMonth ?? "all"}
                placeholder="业务年月"
                className="w-[7.5rem]"
                options={yearMonthSelectOptions()}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>门店</TableHead>
                  <TableHead>单据类型</TableHead>
                  <TableHead>单据编号</TableHead>
                  <TableHead>申请人</TableHead>
                  <TableHead>供应商/往来方</TableHead>
                  <TableHead>部门</TableHead>
                  <TableHead>业务日期</TableHead>
                  <TableHead className="text-right">单据金额</TableHead>
                  <TableHead className="text-center">已关联发票</TableHead>
                  <TableHead className="text-center">已关联流水</TableHead>
                  <TableHead>关联状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {oaDocuments.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={12} className="h-24 text-center text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  oaDocuments.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell className="max-w-48 truncate" title={doc.storeName}>{doc.storeName}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{doc.docType}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{doc.docNo}</TableCell>
                      <TableCell>{doc.applicant}</TableCell>
                      <TableCell className="max-w-56 truncate" title={doc.supplierName}>{doc.supplierName}</TableCell>
                      <TableCell title={doc.department}>{doc.department}</TableCell>
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
                        {doc.linkedTransactions > 0 ? (
                          <Badge variant="default">{doc.linkedTransactions}</Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusMap[doc.status].variant}>
                          {statusMap[doc.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <OaDocumentDetail doc={doc} />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          <TablePagination
            page={oaPage.page}
            totalPages={oaPage.totalPages}
            total={oaPage.total}
            pageSize={oaPage.pageSize}
            basePath="/documents/oa"
            query={{
              keyword: params.keyword,
              docType: params.docType,
              yearMonth: params.yearMonth,
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
