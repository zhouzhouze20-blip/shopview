"use client"

import { useState, useTransition } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { AlertTriangle, Check, Eye, MoreHorizontal, Trash2, UserCog } from "lucide-react"
import { toast } from "sonner"
import type { InvoiceListItem } from "@/lib/etl-data"
import {
  confirmInvoiceMatch,
  confirmInvoiceMatches,
  createSupplementalInvoiceAssociation,
  deleteInvoiceMatch,
} from "@/lib/actions"
import { Badge } from "@/components/ui/badge"
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
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"

const statusMap = {
  matched: { label: "待确认", variant: "default" as const },
  amount_mismatch: { label: "金额不一致", variant: "destructive" as const },
  unmatched: { label: "未匹配", variant: "secondary" as const },
  archived: { label: "已确认", variant: "outline" as const },
}

function money(value: number) {
  return `¥${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function invoiceFormData(invoiceId: string) {
  const formData = new FormData()
  formData.set("invoiceId", invoiceId)
  return formData
}

function DetailItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 break-words font-medium">{value}</div>
    </div>
  )
}

function InvoiceDetail({ invoice }: { invoice: InvoiceListItem }) {
  return (
    <DialogContent className="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle>匹配单据信息</DialogTitle>
        <DialogDescription>{invoice.matchedDoc}</DialogDescription>
      </DialogHeader>
      <div className="grid gap-3 text-sm sm:grid-cols-2">
        <DetailItem label="单据来源" value={invoice.documentSource} />
        <DetailItem label="匹配单据" value={invoice.matchedDoc} />
        <DetailItem label="单据类型" value={invoice.docType} />
        <DetailItem label="业务单据日期" value={invoice.matchedDocDate} />
        <DetailItem label="单据金额" value={money(invoice.matchedDocAmount)} />
        <DetailItem label="匹配分数" value={invoice.matchScore} />
        <DetailItem label="备注信息" value={invoice.remark} />
        <DetailItem label="发票号码" value={invoice.invoiceNo} />
        <DetailItem label="销方名称" value={invoice.sellerName} />
        <DetailItem label="购方名称" value={invoice.buyerName} />
        <DetailItem label="开票日期" value={invoice.invoiceDate} />
        <DetailItem label="发票价税合计" value={money(invoice.totalAmount)} />
        <DetailItem label="发票税额" value={money(invoice.taxAmount)} />
      </div>
    </DialogContent>
  )
}

export function InvoiceRowMenu({ invoice }: { invoice: InvoiceListItem }) {
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
            <Link href={`/invoices/matched?supplierName=${encodeURIComponent(invoice.invoiceNo)}`}>
              查看匹配
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <InvoiceDetail invoice={invoice} />
    </Dialog>
  )
}

function MatchedInvoiceDetailButton({ invoice }: { invoice: InvoiceListItem }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Eye className="mr-1 h-3 w-3" />
          详情
        </Button>
      </DialogTrigger>
      <InvoiceDetail invoice={invoice} />
    </Dialog>
  )
}

export function MatchedInvoicesTable({ invoices }: { invoices: InvoiceListItem[] }) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const allSelected = invoices.length > 0 && selectedIds.length === invoices.length

  const toggleAll = () => {
    setSelectedIds((current) =>
      current.length === invoices.length ? [] : invoices.map((invoice) => invoice.id)
    )
  }

  const toggleOne = (invoiceId: string) => {
    setSelectedIds((current) =>
      current.includes(invoiceId)
        ? current.filter((id) => id !== invoiceId)
        : [...current, invoiceId]
    )
  }

  const confirmSelected = () => {
    const formData = new FormData()
    formData.set("invoiceIds", selectedIds.join(","))
    startTransition(async () => {
      const result = await confirmInvoiceMatches(formData)
      toast[result.ok ? "success" : "error"](result.message)
      if (result.ok) setSelectedIds([])
      router.refresh()
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <Button disabled={selectedIds.length === 0 || isPending} onClick={confirmSelected}>
          <Check className="mr-2 h-4 w-4" />
          批量确认
        </Button>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox checked={allSelected} onCheckedChange={toggleAll} />
              </TableHead>
              <TableHead>发票号码</TableHead>
              <TableHead>销方名称</TableHead>
              <TableHead>购方名称</TableHead>
              <TableHead>开票日期</TableHead>
              <TableHead>业务单据日期</TableHead>
              <TableHead className="text-right">价税合计</TableHead>
              <TableHead>匹配单据</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((invoice) => (
              <TableRow key={invoice.id}>
                <TableCell>
                  <Checkbox
                    checked={selectedIds.includes(invoice.id)}
                    onCheckedChange={() => toggleOne(invoice.id)}
                  />
                </TableCell>
                <TableCell className="font-medium">{invoice.invoiceNo}</TableCell>
                <TableCell className="max-w-40 truncate" title={invoice.sellerName}>{invoice.sellerName}</TableCell>
                <TableCell className="max-w-40 truncate" title={invoice.buyerName}>{invoice.buyerName}</TableCell>
                <TableCell>{invoice.invoiceDate}</TableCell>
                <TableCell>{invoice.matchedDocDate}</TableCell>
                <TableCell className="text-right">{money(invoice.totalAmount)}</TableCell>
                <TableCell className="max-w-48 truncate text-primary" title={invoice.matchedDoc}>{invoice.matchedDoc}</TableCell>
                <TableCell>
                  <InvoiceStatusBadge status={invoice.matchStatus} />
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <MatchedInvoiceDetailButton invoice={invoice} />
                    <ConfirmInvoiceButton invoiceId={invoice.id} />
                    <DeleteInvoiceMatchButton invoiceId={invoice.id} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

export function ConfirmInvoiceButton({ invoiceId }: { invoiceId: string }) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  return (
    <Button
      size="sm"
      disabled={isPending}
      onClick={() => {
        startTransition(async () => {
          const result = await confirmInvoiceMatch(invoiceFormData(invoiceId))
          toast[result.ok ? "success" : "error"](result.message)
          router.refresh()
        })
      }}
    >
      <Check className="mr-1 h-3 w-3" />
      确认
    </Button>
  )
}

export function DeleteInvoiceMatchButton({ invoiceId }: { invoiceId: string }) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  return (
    <Button
      size="sm"
      variant="destructive"
      disabled={isPending}
      onClick={() => {
        startTransition(async () => {
          const result = await deleteInvoiceMatch(invoiceFormData(invoiceId))
          toast[result.ok ? "success" : "error"](result.message)
          router.refresh()
        })
      }}
    >
      <Trash2 className="mr-1 h-3 w-3" />
      删除
    </Button>
  )
}

function SupplementalAssociationDialog({ invoice }: { invoice: InvoiceListItem }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [isPending, startTransition] = useTransition()

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserCog className="mr-1 h-3 w-3" />
          补录并关联
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>补录业务单据并关联发票</DialogTitle>
          <DialogDescription>
            系统会自动生成补录单据号，提交后写入手工补录单据并建立发票关联。
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            const formData = new FormData(event.currentTarget)
            startTransition(async () => {
              const result = await createSupplementalInvoiceAssociation(formData)
              toast[result.ok ? "success" : "error"](result.message)
              if (result.ok) {
                setOpen(false)
                router.refresh()
              }
            })
          }}
        >
          <input type="hidden" name="invoiceId" value={invoice.id} />
          <input type="hidden" name="invoiceAmount" value={invoice.totalAmount} />
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="font-medium">业务日期</span>
              <Input
                name="businessDate"
                required
                type="date"
                defaultValue={invoice.invoiceDate !== "-" ? invoice.invoiceDate : undefined}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">供应商/往来方</span>
              <Input
                name="partnerName"
                required
                defaultValue={invoice.sellerName !== "-" ? invoice.sellerName : ""}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">单据金额</span>
              <Input name="amount" required type="number" step="0.01" defaultValue={invoice.totalAmount} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">门店/购方</span>
              <Input name="storeName" defaultValue={invoice.buyerName !== "-" ? invoice.buyerName : ""} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">所属部门</span>
              <Input name="departmentName" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium">业务类型</span>
              <Input name="businessType" placeholder="费用报销/采购/其他" />
            </label>
            <label className="space-y-1 text-sm sm:col-span-2">
              <span className="font-medium">备注</span>
              <Textarea name="remark" placeholder="说明无原始业务单据的原因或补充信息" />
            </label>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? "提交中..." : "提交关联"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

type DraftState = {
  status?: "exception"
}

export function UnmatchedInvoicesTable({ invoices }: { invoices: InvoiceListItem[] }) {
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({})

  const markException = (invoice: InvoiceListItem) => {
    setDrafts((current) => ({
      ...current,
      [invoice.id]: { status: "exception" },
    }))
    toast.success(`${invoice.invoiceNo} 已标记异常`)
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>发票号码</TableHead>
            <TableHead>销方名称</TableHead>
            <TableHead>购方名称</TableHead>
            <TableHead className="text-right">金额</TableHead>
            <TableHead>开票日期</TableHead>
            <TableHead>处理状态</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {invoices.map((invoice) => {
            const draft = drafts[invoice.id] ?? {}
            return (
              <TableRow key={invoice.id}>
                <TableCell className="font-medium">{invoice.invoiceNo}</TableCell>
                <TableCell className="max-w-40 truncate" title={invoice.sellerName}>{invoice.sellerName}</TableCell>
                <TableCell className="max-w-40 truncate" title={invoice.buyerName}>{invoice.buyerName}</TableCell>
                <TableCell className="text-right">{money(invoice.totalAmount)}</TableCell>
                <TableCell>{invoice.invoiceDate}</TableCell>
                <TableCell>
                  {draft.status === "exception" ? (
                    <Badge variant="destructive">异常</Badge>
                  ) : (
                    <span className="text-sm text-muted-foreground">未处理</span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <SupplementalAssociationDialog invoice={invoice} />
                    <Button size="sm" variant="destructive" onClick={() => markException(invoice)}>
                      <AlertTriangle className="mr-1 h-3 w-3" />
                      异常
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

export function InvoiceStatusBadge({ status }: { status: InvoiceListItem["matchStatus"] }) {
  return <Badge variant={statusMap[status].variant}>{statusMap[status].label}</Badge>
}
