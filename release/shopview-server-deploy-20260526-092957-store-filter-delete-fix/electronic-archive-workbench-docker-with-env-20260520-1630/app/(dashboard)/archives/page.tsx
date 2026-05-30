"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ArchiveDetailSheet } from "@/components/archive-detail-sheet"
import { DocumentViewer } from "@/components/document-viewer"
import {
  Search,
  Filter,
  Download,
  Eye,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Package,
  Printer,
} from "lucide-react"
import { cn } from "@/lib/utils"

const archiveData = [
  {
    id: "ARC-2024-001234",
    voucherNo: "PZ-2024-001234",
    date: "2024-01-15",
    type: "付款凭证",
    businessDoc: "PO-2024-005678",
    invoice: "12345678901234567890",
    amount: 125000.00,
    attachmentCount: 5,
    status: "complete" as const,
    ncStatus: "synced" as const,
  },
  {
    id: "ARC-2024-001235",
    voucherNo: "PZ-2024-001235",
    date: "2024-01-15",
    type: "收款凭证",
    businessDoc: "SO-2024-003456",
    invoice: "98765432109876543210",
    amount: 89000.00,
    attachmentCount: 4,
    status: "complete" as const,
    ncStatus: "synced" as const,
  },
  {
    id: "ARC-2024-001236",
    voucherNo: "PZ-2024-001236",
    date: "2024-01-14",
    type: "付款凭证",
    businessDoc: "PO-2024-005679",
    invoice: "11122233344455566677",
    amount: 56000.00,
    attachmentCount: 3,
    status: "partial" as const,
    ncStatus: "pending" as const,
  },
  {
    id: "ARC-2024-001237",
    voucherNo: "PZ-2024-001237",
    date: "2024-01-14",
    type: "转账凭证",
    businessDoc: "TR-2024-001234",
    invoice: "-",
    amount: 200000.00,
    attachmentCount: 2,
    status: "complete" as const,
    ncStatus: "synced" as const,
  },
  {
    id: "ARC-2024-001238",
    voucherNo: "-",
    date: "2024-01-13",
    type: "待生成",
    businessDoc: "PO-2024-005680",
    invoice: "22233344455566677788",
    amount: 78500.00,
    attachmentCount: 4,
    status: "pending" as const,
    ncStatus: "none" as const,
  },
  {
    id: "ARC-2024-001239",
    voucherNo: "-",
    date: "2024-01-13",
    type: "待生成",
    businessDoc: "PO-2024-005681",
    invoice: "33344455566677788899",
    amount: 45000.00,
    attachmentCount: 3,
    status: "pending" as const,
    ncStatus: "none" as const,
  },
]

const pendingItems = [
  {
    id: "PEND-001",
    businessDoc: "PO-2024-005680",
    supplier: "深圳电子科技有限公司",
    invoice: "22233344455566677788",
    amount: 78500.00,
    invoiceAmount: 78500.00,
    bankAmount: 78500.00,
    receiptStatus: true,
    matchStatus: "matched" as const,
  },
  {
    id: "PEND-002",
    businessDoc: "PO-2024-005681",
    supplier: "广州材料供应商",
    invoice: "33344455566677788899",
    amount: 45000.00,
    invoiceAmount: 45000.00,
    bankAmount: 45000.00,
    receiptStatus: true,
    matchStatus: "matched" as const,
  },
  {
    id: "PEND-003",
    businessDoc: "PO-2024-005682",
    supplier: "北京服务公司",
    invoice: "44455566677788899900",
    amount: 32000.00,
    invoiceAmount: 32000.00,
    bankAmount: 0,
    receiptStatus: false,
    matchStatus: "partial" as const,
  },
]

export default function ArchivesPage() {
  const [selectedArchives, setSelectedArchives] = useState<string[]>([])
  const [selectedPending, setSelectedPending] = useState<string[]>([])
  const [detailOpen, setDetailOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateProgress, setGenerateProgress] = useState(0)

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedArchives(archiveData.map((a) => a.id))
    } else {
      setSelectedArchives([])
    }
  }

  const handleSelectArchive = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedArchives([...selectedArchives, id])
    } else {
      setSelectedArchives(selectedArchives.filter((a) => a !== id))
    }
  }

  const handleSelectPending = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedPending([...selectedPending, id])
    } else {
      setSelectedPending(selectedPending.filter((p) => p !== id))
    }
  }

  const handleGenerate = () => {
    setIsGenerating(true)
    setGenerateProgress(0)
    const interval = setInterval(() => {
      setGenerateProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval)
          setIsGenerating(false)
          setSelectedPending([])
          return 100
        }
        return prev + 10
      })
    }, 300)
  }

  const filteredArchives = archiveData.filter((archive) => {
    const matchesSearch =
      archive.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      archive.voucherNo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      archive.businessDoc.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === "all" || archive.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const stats = {
    total: archiveData.length,
    complete: archiveData.filter((a) => a.status === "complete").length,
    partial: archiveData.filter((a) => a.status === "partial").length,
    pending: archiveData.filter((a) => a.status === "pending").length,
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">电子档案生成</h1>
          <p className="text-sm text-muted-foreground mt-1">
            管理和生成电子档案，支持附件预览和批量操作
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新数据
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            导出报表
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">档案总数</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Package className="h-5 w-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">归档完成</p>
                <p className="text-2xl font-bold text-green-600">{stats.complete}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">部分归档</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.partial}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-yellow-500/10 flex items-center justify-center">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">待生成</p>
                <p className="text-2xl font-bold text-gray-600">{stats.pending}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-gray-500/10 flex items-center justify-center">
                <Clock className="h-5 w-5 text-gray-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Generation Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">待生成档案</CardTitle>
              <CardDescription>
                以下业务单据已完成发票匹配和银行流水匹配，可生成电子档案
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {isGenerating && (
                <div className="flex items-center gap-2 mr-4">
                  <span className="text-sm text-muted-foreground">生成中...</span>
                  <Progress value={generateProgress} className="w-24 h-2" />
                </div>
              )}
              <Button
                onClick={handleGenerate}
                disabled={selectedPending.length === 0 || isGenerating}
              >
                <FileText className="h-4 w-4 mr-2" />
                生成档案 ({selectedPending.length})
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={
                      selectedPending.length === pendingItems.filter((p) => p.matchStatus === "matched").length &&
                      selectedPending.length > 0
                    }
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedPending(
                          pendingItems.filter((p) => p.matchStatus === "matched").map((p) => p.id)
                        )
                      } else {
                        setSelectedPending([])
                      }
                    }}
                  />
                </TableHead>
                <TableHead>业务单据</TableHead>
                <TableHead>供应商</TableHead>
                <TableHead>发票号码</TableHead>
                <TableHead className="text-right">单据金额</TableHead>
                <TableHead className="text-right">发票金额</TableHead>
                <TableHead className="text-right">银行金额</TableHead>
                <TableHead className="text-center">回单</TableHead>
                <TableHead className="text-center">匹配状态</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pendingItems.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedPending.includes(item.id)}
                      disabled={item.matchStatus !== "matched"}
                      onCheckedChange={(checked) =>
                        handleSelectPending(item.id, checked as boolean)
                      }
                    />
                  </TableCell>
                  <TableCell className="font-medium">{item.businessDoc}</TableCell>
                  <TableCell>{item.supplier}</TableCell>
                  <TableCell className="font-mono text-xs">{item.invoice}</TableCell>
                  <TableCell className="text-right">¥{item.amount.toLocaleString()}</TableCell>
                  <TableCell className="text-right">¥{item.invoiceAmount.toLocaleString()}</TableCell>
                  <TableCell className="text-right">
                    {item.bankAmount > 0 ? `¥${item.bankAmount.toLocaleString()}` : "-"}
                  </TableCell>
                  <TableCell className="text-center">
                    {item.receiptStatus ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600 mx-auto" />
                    ) : (
                      <Clock className="h-4 w-4 text-gray-400 mx-auto" />
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant="secondary"
                      className={cn(
                        item.matchStatus === "matched" && "bg-green-500/10 text-green-600",
                        item.matchStatus === "partial" && "bg-yellow-500/10 text-yellow-600"
                      )}
                    >
                      {item.matchStatus === "matched" ? "完全匹配" : "部分匹配"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Archive List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">档案列表</CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索档案编号、凭证号..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="状态筛选" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="complete">归档完成</SelectItem>
                  <SelectItem value="partial">部分归档</SelectItem>
                  <SelectItem value="pending">待生成</SelectItem>
                </SelectContent>
              </Select>
              {selectedArchives.length > 0 && (
                <>
                  <Button variant="outline" size="sm">
                    <Printer className="h-4 w-4 mr-2" />
                    批量打印
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    批量下载
                  </Button>
                </>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={
                      selectedArchives.length === filteredArchives.length &&
                      filteredArchives.length > 0
                    }
                    onCheckedChange={handleSelectAll}
                  />
                </TableHead>
                <TableHead>档案编号</TableHead>
                <TableHead>凭证编号</TableHead>
                <TableHead>日期</TableHead>
                <TableHead>凭证类型</TableHead>
                <TableHead>业务单据</TableHead>
                <TableHead className="text-right">金额</TableHead>
                <TableHead className="text-center">附件数</TableHead>
                <TableHead className="text-center">归档状态</TableHead>
                <TableHead className="text-center">NC状态</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredArchives.map((archive) => (
                <TableRow key={archive.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedArchives.includes(archive.id)}
                      onCheckedChange={(checked) =>
                        handleSelectArchive(archive.id, checked as boolean)
                      }
                    />
                  </TableCell>
                  <TableCell className="font-medium">{archive.id}</TableCell>
                  <TableCell className="font-mono text-sm">
                    {archive.voucherNo !== "-" ? archive.voucherNo : "-"}
                  </TableCell>
                  <TableCell>{archive.date}</TableCell>
                  <TableCell>{archive.type}</TableCell>
                  <TableCell>{archive.businessDoc}</TableCell>
                  <TableCell className="text-right">
                    ¥{archive.amount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline">{archive.attachmentCount}</Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant="secondary"
                      className={cn(
                        archive.status === "complete" && "bg-green-500/10 text-green-600",
                        archive.status === "partial" && "bg-yellow-500/10 text-yellow-600",
                        archive.status === "pending" && "bg-gray-500/10 text-gray-600"
                      )}
                    >
                      {archive.status === "complete"
                        ? "完成"
                        : archive.status === "partial"
                        ? "部分"
                        : "待生成"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant="secondary"
                      className={cn(
                        archive.ncStatus === "synced" && "bg-blue-500/10 text-blue-600",
                        archive.ncStatus === "pending" && "bg-yellow-500/10 text-yellow-600",
                        archive.ncStatus === "none" && "bg-gray-500/10 text-gray-600"
                      )}
                    >
                      {archive.ncStatus === "synced"
                        ? "已同步"
                        : archive.ncStatus === "pending"
                        ? "待同步"
                        : "-"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDetailOpen(true)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Archive Detail Sheet */}
      <ArchiveDetailSheet open={detailOpen} onOpenChange={setDetailOpen} />
    </div>
  )
}
