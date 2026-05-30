"use client"

import { useState } from "react"
import {
  Search,
  Filter,
  Download,
  LayoutGrid,
  User,
  MoreHorizontal,
  Eye,
  Edit,
  FileText,
  TrendingUp,
  Package,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { StatCard } from "@/components/stat-card"

const sections = [
  {
    id: "SEC001",
    name: "男装板块",
    category: "成衣",
    brands: ["优衣库", "ZARA", "H&M"],
    manager: "陈刚",
    supplierCount: 45,
    skuCount: 12580,
    monthlyRevenue: 3256000,
    grossMargin: 42.5,
    status: "运营中",
    archiveCount: 856,
  },
  {
    id: "SEC002",
    name: "女装板块",
    category: "成衣",
    brands: ["ONLY", "VERO MODA", "太平鸟"],
    manager: "林芳",
    supplierCount: 68,
    skuCount: 18960,
    monthlyRevenue: 4580000,
    grossMargin: 45.2,
    status: "运营中",
    archiveCount: 1256,
  },
  {
    id: "SEC003",
    name: "童装板块",
    category: "成衣",
    brands: ["巴拉巴拉", "安奈儿", "小猪班纳"],
    manager: "王丽",
    supplierCount: 32,
    skuCount: 8560,
    monthlyRevenue: 1890000,
    grossMargin: 48.8,
    status: "运营中",
    archiveCount: 428,
  },
  {
    id: "SEC004",
    name: "运动板块",
    category: "运动户外",
    brands: ["Nike", "Adidas", "李宁"],
    manager: "张伟",
    supplierCount: 28,
    skuCount: 6890,
    monthlyRevenue: 2680000,
    grossMargin: 38.5,
    status: "运营中",
    archiveCount: 568,
  },
  {
    id: "SEC005",
    name: "鞋类板块",
    category: "鞋履",
    brands: ["百丽", "达芙妮", "红蜻蜓"],
    manager: "李明",
    supplierCount: 35,
    skuCount: 5680,
    monthlyRevenue: 1560000,
    grossMargin: 52.3,
    status: "调整中",
    archiveCount: 356,
  },
]

const statusColorMap: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  "运营中": "default",
  "调整中": "secondary",
  "暂停": "destructive",
}

export default function SectionsListPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("all")

  const filteredSections = sections.filter((section) => {
    const matchesSearch =
      section.name.includes(searchTerm) ||
      section.id.includes(searchTerm) ||
      section.brands.some((b) => b.includes(searchTerm))
    const matchesCategory =
      categoryFilter === "all" || section.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  const totalRevenue = sections.reduce((sum, s) => sum + s.monthlyRevenue, 0)
  const activeSections = sections.filter((s) => s.status === "运营中").length
  const totalSKU = sections.reduce((sum, s) => sum + s.skuCount, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">板块列表</h1>
          <p className="text-sm text-muted-foreground">管理服装事业部所有业务板块</p>
        </div>
        <Button>
          <Download className="mr-2 h-4 w-4" />
          导出板块数据
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          title="板块总数"
          value={sections.length}
          suffix="个"
          icon={<LayoutGrid className="h-4 w-4" />}
        />
        <StatCard
          title="正常运营"
          value={activeSections}
          suffix="个"
          icon={<LayoutGrid className="h-4 w-4" />}
        />
        <StatCard
          title="本月营收"
          value={`${(totalRevenue / 10000).toFixed(0)}万`}
          trend={{ value: 12.5, isPositive: true }}
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <StatCard
          title="SKU 总数"
          value={`${(totalSKU / 1000).toFixed(1)}K`}
          icon={<Package className="h-4 w-4" />}
        />
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
                placeholder="搜索板块编号、名称、品牌..."
                className="pl-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="选择品类" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部品类</SelectItem>
                <SelectItem value="成衣">成衣</SelectItem>
                <SelectItem value="运动户外">运动户外</SelectItem>
                <SelectItem value="鞋履">鞋履</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 板块表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">板块编号</TableHead>
                <TableHead>板块名称</TableHead>
                <TableHead>品类</TableHead>
                <TableHead>主要品牌</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead className="text-right">供应商</TableHead>
                <TableHead className="text-right">SKU数</TableHead>
                <TableHead className="text-right">本月营收</TableHead>
                <TableHead className="text-right">毛利率</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSections.map((section) => (
                <TableRow key={section.id}>
                  <TableCell className="font-mono text-sm">{section.id}</TableCell>
                  <TableCell className="font-medium">{section.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{section.category}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[180px]">
                    <div className="flex flex-wrap gap-1">
                      {section.brands.slice(0, 2).map((brand) => (
                        <span
                          key={brand}
                          className="text-xs bg-muted px-1.5 py-0.5 rounded"
                        >
                          {brand}
                        </span>
                      ))}
                      {section.brands.length > 2 && (
                        <span className="text-xs text-muted-foreground">
                          +{section.brands.length - 2}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 text-muted-foreground" />
                      {section.manager}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{section.supplierCount}</TableCell>
                  <TableCell className="text-right">
                    {section.skuCount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    ¥{(section.monthlyRevenue / 10000).toFixed(0)}万
                  </TableCell>
                  <TableCell className="text-right">
                    <span
                      className={
                        section.grossMargin >= 45
                          ? "text-green-600"
                          : section.grossMargin >= 40
                          ? "text-foreground"
                          : "text-amber-600"
                      }
                    >
                      {section.grossMargin}%
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusColorMap[section.status]}>
                      {section.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <Eye className="mr-2 h-4 w-4" />
                          查看详情
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Edit className="mr-2 h-4 w-4" />
                          编辑板块
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <FileText className="mr-2 h-4 w-4" />
                          查看档案
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
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
