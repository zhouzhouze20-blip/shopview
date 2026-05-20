"use client"

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

type DashboardSummaryChartProps = {
  data: {
    month: string
    matchedPending: number
    amountMismatch: number
    unmatched: number
    confirmed: number
    paymentBills: number
  }[]
}

const chartConfig = {
  matchedPending: {
    label: "待确认",
    color: "hsl(38 92% 50%)",
  },
  amountMismatch: {
    label: "金额不一致",
    color: "hsl(0 72% 51%)",
  },
  unmatched: {
    label: "未匹配",
    color: "hsl(217 91% 60%)",
  },
  confirmed: {
    label: "已确认",
    color: "hsl(142 71% 45%)",
  },
  paymentBills: {
    label: "付款单",
    color: "hsl(173 58% 39%)",
  },
} satisfies ChartConfig

export function DashboardSummaryChart({ data }: DashboardSummaryChartProps) {
  return (
    <ChartContainer config={chartConfig} className="h-[320px] w-full">
      <LineChart data={data} margin={{ top: 16, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="month"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          interval={0}
        />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
        <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Line
          dataKey="matchedPending"
          type="monotone"
          stroke="var(--color-matchedPending)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          dataKey="amountMismatch"
          type="monotone"
          stroke="var(--color-amountMismatch)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          dataKey="unmatched"
          type="monotone"
          stroke="var(--color-unmatched)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          dataKey="confirmed"
          type="monotone"
          stroke="var(--color-confirmed)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          dataKey="paymentBills"
          type="monotone"
          stroke="var(--color-paymentBills)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ChartContainer>
  )
}
