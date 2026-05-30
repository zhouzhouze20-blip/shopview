"use client"

import Link from "next/link"
import { useMemo, useState, useTransition } from "react"
import { useRouter } from "next/navigation"
import { Eye, Link2, MoreHorizontal } from "lucide-react"
import { toast } from "sonner"
import type { InvoiceListItem, PaymentBillItem } from "@/lib/etl-data"
import { createManualInvoiceAssociation } from "@/lib/actions"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

function money(value: number) {
  return `￥${value.toLocaleString(undefined, {
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

function PaymentBillDetail({ document }: { document: PaymentBillItem }) {
  return (
    <DialogContent className="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>业务单据详情</DialogTitle>
        <DialogDescription>{document.docNo}</DialogDescription>
      </DialogHeader>
      <div className="grid gap-3 text-sm sm:grid-cols-2">
        <DetailItem label="来源系统" value={document.source} />
        <DetailItem label="单据类型" value={document.docType} />
        <DetailItem label="供应商/客户" value={document.partner} />
        <DetailItem label="门店" value={document.storeName} />
        <DetailItem label="业务日期" value={document.businessDate} />
        <DetailItem label="单据金额" value={money(document.amount)} />
        <DetailItem label="已匹配金额" value={money(document.matchedAmount)} />
        <DetailItem label="剩余金额" value={money(document.remainingAmount)} />
        <DetailItem label="已关联发票" value={`${document.linkedInvoices} 张`} />
        <DetailItem label="已关联流水" value={`${document.linkedTransactions} 笔`} />
        <DetailItem
          label="状态"
          value={
            document.status === "completed"
              ? "已关联"
              : document.status === "partial"
                ? "部分关联"
                : "待关联"
          }
        />
      </div>
    </DialogContent>
  )
}

function associationHref(document: PaymentBillItem) {
  const params = new URLSearchParams()
  if (document.partner && document.partner !== "-") {
    params.set("supplierName", document.partner)
  }
  return `/invoices/amount-mismatch${params.size ? `?${params.toString()}` : ""}`
}

function sameText(left: string, right: string) {
  return left.trim() === right.trim()
}

function cleanText(value: string | undefined) {
  const trimmed = value?.trim()
  return trimmed && trimmed !== "-" ? trimmed : ""
}

function sameTaxOrName(
  leftTaxNo: string | undefined,
  rightTaxNo: string | undefined,
  leftName: string,
  rightName: string
) {
  const normalizedLeftTaxNo = cleanText(leftTaxNo)
  const normalizedRightTaxNo = cleanText(rightTaxNo)
  if (normalizedLeftTaxNo && normalizedRightTaxNo) {
    return sameText(normalizedLeftTaxNo, normalizedRightTaxNo)
  }

  return sameText(leftName, rightName)
}

function PaymentBillAssociationDialog({
  document,
  invoices,
}: {
  document: PaymentBillItem
  invoices: InvoiceListItem[]
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [loadedInvoices, setLoadedInvoices] = useState<InvoiceListItem[] | undefined>()
  const [loadError, setLoadError] = useState<string | undefined>()
  const [isLoadingInvoices, setIsLoadingInvoices] = useState(false)
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<string[]>([])
  const [isPending, startTransition] = useTransition()
  const sourceInvoices = loadedInvoices ?? invoices

  const candidateInvoices = useMemo(
    () =>
      sourceInvoices.filter(
        (invoice) =>
          sameText(invoice.sellerName, document.partner) &&
          sameTaxOrName(
            invoice.buyerTaxNo,
            document.storeTaxNo,
            invoice.buyerName,
            document.storeName
          ) &&
          (invoice.isRedInvoice
            ? document.matchedAmount > 0
            : document.remainingAmount > 0)
      ),
    [document, sourceInvoices]
  )
  const invoiceMap = useMemo(
    () => new Map(candidateInvoices.map((invoice) => [invoice.id, invoice])),
    [candidateInvoices]
  )
  const selectedInvoices = selectedInvoiceIds
    .map((id) => invoiceMap.get(id))
    .filter((invoice): invoice is InvoiceListItem => Boolean(invoice))
  const invoiceTotal = selectedInvoices.reduce(
    (sum, invoice) => sum + invoice.totalAmount,
    0
  )
  const hasRedInvoice = selectedInvoices.some((invoice) => invoice.isRedInvoice)
  const capacity = hasRedInvoice ? document.matchedAmount : document.remainingAmount
  const canSubmit =
    selectedInvoices.length > 0 &&
    Math.abs(invoiceTotal) <= capacity + 0.01 &&
    (!hasRedInvoice || selectedInvoices.every((invoice) => invoice.isRedInvoice))

  const toggleInvoice = (invoiceId: string) => {
    setSelectedInvoiceIds((current) =>
      current.includes(invoiceId)
        ? current.filter((id) => id !== invoiceId)
        : [...current, invoiceId]
    )
  }

  const loadInvoices = async () => {
    if (loadedInvoices || isLoadingInvoices) return

    setIsLoadingInvoices(true)
    setLoadError(undefined)
    try {
      const params = new URLSearchParams()
      if (document.partner && document.partner !== "-") {
        params.set("supplierName", document.partner)
      }
      params.set("pageSize", "5000")
      const response = await fetch(
        `/api/manual-association-invoices?${params.toString()}`,
        { cache: "no-store" }
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = (await response.json()) as { invoices?: InvoiceListItem[] }
      setLoadedInvoices(data.invoices ?? [])
    } catch {
      setLoadError("候选发票加载失败")
      setLoadedInvoices([])
    } finally {
      setIsLoadingInvoices(false)
    }
  }

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen) {
      void loadInvoices()
    }
  }

  const submitAssociation = () => {
    if (!canSubmit) return

    const pairs = selectedInvoices.map((invoice) => ({
      invoiceId: invoice.id,
      billId: document.id,
      billNo: document.docNo,
      amount: invoice.totalAmount,
    }))
    const formData = new FormData()
    formData.set("pairs", JSON.stringify(pairs))

    startTransition(async () => {
      const result = await createManualInvoiceAssociation(formData)
      toast[result.ok ? "success" : "error"](result.message)
      if (result.ok) {
        setSelectedInvoiceIds([])
        setOpen(false)
        router.refresh()
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Link2 className="mr-1 h-3 w-3" />
          关联
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>关联发票</DialogTitle>
          <DialogDescription>
            {document.docNo} / {document.partner} / 剩余 {money(document.remainingAmount)}
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left">
                <th className="h-10 w-10 px-2" />
                <th className="h-10 px-2 font-medium">发票号码</th>
                <th className="h-10 px-2 font-medium">销方名称</th>
                <th className="h-10 px-2 font-medium">购方名称</th>
                <th className="h-10 px-2 font-medium">开票日期</th>
                <th className="h-10 px-2 text-right font-medium">价税合计</th>
              </tr>
            </thead>
            <tbody>
              {isLoadingInvoices ? (
                <tr>
                  <td colSpan={6} className="px-2 py-8 text-center text-muted-foreground">
                    正在加载候选发票
                  </td>
                </tr>
              ) : loadError ? (
                <tr>
                  <td colSpan={6} className="px-2 py-8 text-center text-destructive">
                    {loadError}
                  </td>
                </tr>
              ) : candidateInvoices.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-2 py-8 text-center text-muted-foreground">
                    没有符合当前付款单的可关联发票
                  </td>
                </tr>
              ) : (
                candidateInvoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-border">
                    <td className="px-2 py-3">
                      <Checkbox
                        checked={selectedInvoiceIds.includes(invoice.id)}
                        onCheckedChange={() => toggleInvoice(invoice.id)}
                      />
                    </td>
                    <td className="px-2 py-3 font-medium">{invoice.invoiceNo}</td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.sellerName}>{invoice.sellerName}</td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.buyerName}>{invoice.buyerName}</td>
                    <td className="px-2 py-3">{invoice.invoiceDate}</td>
                    <td className="px-2 py-3 text-right font-medium">
                      {money(invoice.totalAmount)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="rounded-md bg-muted p-3 text-sm">
          已选 {selectedInvoices.length} 张，合计 {money(invoiceTotal)}，当前单据可用{" "}
          {money(capacity)}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            取消
          </Button>
          <Button disabled={!canSubmit || isPending} onClick={submitAssociation}>
            确认关联
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function PaymentBillRowMenu({ document }: { document: PaymentBillItem }) {
  return (
    <Dialog>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DialogTrigger asChild>
            <DropdownMenuItem onSelect={(event) => event.preventDefault()}>
              <Eye className="mr-2 h-4 w-4" />
              查看详情
            </DropdownMenuItem>
          </DialogTrigger>
          <DropdownMenuItem asChild>
            <Link href={associationHref(document)}>
              <Link2 className="mr-2 h-4 w-4" />
              关联发票
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <PaymentBillDetail document={document} />
    </Dialog>
  )
}

export function PaymentBillInlineActions({
  document,
  associationInvoices = [],
}: {
  document: PaymentBillItem
  associationInvoices?: InvoiceListItem[]
}) {
  return (
    <div className="flex justify-end gap-2">
      <Dialog>
        <DialogTrigger asChild>
          <Button size="sm" variant="outline">
            <Eye className="mr-1 h-3 w-3" />
            详情
          </Button>
        </DialogTrigger>
        <PaymentBillDetail document={document} />
      </Dialog>
      <PaymentBillAssociationDialog
        document={document}
        invoices={associationInvoices}
      />
    </div>
  )
}
