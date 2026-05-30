"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  Download,
  FileText,
  Calendar,
  Store,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { Checkbox } from "@/components/ui/checkbox"

const archives = [
  {
    id: "AR20240115001",
    storeName: "城西旗舰店",
    storeId: "ST001",
    archiveType: "日结档案",
    period: "2024-01-15",
    invoiceCount: 45,
    transactionCount: 38,
    amount: 125600,
    status: "已归档",
    createdAt: "2024-01-15 23:30",
  },
  {
    id: "AR20240115002",
    storeName: "滨江购物中心店",
    storeId: "ST002",
    archiveType: "日结档案",
    period: "2024-01-15",
    invoiceCount: 32,
    transactionCount: 28,
    amount: 89200,
    status: "已归档",
    createdAt: "2024-01-15 23:35",
  },
  {
    id: "AR20240114001",
    storeName: "城西旗舰店",
    storeId: "ST001",
    archiveType: "日结档案",
    period: "2024-01-14",
    invoiceCount: 52,
    transactionCount: 45,
    amount: 156800,
    status: "已归档",
    createdAt: "2024-01-14 23:30",
  },
  {
    id: "AR20240115003",
    storeName: "南京新街口店",
    storeId: "ST003",
    archiveType: "日结档案",
    period: "2024-01-15",
    invoiceCount: 68,
    transactionCount: 55,
    amount: 198500,
    status: "待审核",
    createdAt: "2024-01-15 23:40",
  },
  {
    id: "AR20240101M01",
    storeName: "城西旗舰店",
    storeId: "ST001",
    archiveType: "月结档案",
    period: "2024-01",
    invoiceCount: 1256,
    transactionCount: 1089,
    amount: 3256000,
    status: "已归档",
    createdAt: "2024-02-01 10:00",
  },
]

export default function StoresArchivesPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [storeFilter, setStoreFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [selectedRows, setSelectedRows] = useState<string[]>([])

  const filteredArchives = archives.filter((archive) => {
    const matchesSearch =
      archive.id.includes(searchTerm) ||
      archive.storeName.includes(searchTerm)
    const matchesStore = storeFilter === "all" || archive.storeId === storeFilter
    const matchesType = typeFilter === "all" || archive.archiveType === typeFilter
    return matchesSearch && matchesStore && matchesType
  })

  const toggleSelectAll = () => {
    if (selectedRows.length === filteredArchives.length) {
      setSelectedRows([])
    } else {
      setSelectedRows(filteredArchives.map((a) => a.id))
    }
  }

  const toggleSelectRow = (id: string) => {
    setSelectedRows((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">门店档案</h1>
          <p className="text-sm text-muted-foreground">查看和管理各门店的归档记录</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            批量导出
          </Button>
        </div>
      </div>

      {/* 筛选区 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索档案编号、门店名称..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={storeFilter} onValueChange={setStoreFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="选择门店" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部门店</SelectItem>
                <SelectItem value="ST001">城西旗舰店</SelectItem>
                <SelectItem value="ST002">滨江购物中心店</SelectItem>
                <SelectItem value="ST003">南京新街口店</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="档案类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="日结档案">日结档案</SelectItem>
                <SelectItem value="月结档案">月结档案</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 档案表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]">
                  <Checkbox
                    checked={
                      selectedRows.length === filteredArchives.length &&
                      filteredArchives.length > 0
                    }
                    onCheckedChange={toggleSelectAll}
                  />
                </TableHead>
                <TableHead>档案编号</TableHead>
                <TableHead>门店</TableHead>
                <TableHead>档案类型</TableHead>
                <TableHead>归档周期</TableHead>
                <TableHead className="text-right">发票数</TableHead>
                <TableHead className="text-right">流水数</TableHead>
                <TableHead className="text-right">金额</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredArchives.map((archive) => (
                <TableRow key={archive.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedRows.includes(archive.id)}
                      onCheckedChange={() => toggleSelectRow(archive.id)}
                    />
                  </TableCell>
                  <TableCell className="font-mono text-sm">{archive.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Store className="h-3.5 w-3.5 text-muted-foreground" />
                      {archive.storeName}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{archive.archiveType}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                      {archive.period}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{archive.invoiceCount}</TableCell>
                  <TableCell className="text-right">{archive.transactionCount}</TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{(archive.amount / 10000).toFixed(2)}万
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={archive.status === "已归档" ? "default" : "secondary"}
                    >
                      {archive.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {archive.createdAt}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
