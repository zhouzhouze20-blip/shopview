"use client"

import { useMemo, useState, useTransition } from "react"
import { Users } from "lucide-react"
import { toast } from "sonner"
import { updateDataScopeUsers } from "@/lib/actions"
import type { AdminDataScope, AdminUser } from "@/lib/admin-data"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"

type DataScopeUserEditorProps = {
  scope: AdminDataScope
  users: AdminUser[]
}

export function DataScopeUserEditor({
  scope,
  users,
}: DataScopeUserEditorProps) {
  const [open, setOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>(scope.userIds)
  const [isPending, startTransition] = useTransition()

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  function resetSelection() {
    setSelectedIds(scope.userIds)
  }

  function toggleUser(userId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, userId]))
      return current.filter((id) => id !== userId)
    })
  }

  function submit() {
    const formData = new FormData()
    formData.set("scopeId", scope.id)
    formData.set("userIds", JSON.stringify(selectedIds))

    startTransition(async () => {
      const result = await updateDataScopeUsers(formData)
      toast[result.ok ? "success" : "error"](result.message)
      if (result.ok) {
        setOpen(false)
      }
    })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (nextOpen) resetSelection()
      }}
    >
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size="sm">
          <Users className="h-4 w-4" />
          设置用户
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>设置数据范围用户</DialogTitle>
          <DialogDescription>
            {scope.scopeName} 当前已选 {selectedIds.length} 个用户
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setSelectedIds(users.map((item) => item.id))}
          >
            全选
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setSelectedIds([])}
          >
            清空
          </Button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto rounded-md border">
          {users.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              暂无用户，请先同步企业微信用户
            </div>
          ) : (
            <div className="divide-y">
              {users.map((user) => {
                const checked = selectedSet.has(user.id)
                return (
                  <Label
                    key={user.id}
                    className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/50"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => toggleUser(user.id, value === true)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{user.displayName}</span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {user.username} · {user.departmentName} · {user.status}
                      </span>
                    </span>
                  </Label>
                )
              })}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setOpen(false)}>
            取消
          </Button>
          <Button type="button" disabled={isPending} onClick={submit}>
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
