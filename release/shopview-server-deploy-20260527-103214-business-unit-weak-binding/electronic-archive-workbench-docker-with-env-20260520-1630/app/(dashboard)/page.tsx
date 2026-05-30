import {
  AlertTriangle,
  ArrowRight,
  BookCheck,
  CheckCircle2,
  Clock,
  FileStack,
  FileText,
  Landmark,
} from "lucide-react"
import Link from "next/link"
import { firstQueryString, getDashboardData } from "@/lib/etl-data"
import { QuerySelect } from "@/components/query-select"
import { DashboardSummaryChart } from "@/components/dashboard-summary-chart"
import { StatCard } from "@/components/stat-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const statusIcon = {
  success: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-500" />,
  info: <Clock className="h-4 w-4 text-blue-500" />,
}

const priorityBadge = {
  high: <Badge variant="destructive">紧急</Badge>,
  medium: <Badge variant="secondary">一般</Badge>,
  low: <Badge variant="outline">低</Badge>,
}

function yearMonthSelectOptions(monthsBack = 36) {
  const options: { value: string; label: string }[] = [
    { value: "all", label: "全部年月" },
  ]
  const start = new Date()
  for (let i = 0; i < monthsBack; i++) {
    const d = new Date(start.getFullYear(), start.getMonth() - i, 1)
    const y = d.getFullYear()
    const m = d.getMonth() + 1
    const value = `${y}-${String(m).padStart(2, "0")}`
    options.push({ value, label: `${y}年${m}月` })
  }
  return options
}

function withMonth(href: string, yearMonth?: string) {
  if (!yearMonth || yearMonth === "all") return href
  const separator = href.includes("?") ? "&" : "?"
  return `${href}${separator}yearMonth=${encodeURIComponent(yearMonth)}`
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ yearMonth?: string | string[] }>
}) {
  const raw = await searchParams
  const yearMonth = firstQueryString(raw.yearMonth)
  const data = await getDashboardData(yearMonth)
  const dashboardYear = new Date().getFullYear()
  const summaryChartData = [
    { name: "待确认", value: data.stats.matchedPending, fill: "hsl(38 92% 50%)" },
    { name: "金额不一致", value: data.stats.amountMismatch, fill: "hsl(0 72% 51%)" },
    { name: "未匹配", value: data.stats.unmatched, fill: "hsl(217 91% 60%)" },
    { name: "已确认", value: data.stats.confirmed, fill: "hsl(142 71% 45%)" },
    { name: "付款单", value: data.stats.paymentBills, fill: "hsl(173 58% 39%)" },
  ]
  void summaryChartData
  const stats = [
    {
      title: "待确认发票",
      value: data.stats.matchedPending,
      icon: <FileText className="h-5 w-5" />,
      variant: "warning" as const,
      href: withMonth("/invoices/matched", yearMonth),
    },
    {
      title: "金额不一致",
      value: data.stats.amountMismatch,
      icon: <AlertTriangle className="h-5 w-5" />,
      variant: "error" as const,
      href: withMonth("/invoices/amount-mismatch", yearMonth),
    },
    {
      title: "未匹配发票",
      value: data.stats.unmatched,
      icon: <Landmark className="h-5 w-5" />,
      variant: "default" as const,
      href: withMonth("/invoices/unmatched", yearMonth),
    },
    {
      title: "付款单",
      value: data.stats.paymentBills,
      icon: <BookCheck className="h-5 w-5" />,
      variant: "success" as const,
      href: withMonth("/documents", yearMonth),
    },
  ]
  stats.splice(3, 0, {
    title: "已确认发票",
    value: data.stats.confirmed,
    icon: <CheckCircle2 className="h-5 w-5" />,
    variant: "success" as const,
    href: withMonth("/invoices/confirmed-report", yearMonth),
  })
  const pendingTasks = [
    {
      id: 1,
      title: "确认已匹配发票",
      count: data.stats.matchedPending,
      priority: "high" as const,
      href: withMonth("/invoices/matched", yearMonth),
    },
    {
      id: 2,
      title: "处理金额差异",
      count: data.stats.amountMismatch,
      priority: "high" as const,
      href: withMonth("/invoices/amount-mismatch", yearMonth),
    },
    {
      id: 3,
      title: "处理未匹配发票",
      count: data.stats.unmatched,
      priority: "medium" as const,
      href: withMonth("/invoices/unmatched", yearMonth),
    },
    {
      id: 4,
      title: "查看付款单",
      count: data.stats.paymentBills,
      priority: "low" as const,
      href: withMonth("/documents", yearMonth),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">工作台</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            当前概览来自 Oracle ETLKP 用户下的发票、匹配记录和付款单数据，支持按月查看。
          </p>
        </div>
        <QuerySelect
          name="yearMonth"
          value={yearMonth ?? "all"}
          placeholder="业务年月"
          className="w-[8rem]"
          options={yearMonthSelectOptions()}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {stats.map((stat) => (
          <Link key={stat.title} href={stat.href}>
            <StatCard
              title={stat.title}
              value={stat.value}
              icon={stat.icon}
              variant={stat.variant}
              className="cursor-pointer"
            />
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium">{dashboardYear}年汇总数据图表</CardTitle>
        </CardHeader>
        <CardContent>
          <DashboardSummaryChart data={data.monthlySummary} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-medium">待办任务</CardTitle>
            <Badge variant="secondary">{pendingTasks.length} 项</Badge>
          </CardHeader>
          <CardContent className="space-y-3">
            {pendingTasks.map((task) => (
              <Link
                key={task.id}
                href={task.href}
                className="flex items-center justify-between rounded-lg border border-border p-3 transition-colors hover:bg-accent"
              >
                <div className="flex items-center gap-3">
                  {priorityBadge[task.priority]}
                  <span className="text-sm font-medium">{task.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    {task.count} 条
                  </span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base font-medium">最近匹配</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link href={withMonth("/invoices/matched", yearMonth)}>查看全部</Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {data.recentActivities.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  暂无最近匹配记录
                </div>
              ) : (
                data.recentActivities.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start gap-3 border-b border-border pb-3 last:border-0 last:pb-0"
                  >
                    <div className="mt-0.5">{statusIcon[activity.status]}</div>
                    <div className="flex-1 space-y-1">
                      <p className="text-sm font-medium text-foreground">
                        {activity.action}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {activity.detail}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {activity.time}
                    </span>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">快捷操作</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Link href="/invoices">
              <Button variant="outline" className="h-auto w-full flex-col gap-2 py-4">
                <FileText className="h-6 w-6 text-primary" />
                <span>发票管理</span>
              </Button>
            </Link>
            <Link href="/invoices/unmatched">
              <Button variant="outline" className="h-auto w-full flex-col gap-2 py-4">
                <Landmark className="h-6 w-6 text-primary" />
                <span>未匹配发票</span>
              </Button>
            </Link>
            <Link href="/documents">
              <Button variant="outline" className="h-auto w-full flex-col gap-2 py-4">
                <FileStack className="h-6 w-6 text-primary" />
                <span>付款单</span>
              </Button>
            </Link>
            <Link href="/vouchers">
              <Button variant="outline" className="h-auto w-full flex-col gap-2 py-4">
                <BookCheck className="h-6 w-6 text-primary" />
                <span>凭证档案</span>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
