"use client"

import { useTransition } from "react"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { syncDefaultPermissions } from "@/lib/actions"
import { Button } from "@/components/ui/button"

export function SyncDefaultPermissionsButton() {
  const [isPending, startTransition] = useTransition()

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={isPending}
      onClick={() => {
        startTransition(async () => {
          const result = await syncDefaultPermissions()
          toast[result.ok ? "success" : "error"](result.message)
        })
      }}
    >
      <RefreshCw className={`h-4 w-4 ${isPending ? "animate-spin" : ""}`} />
      同步业务权限点
    </Button>
  )
}
