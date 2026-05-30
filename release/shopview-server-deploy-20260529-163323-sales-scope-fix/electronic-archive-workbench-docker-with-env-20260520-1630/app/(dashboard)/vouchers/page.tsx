"use client"

import { useState } from "react"
import {
  BookCheck,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  FileText,
  Send,
  CheckCircle2,
  Clock,
  AlertCircle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { StatCard } from "@/components/stat-card"
import Link from "next/link"

const stats = [
  {
    title: "待生成凭证",
    value: 89,
    icon: <Clock className="h-5 w-5" />,
    variant: "warning" as const,
  },
  {
    title: "已生成凭证",
    value: 456,
    icon: <BookCheck className="h-5 w-5" />,
    variant: "default" as const,
  },
  {
    title: "已推送NC",
    value: 398,
    icon: <Send className="h-5 w-5" />,
    variant: "success" as const,
  },
  {
    title: "推送失败",
    value: 12,
    icon: <AlertCircle className="h-5 w-5" />,
    variant: "error" as const,
  },
]

const vouchers = [
  {
    id: "1",
    archiveNo: "AR-2024-0001",
    voucherNo: "PZ-2024-11-0001",
    businessDate: "2024-11-15",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    ncVoucherNo: "NC-2024-0892",
    pushStatus: "success",
    amount: 96050.0,
  },
  {
    id: "2",
    archiveNo: "AR-2024-0002",
    voucherNo: "PZ-2024-11-0002",
    businessDate: "2024-11-14",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: false,
    ncVoucherNo: "",
    pushStatus: "pending",
    amount: 135600.0,
  },
  {
    id: "3",
    archiveNo: "AR-2024-0003",
    voucherNo: "PZ-2024-11-0003",
    businessDate: "2024-11-13",
    invoiceMatched: true,
    transactionMatched: false,
    documentMatched: true,
    ncVoucherNo: "",
    pushStatus: "pending",
    amount: 36160.0,
  },
  {
    id: "4",
    archiveNo: "AR-2024-0004",
    voucherNo: "PZ-2024-11-0004",
    businessDate: "2024-11-12",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    ncVoucherNo: "NC-2024-0890",
    pushStatus: "success",
    amount: 500000.0,
  },
  {
    id: "5",
    archiveNo: "AR-2024-0005",
    voucherNo: "PZ-2024-11-0005",
    businessDate: "2024-11-11",
    invoiceMatched: true,
    transactionMatched: true,
    documentMatched: true,
    ncVoucherNo: "",
    pushStatus: "failed",
    amount: 258000.0,
  },
]

const pushStatusMap: Record<
  string,
  {
    label: string
    variant: "default" | "secondary" | "destructive" | "outline"
    icon?: React.ReactNode
  }
> = {
  success: {
    label: "已推送",
    variant: "default" as const,
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  pending: {
    label: "待推送",
    variant: "secondary" as const,
    icon: <Clock className="h-3 w-3" />,
  },
  failed: {
    label: "推送失败",
    variant: "destructive" as const,
    icon: <AlertCircle className="h-3 w-3" />,
  },
}

export default function VouchersPage() {
  const [searchTerm, setSearchTerm] = useState("")

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">凭证档案</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          管理档案包，生成记账凭证，推送至 NC 系统。
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            icon={stat.icon}
            variant={stat.variant}
          />
        ))}
      </div>

      {/* 凭证列表 */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base font-medium">凭证列表</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索档案号/凭证号"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-64 pl-9"
                />
              </div>
              <Select defaultValue="all">
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="推送状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="success">已推送</SelectItem>
                  <SelectItem value="pending">待推送</SelectItem>
                  <SelectItem value="failed">推送失败</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>档案编号</TableHead>
                  <TableHead>凭证号</TableHead>
                  <TableHead>业务日期</TableHead>
                  <TableHead className="text-center">发票</TableHead>
                  <TableHead className="text-center">流水</TableHead>
                  <TableHead className="text-center">单据</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>NC凭证号</TableHead>
                  <TableHead>推送状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vouchers.map((voucher) => (
                  <TableRow key={voucher.id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/vouchers/${voucher.id}`}
                        className="text-primary hover:underline"
                      >
                        {voucher.archiveNo}
                      </Link>
                    </TableCell>
                    <TableCell>{voucher.voucherNo}</TableCell>
                    <TableCell>{voucher.businessDate}</TableCell>
                    <TableCell className="text-center">
                      {voucher.invoiceMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {voucher.transactionMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {voucher.documentMatched ? (
                        <CheckCircle2 className="mx-auto h-4 w-4 text-emerald-500" />
                      ) : (
                        <AlertCircle className="mx-auto h-4 w-4 text-amber-500" />
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{voucher.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {voucher.ncVoucherNo || (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={pushStatusMap[voucher.pushStatus].variant}
                        className="gap-1"
                      >
                        {pushStatusMap[voucher.pushStatus].icon}
                        {pushStatusMap[voucher.pushStatus].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/vouchers/${voucher.id}`}>
                              <Eye className="mr-2 h-4 w-4" />
                              查看档案
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <FileText className="mr-2 h-4 w-4" />
                            预览凭证
                          </DropdownMenuItem>
                          {voucher.pushStatus !== "success" && (
                            <DropdownMenuItem>
                              <Send className="mr-2 h-4 w-4" />
                              推送NC
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
