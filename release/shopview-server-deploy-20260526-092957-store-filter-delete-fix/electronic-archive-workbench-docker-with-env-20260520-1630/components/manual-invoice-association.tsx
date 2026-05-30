"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Check, ChevronsUpDown } from "lucide-react"
import { toast } from "sonner"
import type { InvoiceListItem, PaymentBillItem } from "@/lib/etl-data"
import { createManualInvoiceAssociation } from "@/lib/actions"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { InvoiceStatusBadge } from "@/components/invoice-actions"

type ManualInvoiceAssociationProps = {
  invoices: InvoiceListItem[]
  paymentBills: PaymentBillItem[]
}

function money(value: number) {
  return `¥${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
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

function invoiceScope(invoice: InvoiceListItem) {
  return {
    sellerName: invoice.sellerName.trim(),
    buyerName: invoice.buyerName.trim(),
    sellerTaxNo: invoice.sellerTaxNo,
    buyerTaxNo: invoice.buyerTaxNo,
    isRedInvoice: invoice.isRedInvoice,
  }
}

export function ManualInvoiceAssociation({
  invoices,
  paymentBills,
}: ManualInvoiceAssociationProps) {
  const router = useRouter()
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<string[]>([])
  const [selectedBillIds, setSelectedBillIds] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const invoiceMap = useMemo(
    () => new Map(invoices.map((invoice) => [invoice.id, invoice])),
    [invoices]
  )
  const selectedInvoices = selectedInvoiceIds
    .map((id) => invoiceMap.get(id))
    .filter((invoice): invoice is InvoiceListItem => Boolean(invoice))
  const selectedScope = selectedInvoices[0]
    ? invoiceScope(selectedInvoices[0])
    : undefined
  const selectedSellerName = selectedScope?.sellerName ?? ""
  const selectedBuyerName = selectedScope?.buyerName ?? ""
  const selectedSellerTaxNo = selectedScope?.sellerTaxNo
  const selectedBuyerTaxNo = selectedScope?.buyerTaxNo
  const selectedIsRedInvoice = selectedScope?.isRedInvoice ?? false
  const isInvoiceCompatible = (invoice: InvoiceListItem) => {
    if (!selectedScope) return true

    return (
      sameTaxOrName(invoice.sellerTaxNo, selectedSellerTaxNo, invoice.sellerName, selectedSellerName) &&
      sameTaxOrName(invoice.buyerTaxNo, selectedBuyerTaxNo, invoice.buyerName, selectedBuyerName) &&
      invoice.isRedInvoice === selectedIsRedInvoice
    )
  }
  const filteredPaymentBills = useMemo(
    () =>
      selectedSellerName && selectedBuyerName
        ? paymentBills.filter(
            (bill) =>
              sameText(bill.partner, selectedSellerName) &&
              sameTaxOrName(selectedBuyerTaxNo, bill.storeTaxNo, selectedBuyerName, bill.storeName) &&
              (selectedIsRedInvoice
                ? bill.matchedAmount > 0
                : bill.remainingAmount > 0)
          )
        : [],
    [paymentBills, selectedBuyerName, selectedBuyerTaxNo, selectedIsRedInvoice, selectedSellerName]
  )
  const filteredBillMap = useMemo(
    () => new Map(filteredPaymentBills.map((bill) => [bill.id, bill])),
    [filteredPaymentBills]
  )
  const compatibleInvoiceIds = invoices
    .filter(isInvoiceCompatible)
    .map((invoice) => invoice.id)
  const selectedBills = selectedBillIds
    .map((id) => filteredBillMap.get(id))
    .filter((bill): bill is PaymentBillItem => Boolean(bill))

  useEffect(() => {
    setSelectedBillIds((current) => {
      const next = current.filter((id) => filteredBillMap.has(id))
      return next.length === current.length ? current : next
    })
  }, [filteredBillMap])

  const invoiceTotal = selectedInvoices.reduce(
    (sum, invoice) => sum + invoice.totalAmount,
    0
  )
  const invoiceAbsTotal = Math.abs(invoiceTotal)
  const billRemainingTotal = selectedBills.reduce(
    (sum, bill) => sum + bill.remainingAmount,
    0
  )
  const billMatchedTotal = selectedBills.reduce(
    (sum, bill) => sum + bill.matchedAmount,
    0
  )

  const allocation = selectedBills.map((bill) => ({
    bill,
    matchAmount: 0,
    remainingAfterMatch: selectedIsRedInvoice
      ? bill.remainingAmount
      : bill.remainingAmount,
  }))
  let amountToConsume = selectedIsRedInvoice ? invoiceAbsTotal : invoiceTotal
  for (const item of allocation) {
    if (amountToConsume <= 0) break
    const capacity = selectedIsRedInvoice
      ? item.bill.matchedAmount
      : item.bill.remainingAmount
    if (capacity <= 0) continue

    const matched = Math.min(capacity, amountToConsume)
    item.matchAmount = selectedIsRedInvoice ? -matched : matched
    item.remainingAfterMatch = selectedIsRedInvoice
      ? item.bill.remainingAmount + matched
      : item.bill.remainingAmount - matched
    amountToConsume -= matched
  }
  if (selectedIsRedInvoice && amountToConsume > 0 && allocation.length > 0) {
    const last = allocation[allocation.length - 1]
    last.matchAmount -= amountToConsume
    last.remainingAfterMatch += amountToConsume
    amountToConsume = 0
  }
  const lastConsumed = [...allocation]
    .reverse()
    .find((item) => item.matchAmount !== 0)

  const validation = (() => {
    if (selectedInvoices.length === 0) {
      return {
        passed: false,
        status: "idle" as const,
        message: "请选择至少一张发票",
      }
    }

    if (selectedBills.length === 0) {
      return {
        passed: false,
        status: "idle" as const,
        message: "请选择至少一张业务单据",
      }
    }

    if (!selectedIsRedInvoice && invoiceTotal > billRemainingTotal) {
      return {
        passed: false,
        status: "error" as const,
        message: "发票合计金额大于单据可用剩余合计，拦截不通过",
      }
    }

    if (selectedIsRedInvoice) {
      return {
        passed: true,
        status: "red" as const,
        message: "红字发票将按所选历史单据反向释放已占用金额",
      }
    }

    if (Math.abs(invoiceTotal - billRemainingTotal) < 0.01) {
      return {
        passed: true,
        status: "exact" as const,
        message: "发票合计金额等于单据剩余合计，通过，单据无剩余",
      }
    }

    return {
      passed: true,
      status: "partial" as const,
      message: "发票合计金额小于单据剩余合计，通过，单据留存剩余金额",
    }
  })()

  const toggleInvoice = (invoiceId: string) => {
    const invoice = invoiceMap.get(invoiceId)
    if (!invoice) return

    setSelectedInvoiceIds((current) =>
      current.includes(invoiceId)
        ? current.filter((id) => id !== invoiceId)
        : current.length === 0 ||
            (sameTaxOrName(
              invoice.sellerTaxNo,
              invoiceMap.get(current[0])?.sellerTaxNo,
              invoice.sellerName,
              invoiceMap.get(current[0])?.sellerName ?? ""
            ) &&
              sameTaxOrName(
                invoice.buyerTaxNo,
                invoiceMap.get(current[0])?.buyerTaxNo,
                invoice.buyerName,
                invoiceMap.get(current[0])?.buyerName ?? ""
              ) &&
              invoice.isRedInvoice === invoiceMap.get(current[0])?.isRedInvoice)
          ? [...current, invoiceId]
          : current
    )
  }

  const toggleBill = (billId: string) => {
    setSelectedBillIds((current) =>
      current.includes(billId)
        ? current.filter((id) => id !== billId)
        : [...current, billId]
    )
  }

  const toggleAllInvoices = () => {
    setSelectedInvoiceIds((current) => {
      const scopeSource = current[0]
        ? invoiceMap.get(current[0])
        : invoices[0]
      if (!scopeSource) return []

      const scope = invoiceScope(scopeSource)
      const compatibleIds = invoices
        .filter(
          (item) =>
            sameTaxOrName(item.sellerTaxNo, scope.sellerTaxNo, item.sellerName, scope.sellerName) &&
            sameTaxOrName(item.buyerTaxNo, scope.buyerTaxNo, item.buyerName, scope.buyerName) &&
            item.isRedInvoice === scope.isRedInvoice
        )
        .map((item) => item.id)

      return compatibleIds.every((id) => current.includes(id))
        ? []
        : compatibleIds
    })
  }

  const buildMatchPairs = () => {
    const billBalances = selectedBills.map((bill) => ({
      bill,
      remaining: selectedIsRedInvoice ? bill.matchedAmount : bill.remainingAmount,
    }))
    const pairs: { invoiceId: string; billId: string; billNo: string; amount: number }[] = []

    for (const invoice of selectedInvoices) {
      let invoiceRemaining = Math.abs(invoice.totalAmount)
      for (const item of billBalances) {
        if (invoiceRemaining <= 0) break
        if (item.remaining <= 0) continue

        const amount = Math.min(invoiceRemaining, item.remaining)
        pairs.push({
          invoiceId: invoice.id,
          billId: item.bill.id,
          billNo: item.bill.docNo,
          amount: selectedIsRedInvoice ? -amount : amount,
        })
        invoiceRemaining -= amount
        item.remaining -= amount
      }
      if (selectedIsRedInvoice && invoiceRemaining > 0 && selectedBills[0]) {
        pairs.push({
          invoiceId: invoice.id,
          billId: selectedBills[0].id,
          billNo: selectedBills[0].docNo,
          amount: -invoiceRemaining,
        })
      }
    }

    return pairs
  }

  const submitAssociation = async () => {
    if (!validation.passed) return

    const pairs = buildMatchPairs()
    const formData = new FormData()
    formData.set("pairs", JSON.stringify(pairs))

    setIsSubmitting(true)
    try {
      const result = await createManualInvoiceAssociation(formData)
      toast[result.ok ? "success" : "error"](result.message)
      if (result.ok) {
        setSelectedInvoiceIds([])
        setSelectedBillIds([])
        router.refresh()
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left">
                <th className="h-10 w-10 px-2">
                  <Checkbox
                    checked={
                      compatibleInvoiceIds.length > 0 &&
                      compatibleInvoiceIds.every((id) =>
                        selectedInvoiceIds.includes(id)
                      )
                    }
                    onCheckedChange={toggleAllInvoices}
                  />
                </th>
                <th className="h-10 px-2 font-medium">发票号码</th>
                <th className="h-10 px-2 font-medium">销方名称</th>
                <th className="h-10 px-2 font-medium">买方名称</th>
                <th className="h-10 px-2 font-medium">开票日期</th>
                <th className="h-10 px-2 font-medium">当前状态</th>
                <th className="h-10 px-2 font-medium">原匹配单据</th>
                <th className="h-10 px-2 text-right font-medium">价税合计</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-2 py-8 text-center text-sm text-muted-foreground"
                  >
                    没有可人工关联的发票
                  </td>
                </tr>
              ) : (
                invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-border">
                    <td className="px-2 py-3">
                      <Checkbox
                        checked={selectedInvoiceIds.includes(invoice.id)}
                        disabled={
                          !selectedInvoiceIds.includes(invoice.id) &&
                          !isInvoiceCompatible(invoice)
                        }
                        onCheckedChange={() => toggleInvoice(invoice.id)}
                      />
                    </td>
                    <td className="px-2 py-3 font-medium">{invoice.invoiceNo}</td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.sellerName}>
                      {invoice.sellerName}
                    </td>
                    <td className="max-w-48 truncate px-2 py-3" title={invoice.buyerName}>
                      {invoice.buyerName}
                    </td>
                    <td className="px-2 py-3">{invoice.invoiceDate}</td>
                    <td className="px-2 py-3">
                      <div className="flex items-center gap-2">
                        <InvoiceStatusBadge status={invoice.matchStatus} />
                        {invoice.isRedInvoice && (
                          <Badge variant="destructive">红字</Badge>
                        )}
                      </div>
                    </td>
                    <td className="max-w-40 truncate px-2 py-3 text-primary" title={invoice.matchedDoc}>
                      {invoice.matchedDoc}
                    </td>
                    <td className="px-2 py-3 text-right font-medium">
                      {money(invoice.totalAmount)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="space-y-4 rounded-md border border-border p-4">
          <div className="space-y-2">
            <div className="text-sm font-medium">选择业务单据</div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="w-full justify-between">
                  <span className="truncate text-left">
                    {selectedBillIds.length > 0
                      ? `已选 ${selectedBillIds.length} 张单据`
                      : "选择一张或多张单据"}
                  </span>
                  <ChevronsUpDown className="h-4 w-4 opacity-60" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="max-h-80 w-96 overflow-y-auto">
                {filteredPaymentBills.length === 0 && (
                  <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                    {selectedScope
                      ? "没有符合当前购销方的付款单"
                      : "请先选择发票"}
                  </div>
                )}
                {filteredPaymentBills.map((bill) => (
                  <DropdownMenuCheckboxItem
                    key={bill.id}
                    checked={selectedBillIds.includes(bill.id)}
                    disabled={
                      selectedIsRedInvoice
                        ? bill.matchedAmount <= 0
                        : bill.remainingAmount <= 0
                    }
                    onCheckedChange={() => toggleBill(bill.id)}
                    onSelect={(event) => event.preventDefault()}
                  >
                    <div className="flex min-w-0 flex-1 flex-col">
                      <span className="truncate font-medium">{bill.docNo}</span>
                      <span className="truncate text-xs text-muted-foreground">
                        <span title={`${bill.partner} / ${bill.storeName}`}>
                          {bill.partner} / {bill.storeName}
                        </span>
                      </span>
                      <span className="text-xs text-muted-foreground">
                        已匹配 {money(bill.matchedAmount)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        剩余 {money(bill.remainingAmount)} / 原金额{" "}
                        {money(bill.amount)}
                      </span>
                    </div>
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="grid gap-2 rounded-md bg-muted p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">已选发票</span>
              <span>{selectedInvoices.length} 张</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">发票合计</span>
              <span className="font-medium">{money(invoiceTotal)}</span>
            </div>
            {selectedIsRedInvoice && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">红冲释放金额</span>
                <span className="font-medium">{money(invoiceAbsTotal)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">已选单据</span>
              <span>{selectedBills.length} 张</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">单据剩余合计</span>
              <span className="font-medium">{money(billRemainingTotal)}</span>
            </div>
            {selectedIsRedInvoice && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">单据已占用合计</span>
                <span className="font-medium">{money(billMatchedTotal)}</span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Badge
              variant={
                validation.passed
                  ? "default"
                  : validation.status === "error"
                    ? "destructive"
                    : "secondary"
              }
            >
              {validation.passed ? "通过" : "不通过"}
            </Badge>
            <p className="text-sm text-muted-foreground">{validation.message}</p>
            {validation.status === "partial" && lastConsumed && (
              <p className="text-sm text-muted-foreground">
                最后扣减单据 {lastConsumed.bill.docNo} 本次匹配{" "}
                {money(lastConsumed.matchAmount)}，匹配后剩余{" "}
                {money(lastConsumed.remainingAfterMatch)}
              </p>
            )}
          </div>

          {selectedBills.length > 0 && (
            <div className="space-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
              {allocation.map((item) => (
                <div key={item.bill.id} className="flex justify-between gap-3">
                  <span className="truncate">{item.bill.docNo}</span>
                  <span className="shrink-0">
                    本次 {money(item.matchAmount)} / 剩余{" "}
                    {money(item.remainingAfterMatch)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <Button
            className="w-full"
            disabled={!validation.passed || isSubmitting}
            onClick={submitAssociation}
          >
            <Check className="mr-2 h-4 w-4" />
            人工关联
          </Button>
        </div>
      </div>
    </div>
  )
}
