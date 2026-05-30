"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  Download,
  FileText,
  Calendar,
  LayoutGrid,
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
    id: "SA20240115001",
    sectionName: "男装板块",
    sectionId: "SEC001",
    archiveType: "采购档案",
    period: "2024-01-15",
    orderCount: 28,
    supplierCount: 12,
    amount: 458000,
    status: "已归档",
    createdAt: "2024-01-15 18:30",
  },
  {
    id: "SA20240115002",
    sectionName: "女装板块",
    sectionId: "SEC002",
    archiveType: "采购档案",
    period: "2024-01-15",
    orderCount: 42,
    supplierCount: 18,
    amount: 685000,
    status: "已归档",
    createdAt: "2024-01-15 18:45",
  },
  {
    id: "SA20240115003",
    sectionName: "男装板块",
    sectionId: "SEC001",
    archiveType: "结算档案",
    period: "2024-01-15",
    orderCount: 35,
    supplierCount: 8,
    amount: 328000,
    status: "待审核",
    createdAt: "2024-01-15 17:00",
  },
  {
    id: "SA20240101M01",
    sectionName: "女装板块",
    sectionId: "SEC002",
    archiveType: "月度汇总",
    period: "2024-01",
    orderCount: 856,
    supplierCount: 68,
    amount: 12580000,
    status: "已归档",
    createdAt: "2024-02-01 10:00",
  },
  {
    id: "SA20240115004",
    sectionName: "运动板块",
    sectionId: "SEC004",
    archiveType: "采购档案",
    period: "2024-01-15",
    orderCount: 18,
    supplierCount: 6,
    amount: 256000,
    status: "已归档",
    createdAt: "2024-01-15 19:00",
  },
]

export default function SectionsArchivesPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [sectionFilter, setSectionFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [selectedRows, setSelectedRows] = useState<string[]>([])

  const filteredArchives = archives.filter((archive) => {
    const matchesSearch =
      archive.id.includes(searchTerm) ||
      archive.sectionName.includes(searchTerm)
    const matchesSection =
      sectionFilter === "all" || archive.sectionId === sectionFilter
    const matchesType = typeFilter === "all" || archive.archiveType === typeFilter
    return matchesSearch && matchesSection && matchesType
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
          <h1 className="text-2xl font-bold text-foreground">板块档案</h1>
          <p className="text-sm text-muted-foreground">查看和管理各板块的归档记录</p>
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
                placeholder="搜索档案编号、板块名称..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={sectionFilter} onValueChange={setSectionFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="选择板块" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部板块</SelectItem>
                <SelectItem value="SEC001">男装板块</SelectItem>
                <SelectItem value="SEC002">女装板块</SelectItem>
                <SelectItem value="SEC004">运动板块</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="档案类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="采购档案">采购档案</SelectItem>
                <SelectItem value="结算档案">结算档案</SelectItem>
                <SelectItem value="月度汇总">月度汇总</SelectItem>
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
                <TableHead>板块</TableHead>
                <TableHead>档案类型</TableHead>
                <TableHead>归档周期</TableHead>
                <TableHead className="text-right">订单数</TableHead>
                <TableHead className="text-right">供应商数</TableHead>
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
                      <LayoutGrid className="h-3.5 w-3.5 text-muted-foreground" />
                      {archive.sectionName}
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
                  <TableCell className="text-right">{archive.orderCount}</TableCell>
                  <TableCell className="text-right">{archive.supplierCount}</TableCell>
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
