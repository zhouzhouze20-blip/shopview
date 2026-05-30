"use client"

import { useState, useTransition } from "react"
import { useRouter } from "next/navigation"
import { Bell, LogOut, User } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

type AppHeaderProps = {
  currentUser?: {
    username: string
    displayName: string
    wecomUserId: string
    mobile?: string
    email?: string
    departmentName?: string
  }
}

export function AppHeader({ currentUser }: AppHeaderProps) {
  const router = useRouter()
  const [profileOpen, setProfileOpen] = useState(false)
  const [isLoggingOut, startLogoutTransition] = useTransition()
  const displayName = currentUser?.displayName || "未登录用户"
  const username = currentUser?.username || "-"
  const wecomUserId = currentUser?.wecomUserId || "-"
  const mobile = currentUser?.mobile || "-"
  const email = currentUser?.email || "-"
  const departmentName = currentUser?.departmentName || "-"

  function handleLogout() {
    startLogoutTransition(async () => {
      await fetch("/api/auth/logout", {
        method: "POST",
        cache: "no-store",
      })
      router.push("/login")
      router.refresh()
    })
  }

  return (
    <>
      <header className="col-start-2 row-start-1 flex h-14 min-w-0 items-center justify-between border-b border-border bg-background px-6">
        <div className="flex min-w-0 items-center gap-4">
          <h1 className="truncate text-lg font-medium text-foreground">
            电子档案管理系统
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <Badge className="absolute -right-1 -top-1 h-5 w-5 rounded-full p-0 text-xs">
                  3
                </Badge>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72">
              <div className="px-3 py-2 text-sm font-medium">消息通知</div>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
                <span className="font-medium">发票匹配完成</span>
                <span className="text-xs text-muted-foreground">
                  自动匹配完成，等待业务确认
                </span>
              </DropdownMenuItem>
              <DropdownMenuItem className="flex flex-col items-start gap-1 py-3">
                <span className="font-medium">金额差异提醒</span>
                <span className="text-xs text-muted-foreground">
                  存在金额不一致的业务单据
                </span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex min-w-0 items-center gap-2">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <User className="h-4 w-4" />
                </div>
                <span className="max-w-32 truncate text-sm font-medium" title={displayName}>
                  {displayName}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5 text-sm">
                <div className="truncate font-medium" title={displayName}>
                  {displayName}
                </div>
                <div className="truncate text-xs text-muted-foreground" title={username}>
                  {username}
                </div>
                {wecomUserId !== "-" ? (
                  <div className="truncate text-xs text-muted-foreground" title={wecomUserId}>
                    企微：{wecomUserId}
                  </div>
                ) : null}
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={(event) => {
                  event.preventDefault()
                  setProfileOpen(true)
                }}
              >
                <User className="mr-2 h-4 w-4" />
                个人信息
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                disabled={isLoggingOut}
                onSelect={(event) => {
                  event.preventDefault()
                  handleLogout()
                }}
              >
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>个人信息</DialogTitle>
            <DialogDescription>当前登录用户的基础账号信息</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <ProfileItem label="姓名" value={displayName} />
            <ProfileItem label="用户名" value={username} />
            <ProfileItem label="企微 UserID" value={wecomUserId} />
            <ProfileItem label="部门" value={departmentName} />
            <ProfileItem label="手机号" value={mobile} />
            <ProfileItem label="邮箱" value={email} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function ProfileItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] gap-3">
      <div className="text-muted-foreground">{label}</div>
      <div className="min-w-0 truncate font-medium" title={value}>
        {value}
      </div>
    </div>
  )
}
