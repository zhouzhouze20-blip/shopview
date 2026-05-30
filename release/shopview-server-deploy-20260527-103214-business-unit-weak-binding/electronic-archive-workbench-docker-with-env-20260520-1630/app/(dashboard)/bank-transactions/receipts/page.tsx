"use client"

import { useState } from "react"
import { ArrowLeft, Upload, Check, Eye, FileImage } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import Link from "next/link"

const pendingReceipts = [
  {
    id: "1",
    transDate: "2024-11-14",
    bankAccount: "6222****8899",
    counterparty: "上海贸易集团",
    amount: 135600.0,
    type: "expense",
    hasReceipt: false,
  },
  {
    id: "2",
    transDate: "2024-11-12",
    bankAccount: "6222****7788",
    counterparty: "杭州物流有限公司",
    amount: 36160.0,
    type: "expense",
    hasReceipt: false,
  },
  {
    id: "3",
    transDate: "2024-11-11",
    bankAccount: "6222****8899",
    counterparty: "北京咨询公司",
    amount: 50000.0,
    type: "expense",
    hasReceipt: true,
  },
  {
    id: "4",
    transDate: "2024-11-10",
    bankAccount: "6222****8899",
    counterparty: "广州客户有限公司",
    amount: 258000.0,
    type: "income",
    hasReceipt: true,
  },
]

export default function BankReceiptsPage() {
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const toggleOne = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  const pendingCount = pendingReceipts.filter((r) => r.hasReceipt).length

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/bank-transactions">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">回单归档</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            上传银行回单并确认归档
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div className="flex items-center gap-4">
            <CardTitle className="text-base font-medium">回单列表</CardTitle>
            <Badge variant="secondary">
              {pendingCount} 份待归档
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline">
              <Upload className="mr-2 h-4 w-4" />
              批量上传回单
            </Button>
            <Button disabled={selectedIds.length === 0}>
              <Check className="mr-2 h-4 w-4" />
              批量归档 ({selectedIds.length})
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={
                        selectedIds.length ===
                        pendingReceipts.filter((r) => r.hasReceipt).length
                      }
                      onCheckedChange={() => {
                        const withReceipts = pendingReceipts
                          .filter((r) => r.hasReceipt)
                          .map((r) => r.id)
                        if (selectedIds.length === withReceipts.length) {
                          setSelectedIds([])
                        } else {
                          setSelectedIds(withReceipts)
                        }
                      }}
                    />
                  </TableHead>
                  <TableHead>交易日期</TableHead>
                  <TableHead>银行账号</TableHead>
                  <TableHead>对方户名</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>回单状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pendingReceipts.map((receipt) => (
                  <TableRow key={receipt.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.includes(receipt.id)}
                        onCheckedChange={() => toggleOne(receipt.id)}
                        disabled={!receipt.hasReceipt}
                      />
                    </TableCell>
                    <TableCell>{receipt.transDate}</TableCell>
                    <TableCell className="font-medium">
                      {receipt.bankAccount}
                    </TableCell>
                    <TableCell>{receipt.counterparty}</TableCell>
                    <TableCell
                      className={`text-right font-medium ${
                        receipt.type === "income"
                          ? "text-emerald-600"
                          : "text-destructive"
                      }`}
                    >
                      {receipt.type === "income" ? "+" : "-"}¥
                      {receipt.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {receipt.hasReceipt ? (
                        <Badge variant="default">已上传</Badge>
                      ) : (
                        <Badge variant="secondary">待上传</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {receipt.hasReceipt ? (
                          <>
                            <Button size="sm" variant="outline">
                              <Eye className="mr-1 h-3 w-3" />
                              预览
                            </Button>
                            <Button size="sm">
                              <Check className="mr-1 h-3 w-3" />
                              归档
                            </Button>
                          </>
                        ) : (
                          <Button size="sm" variant="outline">
                            <Upload className="mr-1 h-3 w-3" />
                            上传
                          </Button>
                        )}
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
