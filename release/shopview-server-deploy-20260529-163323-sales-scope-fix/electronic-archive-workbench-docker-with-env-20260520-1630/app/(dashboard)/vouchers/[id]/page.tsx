"use client"

import {
  ArrowLeft,
  FileText,
  Landmark,
  FileStack,
  Receipt,
  BookCheck,
  Hash,
  CheckCircle2,
  Send,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import Link from "next/link"

interface TimelineItem {
  id: string
  type:
    | "document"
    | "invoice"
    | "transaction"
    | "receipt"
    | "voucher"
    | "nc"
  title: string
  description: string
  date: string
  status: "completed" | "current" | "pending"
  details?: Record<string, string>
}

const archiveDetail = {
  archiveNo: "AR-2024-0001",
  voucherNo: "PZ-2024-11-0001",
  ncVoucherNo: "NC-2024-0892",
  businessDate: "2024-11-15",
  amount: 96050.0,
  pushStatus: "success",
}

const timeline: TimelineItem[] = [
  {
    id: "1",
    type: "document",
    title: "业务单据",
    description: "采购订单 PO-2024-0892",
    date: "2024-11-10 09:30",
    status: "completed",
    details: {
      单据类型: "采购订单",
      单据编号: "PO-2024-0892",
      供应商: "深圳市科技有限公司",
      金额: "¥96,050.00",
    },
  },
  {
    id: "2",
    type: "invoice",
    title: "发票",
    description: "增值税专用发票 44032024110001",
    date: "2024-11-12 14:20",
    status: "completed",
    details: {
      发票号码: "44032024110001",
      发票类型: "增值税专用发票",
      销方名称: "深圳市科技有限公司",
      金额: "¥85,000.00",
      税额: "¥11,050.00",
      价税合计: "¥96,050.00",
    },
  },
  {
    id: "3",
    type: "transaction",
    title: "银行流水",
    description: "工商银行 6222****8899 支付",
    date: "2024-11-15 10:15",
    status: "completed",
    details: {
      交易日期: "2024-11-15",
      银行账号: "6222****8899",
      对方户名: "深圳市科技有限公司",
      摘要: "货款支付",
      支出金额: "¥96,050.00",
    },
  },
  {
    id: "4",
    type: "receipt",
    title: "银行回单",
    description: "电子回单已归档",
    date: "2024-11-15 10:30",
    status: "completed",
    details: {
      回单类型: "电子回单",
      归档状态: "已归档",
      归档时间: "2024-11-15 10:30",
    },
  },
  {
    id: "5",
    type: "voucher",
    title: "记账凭证",
    description: "凭证号 PZ-2024-11-0001",
    date: "2024-11-15 11:00",
    status: "completed",
    details: {
      凭证号: "PZ-2024-11-0001",
      凭证日期: "2024-11-15",
      摘要: "支付货款",
      借方科目: "应付账款",
      贷方科目: "银行存款",
      金额: "¥96,050.00",
    },
  },
  {
    id: "6",
    type: "nc",
    title: "NC凭证号",
    description: "已推送至NC系统",
    date: "2024-11-15 11:15",
    status: "completed",
    details: {
      NC凭证号: "NC-2024-0892",
      推送状态: "成功",
      推送时间: "2024-11-15 11:15",
    },
  },
]

const typeIcon = {
  document: <FileStack className="h-5 w-5" />,
  invoice: <FileText className="h-5 w-5" />,
  transaction: <Landmark className="h-5 w-5" />,
  receipt: <Receipt className="h-5 w-5" />,
  voucher: <BookCheck className="h-5 w-5" />,
  nc: <Hash className="h-5 w-5" />,
}

const typeColor = {
  document: "bg-blue-100 text-blue-600",
  invoice: "bg-amber-100 text-amber-600",
  transaction: "bg-emerald-100 text-emerald-600",
  receipt: "bg-purple-100 text-purple-600",
  voucher: "bg-pink-100 text-pink-600",
  nc: "bg-cyan-100 text-cyan-600",
}

export default function VoucherDetailPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/vouchers">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h2 className="text-2xl font-semibold text-foreground">
            档案详情 - {archiveDetail.archiveNo}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            查看完整的档案包信息和业务流转时间线
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <FileText className="mr-2 h-4 w-4" />
            预览档案包
          </Button>
          <Button>
            <Send className="mr-2 h-4 w-4" />
            重新推送
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 档案基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">档案编号</span>
              <span className="text-sm font-medium">
                {archiveDetail.archiveNo}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">凭证号</span>
              <span className="text-sm font-medium">
                {archiveDetail.voucherNo}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">NC凭证号</span>
              <span className="text-sm font-medium text-primary">
                {archiveDetail.ncVoucherNo}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">业务日期</span>
              <span className="text-sm">{archiveDetail.businessDate}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">金额</span>
              <span className="text-lg font-semibold">
                ¥{archiveDetail.amount.toLocaleString()}
              </span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-sm text-muted-foreground">推送状态</span>
              <Badge variant="default" className="gap-1">
                <CheckCircle2 className="h-3 w-3" />
                已推送
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* 业务流转时间线 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base font-medium">
              业务流转时间线
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative space-y-6 pl-8">
              {/* 时间线连接线 */}
              <div className="absolute bottom-0 left-[15px] top-0 w-0.5 bg-border" />

              {timeline.map((item, index) => (
                <div key={item.id} className="relative">
                  {/* 时间线圆点 */}
                  <div
                    className={`absolute -left-8 flex h-8 w-8 items-center justify-center rounded-full ${
                      typeColor[item.type]
                    }`}
                  >
                    {typeIcon[item.type]}
                  </div>

                  {/* 内容 */}
                  <div className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium">{item.title}</h4>
                        <p className="text-sm text-muted-foreground">
                          {item.description}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {item.date}
                        </span>
                        {item.status === "completed" && (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        )}
                      </div>
                    </div>

                    {item.details && (
                      <div className="mt-3 grid gap-2 rounded-md bg-muted p-3">
                        {Object.entries(item.details).map(([key, value]) => (
                          <div
                            key={key}
                            className="flex justify-between text-sm"
                          >
                            <span className="text-muted-foreground">{key}</span>
                            <span className="font-medium">{value}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
