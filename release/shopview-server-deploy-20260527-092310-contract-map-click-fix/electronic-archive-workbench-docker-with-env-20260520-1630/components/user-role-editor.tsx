"use client"

import { useMemo, useState, useTransition } from "react"
import { ShieldCheck } from "lucide-react"
import { toast } from "sonner"
import { updateUserRoles } from "@/lib/actions"
import type { AdminRole, AdminUser } from "@/lib/admin-data"
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

type UserRoleEditorProps = {
  user: AdminUser
  roles: AdminRole[]
}

export function UserRoleEditor({ user, roles }: UserRoleEditorProps) {
  const [open, setOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>(user.roleIds)
  const [isPending, startTransition] = useTransition()
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  function resetSelection() {
    setSelectedIds(user.roleIds)
  }

  function toggleRole(roleId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, roleId]))
      return current.filter((id) => id !== roleId)
    })
  }

  function submit() {
    const formData = new FormData()
    formData.set("userId", user.id)
    formData.set("roleIds", JSON.stringify(selectedIds))

    startTransition(async () => {
      const result = await updateUserRoles(formData)
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
          <ShieldCheck className="h-4 w-4" />
          设置角色
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>设置用户权限</DialogTitle>
          <DialogDescription>
            {user.displayName} 通过角色获得权限，当前已选 {selectedIds.length} 个角色
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto rounded-md border">
          {roles.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              暂无角色，请先创建角色
            </div>
          ) : (
            <div className="divide-y">
              {roles.map((role) => {
                const checked = selectedSet.has(role.id)
                return (
                  <Label
                    key={role.id}
                    className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/50"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => toggleRole(role.id, value === true)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{role.roleName}</span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {role.roleCode} · {role.permissionNames}
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
