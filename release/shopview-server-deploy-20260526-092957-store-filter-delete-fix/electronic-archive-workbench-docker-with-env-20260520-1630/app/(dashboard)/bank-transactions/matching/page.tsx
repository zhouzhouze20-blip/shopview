"use client"

import { useState } from "react"
import { ArrowLeft, Search, Check, Link2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import Link from "next/link"

const pendingTransactions = [
  {
    id: "1",
    transDate: "2024-11-14",
    bankAccount: "6222****8899",
    counterparty: "上海贸易集团",
    summary: "采购预付款",
    amount: 135600.0,
    type: "expense",
  },
  {
    id: "2",
    transDate: "2024-11-12",
    bankAccount: "6222****7788",
    counterparty: "杭州物流有限公司",
    summary: "运费支付",
    amount: 36160.0,
    type: "expense",
  },
  {
    id: "3",
    transDate: "2024-11-11",
    bankAccount: "6222****8899",
    counterparty: "北京咨询公司",
    summary: "咨询服务费",
    amount: 50000.0,
    type: "expense",
  },
]

const candidateInvoices = [
  {
    id: "1",
    invoiceNo: "44032024110002",
    sellerName: "上海贸易集团",
    amount: 135600.0,
    invoiceDate: "2024-11-14",
  },
  {
    id: "2",
    invoiceNo: "44032024110015",
    sellerName: "上海贸易集团",
    amount: 85000.0,
    invoiceDate: "2024-11-10",
  },
]

const candidateDocuments = [
  {
    id: "1",
    docNo: "PO-2024-0893",
    docType: "采购订单",
    supplier: "上海贸易集团",
    amount: 135600.0,
    date: "2024-11-12",
  },
  {
    id: "2",
    docNo: "PO-2024-0894",
    docType: "采购订单",
    supplier: "上海贸易集团",
    amount: 50600.0,
    date: "2024-11-10",
  },
]

export default function BankMatchingPage() {
  const [selectedTransaction, setSelectedTransaction] = useState<string | null>(
    pendingTransactions[0]?.id || null
  )
  const [selectedInvoice, setSelectedInvoice] = useState<string>("")
  const [selectedDoc, setSelectedDoc] = useState<string>("")

  const currentTransaction = pendingTransactions.find(
    (t) => t.id === selectedTransaction
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/bank-transactions">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h2 className="text-2xl font-semibold text-foreground">流水匹配</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            为银行流水匹配对应的发票和业务单据
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 左侧：待匹配流水 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-base font-medium">待匹配流水</CardTitle>
            <Badge variant="secondary">
              {pendingTransactions.length} 笔待匹配
            </Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {pendingTransactions.map((trans) => (
              <div
                key={trans.id}
                onClick={() => setSelectedTransaction(trans.id)}
                className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                  selectedTransaction === trans.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:bg-accent"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <p className="font-medium">{trans.counterparty}</p>
                    <p className="text-sm text-muted-foreground">
                      {trans.summary}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {trans.transDate} · {trans.bankAccount}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-lg font-semibold ${
                        trans.type === "income"
                          ? "text-emerald-600"
                          : "text-destructive"
                      }`}
                    >
                      {trans.type === "income" ? "+" : "-"}¥
                      {trans.amount.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* 右侧：匹配选择 */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base font-medium">
              匹配 {currentTransaction?.counterparty || ""}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="invoices">
              <TabsList className="w-full">
                <TabsTrigger value="invoices" className="flex-1">
                  匹配发票
                </TabsTrigger>
                <TabsTrigger value="documents" className="flex-1">
                  匹配单据
                </TabsTrigger>
              </TabsList>

              <TabsContent value="invoices" className="mt-4 space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="搜索发票" className="pl-9" />
                </div>

                <div className="space-y-2">
                  {candidateInvoices.map((inv) => (
                    <div
                      key={inv.id}
                      className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                        selectedInvoice === inv.id
                          ? "border-primary bg-primary/5"
                          : "border-border"
                      }`}
                    >
                      <Checkbox
                        checked={selectedInvoice === inv.id}
                        onCheckedChange={() =>
                          setSelectedInvoice(
                            selectedInvoice === inv.id ? "" : inv.id
                          )
                        }
                      />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{inv.invoiceNo}</p>
                        <p className="text-xs text-muted-foreground">
                          {inv.sellerName} · {inv.invoiceDate}
                        </p>
                      </div>
                      <p className="font-medium">
                        ¥{inv.amount.toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>

                <Button
                  className="w-full"
                  disabled={!selectedInvoice}
                >
                  <Link2 className="mr-2 h-4 w-4" />
                  确认匹配发票
                </Button>
              </TabsContent>

              <TabsContent value="documents" className="mt-4 space-y-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="搜索单据" className="pl-9" />
                </div>

                <div className="space-y-2">
                  {candidateDocuments.map((doc) => (
                    <div
                      key={doc.id}
                      className={`flex items-center gap-3 rounded-lg border p-3 transition-colors ${
                        selectedDoc === doc.id
                          ? "border-primary bg-primary/5"
                          : "border-border"
                      }`}
                    >
                      <Checkbox
                        checked={selectedDoc === doc.id}
                        onCheckedChange={() =>
                          setSelectedDoc(selectedDoc === doc.id ? "" : doc.id)
                        }
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{doc.docNo}</p>
                          <Badge variant="outline" className="text-xs">
                            {doc.docType}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {doc.supplier} · {doc.date}
                        </p>
                      </div>
                      <p className="font-medium">
                        ¥{doc.amount.toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>

                <Button className="w-full" disabled={!selectedDoc}>
                  <Check className="mr-2 h-4 w-4" />
                  确认匹配单据
                </Button>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
