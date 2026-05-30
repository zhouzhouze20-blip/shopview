"use client"

import { useMemo, useState, useTransition } from "react"
import { Store } from "lucide-react"
import { toast } from "sonner"
import { updateUserStoreScopes } from "@/lib/actions"
import type { AdminUser } from "@/lib/admin-data"
import type { StoreOption } from "@/lib/stores"
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

type UserStoreScopeEditorProps = {
  user: AdminUser
  stores: StoreOption[]
}

export function UserStoreScopeEditor({ user, stores }: UserStoreScopeEditorProps) {
  const [open, setOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>(user.dataScopeStoreIds)
  const [isPending, startTransition] = useTransition()
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds])

  function resetSelection() {
    setSelectedIds(user.dataScopeStoreIds)
  }

  function toggleStore(storeId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return Array.from(new Set([...current, storeId]))
      return current.filter((id) => id !== storeId)
    })
  }

  function submit() {
    const selectedStores = stores.filter((store) => selectedSet.has(store.id))
    const formData = new FormData()
    formData.set("userId", user.id)
    formData.set("stores", JSON.stringify(selectedStores))

    startTransition(async () => {
      const result = await updateUserStoreScopes(formData)
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
          <Store className="h-4 w-4" />
          设置门店
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>设置用户数据范围</DialogTitle>
          <DialogDescription>
            数据范围按门店控制，{user.displayName} 当前已选 {selectedIds.length} 个门店
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setSelectedIds(stores.map((store) => store.id))}
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
          {stores.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              暂无门店数据
            </div>
          ) : (
            <div className="divide-y">
              {stores.map((store) => {
                const checked = selectedSet.has(store.id)
                return (
                  <Label
                    key={store.id}
                    className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/50"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={(value) => toggleStore(store.id, value === true)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{store.name}</span>
                      <span className="mt-1 block truncate text-xs text-muted-foreground">
                        {store.id}
                        {store.taxNo ? ` · ${store.taxNo}` : ""}
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
