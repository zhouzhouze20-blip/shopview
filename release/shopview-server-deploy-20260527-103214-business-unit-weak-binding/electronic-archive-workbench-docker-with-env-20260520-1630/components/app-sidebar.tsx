"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  FileText,
  Landmark,
  FileStack,
  BookCheck,
  Home,
  ChevronDown,
  ChevronRight,
  Building2,
  Store,
  Check,
  ShieldCheck,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface StoreOption {
  id: string
  name: string
  taxNo?: string
}

interface MenuItem {
  title: string
  href: string
  icon: React.ReactNode
  permissionCode: string
  children?: { title: string; href: string; permissionCode: string }[]
}

type AppSidebarProps = {
  currentUser?: {
    username?: string
    permissionCodes?: string[]
    dataScopeStoreIds?: string[]
    hasAllDataScope?: boolean
  }
}

const baseMenuItems: MenuItem[] = [
  {
    title: "工作台",
    href: "/",
    permissionCode: "dashboard",
    icon: <Home className="h-4 w-4" />,
  },
  {
    title: "发票池",
    href: "/invoices",
    permissionCode: "invoices",
    icon: <FileText className="h-4 w-4" />,
    children: [
      { title: "已匹配单据确认", href: "/invoices/matched", permissionCode: "invoices.matched" },
      { title: "匹配确认报表", href: "/invoices/confirmed-report", permissionCode: "invoices.confirmedReport" },
      { title: "金额不一致处理", href: "/invoices/amount-mismatch", permissionCode: "invoices.amountMismatch" },
      { title: "未匹配发票确认", href: "/invoices/unmatched", permissionCode: "invoices.unmatched" },
    ],
  },
  {
    title: "银行流水",
    href: "/bank-transactions",
    permissionCode: "bankTransactions",
    icon: <Landmark className="h-4 w-4" />,
    children: [
      { title: "流水匹配", href: "/bank-transactions/matching", permissionCode: "bankTransactions.matching" },
      { title: "回单归档", href: "/bank-transactions/receipts", permissionCode: "bankTransactions.receipts" },
      { title: "异常流水", href: "/bank-transactions/exceptions", permissionCode: "bankTransactions.exceptions" },
    ],
  },
  {
    title: "业务单据",
    href: "/documents",
    permissionCode: "documents",
    icon: <FileStack className="h-4 w-4" />,
    children: [
      { title: "ERP单据", href: "/documents/erp", permissionCode: "documents.erp" },
      { title: "OA单据", href: "/documents/oa", permissionCode: "documents.oa" },
      { title: "合同/结算单", href: "/documents/contracts", permissionCode: "documents.contracts" },
    ],
  },
  {
    title: "凭证档案",
    href: "/vouchers",
    permissionCode: "vouchers",
    icon: <BookCheck className="h-4 w-4" />,
    children: [
      { title: "待生成凭证", href: "/vouchers/pending", permissionCode: "vouchers.pending" },
      { title: "已生成凭证", href: "/vouchers/generated", permissionCode: "vouchers.generated" },
      { title: "NC对接记录", href: "/vouchers/nc-records", permissionCode: "vouchers.ncRecords" },
    ],
  },
]

const adminMenuItem: MenuItem = {
  title: "系统管理",
  href: "/admin",
  permissionCode: "admin",
  icon: <ShieldCheck className="h-4 w-4" />,
  children: [
    { title: "用户管理", href: "/admin/users", permissionCode: "admin.users" },
    { title: "权限管理", href: "/admin/permissions", permissionCode: "admin.permissions" },
    { title: "数据范围", href: "/admin/data-scopes", permissionCode: "admin.dataScopes" },
  ],
}

export function AppSidebar({ currentUser }: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [expandedItems, setExpandedItems] = useState<string[]>([
    "/stores",
    "/invoices",
    "/bank-transactions",
    "/documents",
    "/vouchers",
    "/admin",
  ])
  const [stores, setStores] = useState<StoreOption[]>([])
  const [currentStore, setCurrentStore] = useState<StoreOption | undefined>()
  const [isLoadingStores, setIsLoadingStores] = useState(true)

  useEffect(() => {
    const hasAllStores =
      currentUser?.username === "admin" || currentUser?.hasAllDataScope === true
    const allowedStoreIds = new Set(currentUser?.dataScopeStoreIds ?? [])
    const cookieStore = Object.fromEntries(
      document.cookie
        .split("; ")
        .filter(Boolean)
        .map((item) => {
          const [key, ...value] = item.split("=")
          return [key, value.join("=")]
        })
    )
    const storedId = cookieStore.activeStoreId
    const storedName = cookieStore.activeStoreName
      ? decodeURIComponent(cookieStore.activeStoreName)
      : undefined
    const storedTaxNo = cookieStore.activeStoreTaxNo
      ? decodeURIComponent(cookieStore.activeStoreTaxNo)
      : undefined

    let ignore = false

    async function loadStores() {
      try {
        const response = await fetch("/api/stores", { cache: "no-store" })
        const data = (await response.json()) as { stores?: StoreOption[] }
        if (ignore) return

        const nextStores = data.stores ?? []
        const accessibleStores = hasAllStores
          ? nextStores
          : nextStores.filter((store) => allowedStoreIds.has(store.id))
        setStores(accessibleStores)

        const storedStore =
          storedId && storedName
            ? accessibleStores.find((store) => store.id === storedId) ||
              accessibleStores.find((store) => store.name === storedName)
            : undefined

        if (storedStore) {
          setCurrentStore({
            ...storedStore,
            taxNo: storedStore.taxNo ?? storedTaxNo,
          })
          writeStoreCookies({
            ...storedStore,
            taxNo: storedStore.taxNo ?? storedTaxNo,
          })
        } else if (accessibleStores[0]) {
          setCurrentStore(accessibleStores[0])
          writeStoreCookies(accessibleStores[0])
          router.refresh()
        } else {
          setCurrentStore(undefined)
        }
      } catch {
        if (!ignore) setStores([])
      } finally {
        if (!ignore) setIsLoadingStores(false)
      }
    }

    loadStores()

    return () => {
      ignore = true
    }
  }, [currentUser, router])

  const writeStoreCookies = (store: StoreOption) => {
    const maxAge = 60 * 60 * 24 * 30
    document.cookie = `activeStoreId=${store.id}; path=/; max-age=${maxAge}; SameSite=Lax`
    document.cookie = `activeStoreName=${encodeURIComponent(store.name)}; path=/; max-age=${maxAge}; SameSite=Lax`
    document.cookie = `activeStoreTaxNo=${encodeURIComponent(store.taxNo ?? "")}; path=/; max-age=${maxAge}; SameSite=Lax`
  }

  const handleStoreChange = (store: StoreOption) => {
    setCurrentStore(store)
    writeStoreCookies(store)
    router.refresh()
  }

  const menuItems: MenuItem[] = [
    ...baseMenuItems.slice(0, 1),
    {
      title: "门店管理",
      href: "/stores",
      permissionCode: "stores",
      icon: <Store className="h-4 w-4" />,
      children: [
        { title: "门店列表", href: "/stores/list", permissionCode: "stores.list" },
        { title: "门店档案", href: "/stores/archives", permissionCode: "stores.archives" },
        { title: "门店对账", href: "/stores/reconciliation", permissionCode: "stores.reconciliation" },
      ],
    },
    ...baseMenuItems.slice(1),
    adminMenuItem,
  ]
  const permissionSet = new Set(currentUser?.permissionCodes ?? [])
  const canSee = (permissionCode: string) => permissionSet.has(permissionCode)
  const visibleMenuItems = menuItems.reduce<MenuItem[]>((items, item) => {
      const children = item.children?.filter((child) => canSee(child.permissionCode))
      if (canSee(item.permissionCode) || (children && children.length > 0)) {
        items.push({ ...item, children })
      }
      return items
    }, [])

  const toggleExpand = (href: string) => {
    setExpandedItems((prev) =>
      prev.includes(href)
        ? prev.filter((item) => item !== href)
        : [...prev, href]
    )
  }

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/"
    return pathname.startsWith(href)
  }

  return (
    <aside className="col-start-1 row-span-2 flex h-screen min-w-0 flex-col overflow-hidden border-r border-border bg-sidebar">
      <div className="flex h-14 items-center border-b border-border px-4">
        <FileText className="mr-2 h-5 w-5 text-primary" />
        <span className="text-base font-semibold text-sidebar-foreground">
          电子档案工作台
        </span>
      </div>

      {/* 门店选择器 */}
      <div className="border-b border-border p-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex w-full min-w-0 items-center justify-between gap-2 rounded-md bg-sidebar-accent px-3 py-2 text-sm transition-colors hover:bg-sidebar-accent/80">
              <span className="flex min-w-0 flex-1 items-center gap-2">
                <Building2 className="h-4 w-4 shrink-0 text-primary" />
                <span className="min-w-0 truncate font-medium text-sidebar-foreground">
                  {currentStore?.name ?? (isLoadingStores ? "加载门店..." : "暂无门店")}
                </span>
              </span>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-80 w-52 overflow-y-auto">
            {stores.length === 0 && (
              <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                {isLoadingStores ? "正在加载门店" : "没有门店数据"}
              </div>
            )}
            {stores.map((store) => (
              <DropdownMenuItem
                key={store.id}
                onClick={() => handleStoreChange(store)}
                className="cursor-pointer"
              >
                <Building2 className="mr-2 h-4 w-4 shrink-0" />
                <span className="min-w-0 flex-1 truncate" title={store.name}>{store.name}</span>
                {currentStore?.id === store.id && (
                  <Check className="h-4 w-4 shrink-0 text-primary" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <div className="mt-1.5 px-1 text-xs text-muted-foreground">
          门店管理模式
        </div>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto p-3">
        <ul className="space-y-1">
          {visibleMenuItems.map((item) => (
            <li key={item.href}>
              {item.children ? (
                <div>
                  <div
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isActive(item.href)
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    )}
                  >
                    <Link href={item.href} className="flex min-w-0 flex-1 items-center gap-2">
                      <span className="shrink-0">{item.icon}</span>
                      <span className="truncate">{item.title}</span>
                    </Link>
                    <button
                      type="button"
                      onClick={() => toggleExpand(item.href)}
                      className="ml-2 shrink-0 rounded-sm p-0.5 hover:bg-sidebar-accent"
                      aria-label={expandedItems.includes(item.href) ? "收起菜单" : "展开菜单"}
                      aria-expanded={expandedItems.includes(item.href)}
                    >
                    {expandedItems.includes(item.href) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    </button>
                  </div>
                  {expandedItems.includes(item.href) && (
                    <ul className="ml-4 mt-1 space-y-1 border-l border-border pl-3">
                      {item.children.map((child) => (
                        <li key={child.href}>
                          <Link
                            href={child.href}
                            className={cn(
                              "block rounded-md px-3 py-1.5 text-sm transition-colors",
                              pathname === child.href
                                ? "bg-sidebar-primary text-sidebar-primary-foreground"
                                : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                            )}
                          >
                            {child.title}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <Link
                  href={item.href}
                  className={cn(
                    "flex min-w-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive(item.href)
                      ? "bg-sidebar-primary text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                >
                  <span className="shrink-0">{item.icon}</span>
                  <span className="truncate">{item.title}</span>
                </Link>
              )}
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
