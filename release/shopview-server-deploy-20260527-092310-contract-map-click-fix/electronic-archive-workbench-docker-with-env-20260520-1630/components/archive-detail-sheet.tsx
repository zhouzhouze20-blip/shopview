"use client"

import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DocumentViewer } from "@/components/document-viewer"
import {
  FileText,
  Receipt,
  Building2,
  CreditCard,
  BookOpen,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
  Download,
  Printer,
  Share2,
  Eye,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface ArchiveDetailSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  archiveData?: {
    id: string
    voucherNo: string
    date: string
    amount: number
    status: "complete" | "partial" | "pending"
    businessDoc?: {
      type: string
      docNo: string
      date: string
      amount: number
      supplier: string
      attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]
    }
    invoice?: {
      invoiceNo: string
      invoiceCode: string
      date: string
      amount: number
      taxAmount: number
      type: string
      attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]
    }
    bankTransaction?: {
      transNo: string
      date: string
      amount: number
      bankName: string
      accountNo: string
      attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]
    }
    bankReceipt?: {
      receiptNo: string
      date: string
      amount: number
      attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]
    }
    voucher?: {
      voucherNo: string
      date: string
      debitAmount: number
      creditAmount: number
      summary: string
      attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]
    }
    ncRecord?: {
      ncVoucherNo: string
      syncTime: string
      status: "success" | "failed" | "pending"
    }
  }
}

const mockArchiveData = {
  id: "ARC-2024-001234",
  voucherNo: "PZ-2024-001234",
  date: "2024-01-15",
  amount: 125000.00,
  status: "complete" as const,
  businessDoc: {
    type: "采购入库单",
    docNo: "PO-2024-005678",
    date: "2024-01-10",
    amount: 125000.00,
    supplier: "上海科技有限公司",
    attachments: [
      { id: "1", name: "采购入库单.pdf", type: "pdf" as const, url: "/docs/po.pdf", pages: 2 },
      { id: "2", name: "采购合同.pdf", type: "pdf" as const, url: "/docs/contract.pdf", pages: 5 },
    ],
  },
  invoice: {
    invoiceNo: "12345678901234567890",
    invoiceCode: "3100221130",
    date: "2024-01-12",
    amount: 110619.47,
    taxAmount: 14380.53,
    type: "增值税专用发票",
    attachments: [
      { id: "3", name: "增值税专用发票.pdf", type: "pdf" as const, url: "/docs/invoice.pdf", pages: 1 },
    ],
  },
  bankTransaction: {
    transNo: "TRANS-2024-001234567",
    date: "2024-01-14",
    amount: 125000.00,
    bankName: "中国工商银行",
    accountNo: "6222****1234",
    attachments: [],
  },
  bankReceipt: {
    receiptNo: "REC-2024-001234",
    date: "2024-01-14",
    amount: 125000.00,
    attachments: [
      { id: "4", name: "银行回单.pdf", type: "pdf" as const, url: "/docs/receipt.pdf", pages: 1 },
    ],
  },
  voucher: {
    voucherNo: "PZ-2024-001234",
    date: "2024-01-15",
    debitAmount: 125000.00,
    creditAmount: 125000.00,
    summary: "支付上海科技有限公司采购款",
    attachments: [
      { id: "5", name: "记账凭证.pdf", type: "pdf" as const, url: "/docs/voucher.pdf", pages: 1 },
    ],
  },
  ncRecord: {
    ncVoucherNo: "NC-PZ-2024-001234",
    syncTime: "2024-01-15 16:30:45",
    status: "success" as const,
  },
}

const timelineSteps = [
  { key: "businessDoc", label: "业务单据", icon: FileText },
  { key: "invoice", label: "发票", icon: Receipt },
  { key: "bankTransaction", label: "银行流水", icon: Building2 },
  { key: "bankReceipt", label: "银行回单", icon: CreditCard },
  { key: "voucher", label: "凭证", icon: BookOpen },
  { key: "ncRecord", label: "NC凭证", icon: CheckCircle2 },
]

export function ArchiveDetailSheet({ open, onOpenChange, archiveData }: ArchiveDetailSheetProps) {
  const [selectedStep, setSelectedStep] = useState<string>("businessDoc")
  const [showPreview, setShowPreview] = useState(false)
  const [previewFiles, setPreviewFiles] = useState<{ id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]>([])

  const data = archiveData || mockArchiveData

  const getStepStatus = (stepKey: string) => {
    const stepData = data[stepKey as keyof typeof data]
    if (!stepData) return "pending"
    if (stepKey === "ncRecord") {
      return (stepData as typeof data.ncRecord)?.status === "success" ? "complete" : "pending"
    }
    return "complete"
  }

  const handleViewAttachments = (attachments: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number }[]) => {
    setPreviewFiles(attachments)
    setShowPreview(true)
  }

  const getAllAttachments = () => {
    const all: { id: string; name: string; type: "pdf" | "image" | "other"; url: string; pages?: number; source: string }[] = []
    if (data.businessDoc?.attachments) {
      data.businessDoc.attachments.forEach(a => all.push({ ...a, source: "业务单据" }))
    }
    if (data.invoice?.attachments) {
      data.invoice.attachments.forEach(a => all.push({ ...a, source: "发票" }))
    }
    if (data.bankReceipt?.attachments) {
      data.bankReceipt.attachments.forEach(a => all.push({ ...a, source: "银行回单" }))
    }
    if (data.voucher?.attachments) {
      data.voucher.attachments.forEach(a => all.push({ ...a, source: "凭证" }))
    }
    return all
  }

  const renderStepContent = () => {
    switch (selectedStep) {
      case "businessDoc":
        return data.businessDoc ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-muted-foreground">单据类型</span>
                <p className="font-medium">{data.businessDoc.type}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">单据编号</span>
                <p className="font-medium">{data.businessDoc.docNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">单据日期</span>
                <p className="font-medium">{data.businessDoc.date}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">金额</span>
                <p className="font-medium">¥{data.businessDoc.amount.toLocaleString()}</p>
              </div>
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">供应商</span>
                <p className="font-medium">{data.businessDoc.supplier}</p>
              </div>
            </div>
            {data.businessDoc.attachments.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground mb-2 block">附件</span>
                <div className="space-y-2">
                  {data.businessDoc.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-2 bg-muted/50 rounded"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{att.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewAttachments([att])}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无业务单据</p>
          </div>
        )

      case "invoice":
        return data.invoice ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-sm text-muted-foreground">发票类型</span>
                <p className="font-medium">{data.invoice.type}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">发票代码</span>
                <p className="font-medium">{data.invoice.invoiceCode}</p>
              </div>
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">发票号码</span>
                <p className="font-medium font-mono">{data.invoice.invoiceNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">开票日期</span>
                <p className="font-medium">{data.invoice.date}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">金额（不含税）</span>
                <p className="font-medium">¥{data.invoice.amount.toLocaleString()}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">税额</span>
                <p className="font-medium">¥{data.invoice.taxAmount.toLocaleString()}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">价税合计</span>
                <p className="font-medium text-primary">
                  ¥{(data.invoice.amount + data.invoice.taxAmount).toLocaleString()}
                </p>
              </div>
            </div>
            {data.invoice.attachments.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground mb-2 block">附件</span>
                <div className="space-y-2">
                  {data.invoice.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-2 bg-muted/50 rounded"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{att.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewAttachments([att])}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无发票信息</p>
          </div>
        )

      case "bankTransaction":
        return data.bankTransaction ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">交易流水号</span>
                <p className="font-medium font-mono">{data.bankTransaction.transNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">交易日期</span>
                <p className="font-medium">{data.bankTransaction.date}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">交易金额</span>
                <p className="font-medium">¥{data.bankTransaction.amount.toLocaleString()}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">开户银行</span>
                <p className="font-medium">{data.bankTransaction.bankName}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">账号</span>
                <p className="font-medium font-mono">{data.bankTransaction.accountNo}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无银行流水</p>
          </div>
        )

      case "bankReceipt":
        return data.bankReceipt ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">回单编号</span>
                <p className="font-medium font-mono">{data.bankReceipt.receiptNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">回单日期</span>
                <p className="font-medium">{data.bankReceipt.date}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">金额</span>
                <p className="font-medium">¥{data.bankReceipt.amount.toLocaleString()}</p>
              </div>
            </div>
            {data.bankReceipt.attachments.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground mb-2 block">附件</span>
                <div className="space-y-2">
                  {data.bankReceipt.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-2 bg-muted/50 rounded"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{att.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewAttachments([att])}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无银行回单</p>
          </div>
        )

      case "voucher":
        return data.voucher ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">凭证编号</span>
                <p className="font-medium font-mono">{data.voucher.voucherNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">凭证日期</span>
                <p className="font-medium">{data.voucher.date}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">借方金额</span>
                <p className="font-medium">¥{data.voucher.debitAmount.toLocaleString()}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">贷方金额</span>
                <p className="font-medium">¥{data.voucher.creditAmount.toLocaleString()}</p>
              </div>
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">摘要</span>
                <p className="font-medium">{data.voucher.summary}</p>
              </div>
            </div>
            {data.voucher.attachments.length > 0 && (
              <div>
                <span className="text-sm text-muted-foreground mb-2 block">附件</span>
                <div className="space-y-2">
                  {data.voucher.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-2 bg-muted/50 rounded"
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{att.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewAttachments([att])}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无凭证信息</p>
          </div>
        )

      case "ncRecord":
        return data.ncRecord ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <span className="text-sm text-muted-foreground">NC凭证号</span>
                <p className="font-medium font-mono">{data.ncRecord.ncVoucherNo}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">同步时间</span>
                <p className="font-medium">{data.ncRecord.syncTime}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">同步状态</span>
                <Badge
                  variant={data.ncRecord.status === "success" ? "default" : "destructive"}
                  className={cn(
                    data.ncRecord.status === "success" && "bg-green-500/10 text-green-600 hover:bg-green-500/20"
                  )}
                >
                  {data.ncRecord.status === "success" ? "同步成功" : "同步失败"}
                </Badge>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>暂无NC对接记录</p>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-2xl p-0 flex flex-col">
          <SheetHeader className="px-6 py-4 border-b flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <SheetTitle className="text-lg">档案详情</SheetTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {data.id} | {data.date}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={cn(
                    data.status === "complete" && "bg-green-500/10 text-green-600",
                    data.status === "partial" && "bg-yellow-500/10 text-yellow-600",
                    data.status === "pending" && "bg-gray-500/10 text-gray-600"
                  )}
                >
                  {data.status === "complete" ? "归档完成" : data.status === "partial" ? "部分归档" : "待归档"}
                </Badge>
              </div>
            </div>
          </SheetHeader>

          <Tabs defaultValue="timeline" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="mx-6 mt-4 flex-shrink-0">
              <TabsTrigger value="timeline">业务流转</TabsTrigger>
              <TabsTrigger value="attachments">全部附件</TabsTrigger>
            </TabsList>

            <TabsContent value="timeline" className="flex-1 overflow-hidden m-0 mt-4">
              <div className="flex h-full">
                {/* Timeline Sidebar */}
                <div className="w-48 border-r flex-shrink-0 px-4">
                  <div className="relative">
                    {timelineSteps.map((step, index) => {
                      const status = getStepStatus(step.key)
                      const Icon = step.icon
                      const isLast = index === timelineSteps.length - 1

                      return (
                        <div key={step.key} className="relative">
                          <button
                            onClick={() => setSelectedStep(step.key)}
                            className={cn(
                              "w-full flex items-center gap-3 py-3 pl-2 pr-2 rounded-lg transition-colors text-left",
                              selectedStep === step.key
                                ? "bg-primary/10"
                                : "hover:bg-muted"
                            )}
                          >
                            <div
                              className={cn(
                                "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 z-10",
                                status === "complete"
                                  ? "bg-green-500 text-white"
                                  : "bg-muted text-muted-foreground"
                              )}
                            >
                              {status === "complete" ? (
                                <CheckCircle2 className="h-4 w-4" />
                              ) : (
                                <Icon className="h-4 w-4" />
                              )}
                            </div>
                            <span
                              className={cn(
                                "text-sm font-medium",
                                selectedStep === step.key
                                  ? "text-primary"
                                  : "text-foreground"
                              )}
                            >
                              {step.label}
                            </span>
                            {selectedStep === step.key && (
                              <ChevronRight className="h-4 w-4 ml-auto text-primary" />
                            )}
                          </button>
                          {!isLast && (
                            <div
                              className={cn(
                                "absolute left-[22px] top-[44px] w-0.5 h-3",
                                status === "complete" ? "bg-green-500" : "bg-muted"
                              )}
                            />
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Content Area */}
                <ScrollArea className="flex-1">
                  <div className="p-6">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">
                          {timelineSteps.find((s) => s.key === selectedStep)?.label}详情
                        </CardTitle>
                      </CardHeader>
                      <CardContent>{renderStepContent()}</CardContent>
                    </Card>
                  </div>
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="attachments" className="flex-1 overflow-hidden m-0 mt-4">
              <ScrollArea className="h-full">
                <div className="p-6 space-y-4">
                  {getAllAttachments().length > 0 ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          共 {getAllAttachments().length} 个附件
                        </span>
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm">
                            <Download className="h-4 w-4 mr-2" />
                            全部下载
                          </Button>
                          <Button variant="outline" size="sm">
                            <Printer className="h-4 w-4 mr-2" />
                            打印
                          </Button>
                        </div>
                      </div>
                      <div className="grid gap-3">
                        {getAllAttachments().map((att) => (
                          <div
                            key={att.id}
                            className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
                                <FileText className="h-5 w-5 text-primary" />
                              </div>
                              <div>
                                <p className="text-sm font-medium">{att.name}</p>
                                <p className="text-xs text-muted-foreground">{att.source}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewAttachments([att])}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="sm">
                                <Download className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="sm">
                                <Share2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>暂无附件</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>

          {/* Footer Actions */}
          <div className="px-6 py-4 border-t flex items-center justify-between flex-shrink-0 bg-muted/30">
            <span className="text-sm text-muted-foreground">
              金额合计: <span className="font-semibold text-foreground">¥{data.amount.toLocaleString()}</span>
            </span>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                关闭
              </Button>
              <Button
                onClick={() => handleViewAttachments(getAllAttachments())}
                disabled={getAllAttachments().length === 0}
              >
                <Eye className="h-4 w-4 mr-2" />
                预览全部附件
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Document Preview Dialog */}
      {showPreview && (
        <div className="fixed inset-0 z-[60] bg-black/80 flex items-center justify-center p-4">
          <div className="w-full max-w-5xl h-[85vh] bg-background rounded-lg overflow-hidden">
            <DocumentViewer
              files={previewFiles}
              onClose={() => setShowPreview(false)}
            />
          </div>
        </div>
      )}
    </>
  )
}
