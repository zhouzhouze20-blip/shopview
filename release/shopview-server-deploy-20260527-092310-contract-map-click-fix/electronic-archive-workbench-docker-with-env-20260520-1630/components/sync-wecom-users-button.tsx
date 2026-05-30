"use client"

import { useTransition } from "react"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { syncWecomUsers } from "@/lib/actions"
import { Button } from "@/components/ui/button"

export function SyncWecomUsersButton() {
  const [isPending, startTransition] = useTransition()

  return (
    <Button
      type="button"
      size="sm"
      disabled={isPending}
      onClick={() => {
        startTransition(async () => {
          const result = await syncWecomUsers()
          toast[result.ok ? "success" : "error"](result.message)
        })
      }}
    >
      <RefreshCw className={`mr-2 h-4 w-4 ${isPending ? "animate-spin" : ""}`} />
      同步企微用户
    </Button>
  )
}
