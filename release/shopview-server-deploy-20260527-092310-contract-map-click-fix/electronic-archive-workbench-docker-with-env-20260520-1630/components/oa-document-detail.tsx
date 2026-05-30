"use client"

import { useState, useTransition } from "react"
import { Eye, Loader2 } from "lucide-react"
import type { OaBillItem, OaLinkedInvoiceItem } from "@/lib/etl-data"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  completed: { label: "已完成", variant: "default" },
  partial: { label: "部分关联", variant: "secondary" },
  pending: { label: "待关联", variant: "outline" },
}

function money(value: number) {
  return `¥${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 break-words font-medium">{value}</div>
    </div>
  )
}

export function OaDocumentDetail({ doc }: { doc: OaBillItem }) {
  const [open, setOpen] = useState(false)
  const [invoices, setInvoices] = useState<OaLinkedInvoiceItem[]>([])
  const [error, setError] = useState<string | undefined>()
  const [isPending, startTransition] = useTransition()

  const loadInvoices = () => {
    if (invoices.length > 0 || isPending) return

    startTransition(async () => {
      setError(undefined)
      try {
        const response = await fetch(
          `/api/oa-bills/${encodeURIComponent(doc.id)}/invoices`,
          { cache: "no-store" }
        )
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const data = (await response.json()) as {
          invoices?: OaLinkedInvoiceItem[]
        }
        setInvoices(data.invoices ?? [])
      } catch {
        setError("关联发票加载失败")
      }
    })
  }

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen) loadInvoices()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Eye className="mr-1 h-3 w-3" />
          详情
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>OA单据详情</DialogTitle>
          <DialogDescription>{doc.docNo}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <DetailItem label="门店" value={doc.storeName} />
          <DetailItem label="门店编码" value={doc.storeId} />
          <DetailItem label="单据类型" value={doc.docType} />
          <DetailItem label="申请人" value={doc.applicant} />
          <DetailItem label="部门" value={doc.department} />
          <DetailItem label="供应商/往来方" value={doc.supplierName} />
          <DetailItem label="业务日期" value={doc.businessDate} />
          <DetailItem label="单据金额" value={money(doc.amount)} />
          <DetailItem
            label="状态"
            value={(statusMap[doc.status] ?? statusMap.pending).label}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">关联发票明细</div>
            <Badge variant={doc.linkedInvoices > 0 ? "default" : "outline"}>
              {doc.linkedInvoices} 张
            </Badge>
          </div>
          <div className="overflow-x-auto rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>发票号码</TableHead>
                  <TableHead>销方名称</TableHead>
                  <TableHead>购方名称</TableHead>
                  <TableHead>开票日期</TableHead>
                  <TableHead className="text-right">价税合计</TableHead>
                  <TableHead>匹配状态</TableHead>
                  <TableHead className="text-center">匹配度</TableHead>
                  <TableHead className="text-right">差额</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isPending ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="h-20 text-center text-muted-foreground"
                    >
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        正在加载关联发票
                      </span>
                    </TableCell>
                  </TableRow>
                ) : error ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="h-20 text-center text-destructive"
                    >
                      {error}
                    </TableCell>
                  </TableRow>
                ) : invoices.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="h-20 text-center text-muted-foreground"
                    >
                      暂无关联发票
                    </TableCell>
                  </TableRow>
                ) : (
                  invoices.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell className="font-medium">{invoice.invoiceNo}</TableCell>
                      <TableCell className="max-w-56 truncate" title={invoice.sellerName}>
                        {invoice.sellerName}
                      </TableCell>
                      <TableCell className="max-w-56 truncate" title={invoice.buyerName}>
                        {invoice.buyerName}
                      </TableCell>
                      <TableCell>{invoice.invoiceDate}</TableCell>
                      <TableCell className="text-right font-medium">
                        {money(invoice.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={invoice.manualConfirmed ? "default" : "secondary"}>
                          {invoice.matchStatus}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        {invoice.matchScore > 0 ? `${invoice.matchScore}%` : "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        {money(invoice.diffAmount)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
