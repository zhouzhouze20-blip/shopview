"use client"

import { ArrowLeft, AlertTriangle, Check, UserCog, Eye } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import Link from "next/link"

const exceptionTransactions = [
  {
    id: "1",
    transDate: "2024-11-15",
    bankAccount: "6222****8899",
    counterparty: "未知户名",
    summary: "转账",
    amount: 15000.0,
    type: "expense",
    exceptionType: "unknown_counterparty",
    exceptionDesc: "对方户名无法识别",
  },
  {
    id: "2",
    transDate: "2024-11-14",
    bankAccount: "6222****7788",
    counterparty: "深圳某公司",
    summary: "货款",
    amount: 98500.0,
    type: "expense",
    exceptionType: "duplicate",
    exceptionDesc: "疑似重复交易",
  },
  {
    id: "3",
    transDate: "2024-11-13",
    bankAccount: "6222****8899",
    counterparty: "个人账户",
    summary: "转账",
    amount: 5000.0,
    type: "expense",
    exceptionType: "personal_account",
    exceptionDesc: "转账至个人账户",
  },
  {
    id: "4",
    transDate: "2024-11-12",
    bankAccount: "6222****8899",
    counterparty: "广州贸易公司",
    summary: "退款",
    amount: 23000.0,
    type: "income",
    exceptionType: "refund",
    exceptionDesc: "退款交易需确认",
  },
]

const exceptionTypeMap = {
  unknown_counterparty: { label: "未知户名", variant: "destructive" as const },
  duplicate: { label: "疑似重复", variant: "secondary" as const },
  personal_account: { label: "个人账户", variant: "outline" as const },
  refund: { label: "退款确认", variant: "secondary" as const },
}

export default function BankExceptionsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/bank-transactions">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">异常流水</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            处理系统标记的异常银行流水
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-base font-medium">异常列表</CardTitle>
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              {exceptionTransactions.length} 笔异常
            </Badge>
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
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>异常类型</TableHead>
                  <TableHead>异常描述</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exceptionTransactions.map((trans) => (
                  <TableRow key={trans.id}>
                    <TableCell>{trans.transDate}</TableCell>
                    <TableCell className="font-medium">
                      {trans.bankAccount}
                    </TableCell>
                    <TableCell>{trans.counterparty}</TableCell>
                    <TableCell>{trans.summary}</TableCell>
                    <TableCell
                      className={`text-right font-medium ${
                        trans.type === "income"
                          ? "text-emerald-600"
                          : "text-destructive"
                      }`}
                    >
                      {trans.type === "income" ? "+" : "-"}¥
                      {trans.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          exceptionTypeMap[
                            trans.exceptionType as keyof typeof exceptionTypeMap
                          ].variant
                        }
                      >
                        {
                          exceptionTypeMap[
                            trans.exceptionType as keyof typeof exceptionTypeMap
                          ].label
                        }
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {trans.exceptionDesc}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline">
                          <Eye className="mr-1 h-3 w-3" />
                          详情
                        </Button>
                        <Button size="sm" variant="outline">
                          <UserCog className="mr-1 h-3 w-3" />
                          人工处理
                        </Button>
                        <Button size="sm">
                          <Check className="mr-1 h-3 w-3" />
                          确认正常
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
