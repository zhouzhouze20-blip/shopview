"use client"

import { useState } from "react"
import { ArrowLeft, Search, Filter, Eye, Link2, FileCheck } from "lucide-react"
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

const contracts = [
  {
    id: "1",
    docType: "采购合同",
    docNo: "CT-2024-0123",
    partner: "成都制造有限公司",
    signDate: "2024-10-15",
    startDate: "2024-11-01",
    endDate: "2025-10-31",
    amount: 500000.0,
    executedAmount: 350000.0,
    linkedInvoices: 3,
    status: "executing",
  },
  {
    id: "2",
    docType: "服务合同",
    docNo: "CT-2024-0124",
    partner: "北京咨询公司",
    signDate: "2024-09-20",
    startDate: "2024-10-01",
    endDate: "2025-03-31",
    amount: 200000.0,
    executedAmount: 100000.0,
    linkedInvoices: 2,
    status: "executing",
  },
  {
    id: "3",
    docType: "销售合同",
    docNo: "CT-2024-0125",
    partner: "广州客户有限公司",
    signDate: "2024-11-01",
    startDate: "2024-11-15",
    endDate: "2025-11-14",
    amount: 800000.0,
    executedAmount: 258000.0,
    linkedInvoices: 1,
    status: "executing",
  },
  {
    id: "4",
    docType: "结算单",
    docNo: "ST-2024-0056",
    partner: "深圳市科技有限公司",
    signDate: "2024-11-10",
    startDate: "-",
    endDate: "-",
    amount: 96050.0,
    executedAmount: 96050.0,
    linkedInvoices: 1,
    status: "completed",
  },
]

const statusMap: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  executing: { label: "执行中", variant: "default" as const },
  completed: { label: "已完成", variant: "secondary" as const },
  pending: { label: "待执行", variant: "outline" as const },
}

export default function ContractsPage() {
  const [searchTerm, setSearchTerm] = useState("")

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/documents">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">合同/结算单</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            查看和管理合同及结算单据
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <CardTitle className="text-base font-medium">合同/结算单列表</CardTitle>
              <Badge variant="secondary">{contracts.length} 条记录</Badge>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索合同号/单位名称"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-64 pl-9"
                />
              </div>
              <Select defaultValue="all">
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="合同类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="purchase">采购合同</SelectItem>
                  <SelectItem value="sales">销售合同</SelectItem>
                  <SelectItem value="service">服务合同</SelectItem>
                  <SelectItem value="settlement">结算单</SelectItem>
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
                  <TableHead>类型</TableHead>
                  <TableHead>合同/单据编号</TableHead>
                  <TableHead>对方单位</TableHead>
                  <TableHead>签订日期</TableHead>
                  <TableHead>有效期</TableHead>
                  <TableHead className="text-right">合同金额</TableHead>
                  <TableHead className="text-right">已执行金额</TableHead>
                  <TableHead className="text-center">关联发票</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contracts.map((contract) => (
                  <TableRow key={contract.id}>
                    <TableCell>
                      <Badge variant="outline">{contract.docType}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{contract.docNo}</TableCell>
                    <TableCell className="max-w-32 truncate">
                      {contract.partner}
                    </TableCell>
                    <TableCell>{contract.signDate}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {contract.startDate === "-"
                        ? "-"
                        : `${contract.startDate} 至 ${contract.endDate}`}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      ¥{contract.amount.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      ¥{contract.executedAmount.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-center">
                      {contract.linkedInvoices > 0 ? (
                        <Badge variant="default">{contract.linkedInvoices}</Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusMap[contract.status].variant}>
                        {statusMap[contract.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline">
                          <Eye className="mr-1 h-3 w-3" />
                          详情
                        </Button>
                        <Button size="sm" variant="outline">
                          <Link2 className="mr-1 h-3 w-3" />
                          关联
                        </Button>
                      </div>
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
