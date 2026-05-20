"use client"

import { useState } from "react"
import {
  ArrowLeft,
  Search,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import Link from "next/link"

const ncRecords = [
  {
    id: "1",
    voucherNo: "PZ-2024-11-0001",
    ncVoucherNo: "NC-2024-0892",
    pushTime: "2024-11-15 11:15:23",
    status: "success",
    message: "推送成功",
  },
  {
    id: "2",
    voucherNo: "PZ-2024-11-0002",
    ncVoucherNo: "",
    pushTime: "2024-11-15 10:30:45",
    status: "failed",
    message: "NC系统返回错误：凭证日期不在当前会计期间",
  },
  {
    id: "3",
    voucherNo: "PZ-2024-11-0003",
    ncVoucherNo: "NC-2024-0891",
    pushTime: "2024-11-14 16:45:12",
    status: "success",
    message: "推送成功",
  },
  {
    id: "4",
    voucherNo: "PZ-2024-11-0004",
    ncVoucherNo: "",
    pushTime: "2024-11-14 15:20:33",
    status: "pending",
    message: "等待NC系统响应",
  },
  {
    id: "5",
    voucherNo: "PZ-2024-11-0005",
    ncVoucherNo: "",
    pushTime: "2024-11-14 14:10:56",
    status: "failed",
    message: "网络连接超时，请重试",
  },
  {
    id: "6",
    voucherNo: "PZ-2024-11-0006",
    ncVoucherNo: "NC-2024-0890",
    pushTime: "2024-11-13 09:30:18",
    status: "success",
    message: "推送成功",
  },
]

const statusMap: Record<
  string,
  {
    label: string
    variant: "default" | "secondary" | "destructive" | "outline"
    icon?: React.ReactNode
  }
> = {
  success: {
    label: "成功",
    variant: "default" as const,
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  failed: {
    label: "失败",
    variant: "destructive" as const,
    icon: <XCircle className="h-3 w-3" />,
  },
  pending: {
    label: "等待中",
    variant: "secondary" as const,
    icon: <Clock className="h-3 w-3" />,
  },
}

export default function NCRecordsPage() {
  const [searchTerm, setSearchTerm] = useState("")

  const successCount = ncRecords.filter((r) => r.status === "success").length
  const failedCount = ncRecords.filter((r) => r.status === "failed").length

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/vouchers">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">NC对接记录</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            查看凭证推送NC系统的历史记录
          </p>
        </div>
      </div>

      {/* 统计概览 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-muted-foreground">总推送次数</p>
              <p className="text-2xl font-semibold">{ncRecords.length}</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <RefreshCw className="h-5 w-5 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-muted-foreground">成功</p>
              <p className="text-2xl font-semibold text-emerald-600">
                {successCount}
              </p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-muted-foreground">失败</p>
              <p className="text-2xl font-semibold text-destructive">
                {failedCount}
              </p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100">
              <XCircle className="h-5 w-5 text-destructive" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <CardTitle className="text-base font-medium">推送记录</CardTitle>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索凭证号"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-48 pl-9"
              />
            </div>
            <Select defaultValue="all">
              <SelectTrigger className="w-28">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="success">成功</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="pending">等待中</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>凭证号</TableHead>
                  <TableHead>NC凭证号</TableHead>
                  <TableHead>推送时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>返回信息</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ncRecords.map((record) => (
                  <TableRow key={record.id}>
                    <TableCell className="font-medium">
                      {record.voucherNo}
                    </TableCell>
                    <TableCell>
                      {record.ncVoucherNo ? (
                        <span className="text-primary">{record.ncVoucherNo}</span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>{record.pushTime}</TableCell>
                    <TableCell>
                      <Badge
                        variant={statusMap[record.status].variant}
                        className="gap-1"
                      >
                        {statusMap[record.status].icon}
                        {statusMap[record.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className={`max-w-64 truncate ${
                        record.status === "failed"
                          ? "text-destructive"
                          : "text-muted-foreground"
                      }`}
                    >
                      {record.message}
                    </TableCell>
                    <TableCell className="text-right">
                      {record.status === "failed" && (
                        <Button size="sm">
                          <RefreshCw className="mr-1 h-3 w-3" />
                          重试
                        </Button>
                      )}
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
