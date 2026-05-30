"use client"

import { useMemo, useState, useTransition } from "react"
import { ShieldCheck } from "lucide-react"
import { toast } from "sonner"
import { updateRolePermissions } from "@/lib/actions"
import type { AdminPermission, AdminRole } from "@/lib/admin-data"
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

type RolePermissionEditorProps = {
  role: AdminRole
  permissions: AdminPermission[]
}

export function RolePermissionEditor({
  role,
  permissions,
}: RolePermissionEditorProps) {
  const [open, setOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>(role.permissionIds)
  const [isPending, startTransition] = useTransition()

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  function resetSelection() {
    setSelectedIds(role.permissionIds)
  }

  function togglePermission(permissionId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, permissionId]))
      return current.filter((id) => id !== permissionId)
    })
  }

  function submit() {
    const formData = new FormData()
    formData.set("roleId", role.id)
    formData.set("permissionIds", JSON.stringify(selectedIds))

    startTransition(async () => {
      const result = await updateRolePermissions(formData)
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
          设置权限
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>设置角色权限</DialogTitle>
          <DialogDescription>
            {role.roleName} 当前已选 {selectedIds.length} 个权限点
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setSelectedIds(permissions.map((item) => item.id))}
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
          {permissions.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              暂无权限点
            </div>
          ) : (
            <div className="divide-y">
              {permissions.map((permission) => {
                const checked = selectedSet.has(permission.id)
                return (
                  <Label
                    key={permission.id}
                    className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/50"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) =>
                        togglePermission(permission.id, value === true)
                      }
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">
                        {permission.permissionName}
                      </span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {permission.permissionCode} · {permission.permissionType} ·{" "}
                        {permission.routePath}
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
