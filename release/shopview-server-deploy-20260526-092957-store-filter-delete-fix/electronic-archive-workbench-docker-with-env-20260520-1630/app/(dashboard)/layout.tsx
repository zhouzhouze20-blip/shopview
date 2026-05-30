import { AppSidebar } from "@/components/app-sidebar"
import { AppHeader } from "@/components/app-header"
import { getCurrentUser } from "@/lib/auth"
import { redirect } from "next/navigation"

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const currentUser = await getCurrentUser()
  if (!currentUser) {
    redirect("/login")
  }

  return (
    <div className="grid h-screen grid-cols-[14rem_minmax(0,1fr)] grid-rows-[3.5rem_minmax(0,1fr)] overflow-hidden bg-background">
      <AppSidebar currentUser={currentUser} />
      <AppHeader currentUser={currentUser} />
      <main className="col-start-2 row-start-2 min-h-0 min-w-0 overflow-auto p-6">
        {children}
      </main>
    </div>
  )
}
