"use client"

import { useMemo, useState, useTransition } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { createRole } from "@/lib/actions"
import type { AdminPermission } from "@/lib/admin-data"
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

type CreateRoleDialogProps = {
  permissions: AdminPermission[]
}

export function CreateRoleDialog({ permissions }: CreateRoleDialogProps) {
  const [open, setOpen] = useState(false)
  const [roleCode, setRoleCode] = useState("")
  const [roleName, setRoleName] = useState("")
  const [description, setDescription] = useState("")
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [isPending, startTransition] = useTransition()
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  function resetForm() {
    setRoleCode("")
    setRoleName("")
    setDescription("")
    setSelectedIds([])
  }

  function togglePermission(permissionId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, permissionId]))
      return current.filter((id) => id !== permissionId)
    })
  }

  function submit() {
    const formData = new FormData()
    formData.set("roleCode", roleCode)
    formData.set("roleName", roleName)
    formData.set("description", description)
    formData.set("permissionIds", JSON.stringify(selectedIds))

    startTransition(async () => {
      const result = await createRole(formData)
      toast[result.ok ? "success" : "error"](result.message)
      if (result.ok) {
        setOpen(false)
        resetForm()
      }
    })
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (!nextOpen) resetForm()
      }}
    >
      <DialogTrigger asChild>
        <Button type="button" size="sm">
          <Plus className="h-4 w-4" />
          新建角色
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>新建角色</DialogTitle>
          <DialogDescription>
            创建角色并分配发票池、银行流水、业务单据等权限点。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="role-code">角色编码</Label>
            <Input
              id="role-code"
              value={roleCode}
              onChange={(event) => setRoleCode(event.target.value)}
              placeholder="finance_manager"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role-name">角色名称</Label>
            <Input
              id="role-name"
              value={roleName}
              onChange={(event) => setRoleName(event.target.value)}
              placeholder="财务经理"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="role-description">说明</Label>
            <Textarea
              id="role-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="说明该角色的使用范围"
              rows={3}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">权限点</div>
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
        </div>

        <div className="max-h-[45vh] overflow-y-auto rounded-md border">
          {permissions.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              暂无权限点，请先同步业务权限点
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
                        {permission.permissionCode} · {permission.routePath}
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
          <Button
            type="button"
            disabled={isPending || !roleCode.trim() || !roleName.trim()}
            onClick={submit}
          >
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
