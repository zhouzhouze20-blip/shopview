"use client"

import { useState } from "react"
import {
  Landmark,
  Search,
  Filter,
  MoreHorizontal,
  FileText,
  Upload,
  Archive,
  Link2,
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

const stats = [
  {
    title: "待匹配流水",
    value: 56,
    icon: <Link2 className="h-5 w-5" />,
    variant: "warning" as const,
  },
  {
    title: "待归档回单",
    value: 38,
    icon: <Archive className="h-5 w-5" />,
    variant: "default" as const,
  },
  {
    title: "异常流水",
    value: 8,
    icon: <Landmark className="h-5 w-5" />,
    variant: "error" as const,
  },
  {
    title: "已完成",
    value: 1245,
    icon: <FileText className="h-5 w-5" />,
    variant: "success" as const,
  },
]

const transactions = [
  {
    id: "1",
    transDate: "2024-11-15",
    bankAccount: "6222****8899",
    counterparty: "深圳市科技有限公司",
    summary: "货款支付",
    income: 0,
    expense: 96050.0,
    matchedInvoice: "44032024110001",
    matchedDoc: "PO-2024-0892",
    receiptStatus: "uploaded",
    archiveStatus: "pending",
  },
  {
    id: "2",
    transDate: "2024-11-14",
    bankAccount: "6222****8899",
    counterparty: "上海贸易集团",
    summary: "采购预付款",
    income: 0,
    expense: 135600.0,
    matchedInvoice: "",
    matchedDoc: "PO-2024-0893",
    receiptStatus: "pending",
    archiveStatus: "pending",
  },
  {
    id: "3",
    transDate: "2024-11-13",
    bankAccount: "6222****8899",
    counterparty: "广州客户有限公司",
    summary: "销售回款",
    income: 258000.0,
    expense: 0,
    matchedInvoice: "44032024100089",
    matchedDoc: "SO-2024-0456",
    receiptStatus: "uploaded",
    archiveStatus: "archived",
  },
  {
    id: "4",
    transDate: "2024-11-12",
    bankAccount: "6222****7788",
    counterparty: "杭州物流有限公司",
    summary: "运费支付",
    income: 0,
    expense: 36160.0,
    matchedInvoice: "44032024110004",
    matchedDoc: "",
    receiptStatus: "pending",
    archiveStatus: "pending",
  },
  {
    id: "5",
    transDate: "2024-11-11",
    bankAccount: "6222****8899",
    counterparty: "北京咨询公司",
    summary: "咨询服务费",
    income: 0,
    expense: 50000.0,
    matchedInvoice: "",
    matchedDoc: "",
    receiptStatus: "pending",
    archiveStatus: "pending",
  },
]

const receiptStatusMap: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  uploaded: { label: "已上传", variant: "default" as const },
  pending: { label: "待上传", variant: "secondary" as const },
}

const archiveStatusMap: Record<
  string,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  archived: { label: "已归档", variant: "default" as const },
  pending: { label: "待归档", variant: "secondary" as const },
}

export default function BankTransactionsPage() {
  const [searchTerm, setSearchTerm] = useState("")

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">银行流水</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          管理银行流水数据，匹配发票和业务单据，归档银行回单。
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

      {/* 流水列表 */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="text-base font-medium">流水列表</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="搜索对方户名/摘要"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-64 pl-9"
                />
              </div>
              <Select defaultValue="all">
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="回单状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="uploaded">已上传</SelectItem>
                  <SelectItem value="pending">待上传</SelectItem>
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
                  <TableHead>交易日期</TableHead>
                  <TableHead>银行账号</TableHead>
                  <TableHead>对方户名</TableHead>
                  <TableHead>摘要</TableHead>
                  <TableHead className="text-right">收入金额</TableHead>
                  <TableHead className="text-right">支出金额</TableHead>
                  <TableHead>匹配发票</TableHead>
                  <TableHead>匹配单据</TableHead>
                  <TableHead>回单状态</TableHead>
                  <TableHead>归档状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((trans) => (
                  <TableRow key={trans.id}>
                    <TableCell>{trans.transDate}</TableCell>
                    <TableCell className="font-medium">
                      {trans.bankAccount}
                    </TableCell>
                    <TableCell className="max-w-32 truncate">
                      {trans.counterparty}
                    </TableCell>
                    <TableCell>{trans.summary}</TableCell>
                    <TableCell className="text-right text-emerald-600">
                      {trans.income > 0
                        ? `¥${trans.income.toLocaleString()}`
                        : "-"}
                    </TableCell>
                    <TableCell className="text-right text-destructive">
                      {trans.expense > 0
                        ? `¥${trans.expense.toLocaleString()}`
                        : "-"}
                    </TableCell>
                    <TableCell>
                      {trans.matchedInvoice ? (
                        <span className="text-primary">
                          {trans.matchedInvoice}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">未匹配</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {trans.matchedDoc ? (
                        <span className="text-primary">{trans.matchedDoc}</span>
                      ) : (
                        <span className="text-muted-foreground">未匹配</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          receiptStatusMap[trans.receiptStatus].variant
                        }
                      >
                        {receiptStatusMap[trans.receiptStatus].label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          archiveStatusMap[trans.archiveStatus].variant
                        }
                      >
                        {archiveStatusMap[trans.archiveStatus].label}
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
                          <DropdownMenuItem>
                            <FileText className="mr-2 h-4 w-4" />
                            匹配发票
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Link2 className="mr-2 h-4 w-4" />
                            匹配单据
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Upload className="mr-2 h-4 w-4" />
                            上传回单
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Archive className="mr-2 h-4 w-4" />
                            确认归档
                          </DropdownMenuItem>
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
