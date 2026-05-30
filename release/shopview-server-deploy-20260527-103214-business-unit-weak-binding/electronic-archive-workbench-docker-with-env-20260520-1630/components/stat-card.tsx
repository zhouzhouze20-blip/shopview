import { cn } from "@/lib/utils"

interface StatCardProps {
  title: string
  value: number | string
  suffix?: string
  icon: React.ReactNode
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
  variant?: "default" | "warning" | "success" | "error"
}

const variantStyles = {
  default: "bg-card border-border",
  warning: "bg-amber-50 border-amber-200",
  success: "bg-emerald-50 border-emerald-200",
  error: "bg-red-50 border-red-200",
}

const iconStyles = {
  default: "bg-primary/10 text-primary",
  warning: "bg-amber-100 text-amber-600",
  success: "bg-emerald-100 text-emerald-600",
  error: "bg-red-100 text-red-600",
}

export function StatCard({
  title,
  value,
  suffix,
  icon,
  trend,
  className,
  variant = "default",
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-shadow hover:shadow-sm",
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-foreground">
            {value}
            {suffix && (
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                {suffix}
              </span>
            )}
          </p>
          {trend && (
            <p
              className={cn(
                "mt-1 text-xs",
                trend.isPositive ? "text-emerald-600" : "text-red-600"
              )}
            >
              {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-lg",
            iconStyles[variant]
          )}
        >
          {icon}
        </div>
      </div>
    </div>
  )
}
