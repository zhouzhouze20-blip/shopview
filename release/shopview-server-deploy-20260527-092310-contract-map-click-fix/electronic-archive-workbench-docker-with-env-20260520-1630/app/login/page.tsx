"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Building2, Lock, User, Eye, EyeOff, FileText, ChevronDown, QrCode } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

type StoreOption = {
  id: string
  name: string
  taxNo?: string
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  )
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [showPassword, setShowPassword] = useState(false)
  const [stores, setStores] = useState<StoreOption[]>([])
  const [selectedStore, setSelectedStore] = useState<StoreOption | undefined>()
  const [isLoadingStores, setIsLoadingStores] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  })
  const authError = searchParams.get("error")
  const authErrorUserId = searchParams.get("userid")

  const authErrorText =
    authError === "missing_code"
      ? "企业微信没有返回授权码，请重新扫码。"
      : authError === "unbound_wecom"
        ? `企业微信账号未绑定系统用户${authErrorUserId ? `：${authErrorUserId}` : ""}`
        : authError
          ? authError
          : ""

  useEffect(() => {
    let ignore = false

    async function loadStores() {
      try {
        const response = await fetch("/api/stores", { cache: "no-store" })
        const data = (await response.json()) as { stores?: StoreOption[] }
        if (ignore) return

        const nextStores = data.stores ?? []
        setStores(nextStores)
        setSelectedStore((current) => current ?? nextStores[0])
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
  }, [])

  function writeStoreCookies(store: StoreOption | undefined) {
    if (!store) return
    const maxAge = 60 * 60 * 24 * 30
    document.cookie = `activeStoreId=${store.id}; path=/; max-age=${maxAge}; SameSite=Lax`
    document.cookie = `activeStoreName=${encodeURIComponent(store.name)}; path=/; max-age=${maxAge}; SameSite=Lax`
    document.cookie = `activeStoreTaxNo=${encodeURIComponent(store.taxNo ?? "")}; path=/; max-age=${maxAge}; SameSite=Lax`
    localStorage.setItem("selectedStore", JSON.stringify(store))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...formData,
          storeId: selectedStore?.id,
          storeName: selectedStore?.name,
        }),
      })
      const data = (await response.json()) as { ok?: boolean; error?: string }
      if (!response.ok || !data.ok) {
        throw new Error(data.error || "登录失败")
      }

      writeStoreCookies(selectedStore)
      router.push("/")
      router.refresh()
    } catch (error) {
      alert(error instanceof Error ? error.message : "登录失败")
      setIsLoading(false)
    }
  }

  const handleWecomLogin = async () => {
    setIsLoading(true)
    try {
      writeStoreCookies(selectedStore)
      const next = searchParams.get("next") || "/"
      const response = await fetch(`/api/auth/wecom/login-url?next=${encodeURIComponent(next)}`, {
        cache: "no-store",
      })
      const data = (await response.json()) as { url?: string; error?: string }
      if (!response.ok || !data.url) {
        throw new Error(data.error || "企业微信登录配置错误")
      }
      window.location.href = data.url
    } catch (error) {
      alert(error instanceof Error ? error.message : "企业微信登录失败")
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区域 */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,oklch(0.45_0.12_240)_0%,oklch(0.35_0.15_240)_100%)]" />
        <div className="relative z-10 flex flex-col justify-center px-16 text-primary-foreground">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-foreground/10 backdrop-blur">
              <FileText className="h-6 w-6" />
            </div>
            <span className="text-2xl font-bold">电子档案工作台</span>
          </div>
          <h1 className="text-4xl font-bold leading-tight mb-4">
            企业级电子档案<br />管理系统
          </h1>
          <p className="text-lg text-primary-foreground/80 max-w-md">
            集成发票管理、银行流水、业务单据、凭证档案于一体的智能化财务档案解决方案
          </p>
          
          {/* 装饰元素 */}
          <div className="mt-16 grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-primary-foreground/10 backdrop-blur p-4">
              <div className="text-3xl font-bold">50K+</div>
              <div className="text-sm text-primary-foreground/70">日处理单据</div>
            </div>
            <div className="rounded-lg bg-primary-foreground/10 backdrop-blur p-4">
              <div className="text-3xl font-bold">99.9%</div>
              <div className="text-sm text-primary-foreground/70">匹配准确率</div>
            </div>
            <div className="rounded-lg bg-primary-foreground/10 backdrop-blur p-4">
              <div className="text-3xl font-bold">10+</div>
              <div className="text-sm text-primary-foreground/70">门店覆盖</div>
            </div>
          </div>
        </div>
        
        {/* 背景装饰 */}
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-primary-foreground/5" />
        <div className="absolute -top-16 -right-16 h-64 w-64 rounded-full bg-primary-foreground/5" />
      </div>

      {/* 右侧登录表单 */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md">
          {/* 移动端 Logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <FileText className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold text-foreground">电子档案工作台</span>
          </div>

          <Card className="border-0 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <h2 className="text-2xl font-bold text-center text-foreground">用户登录</h2>
              <p className="text-sm text-muted-foreground text-center">
                请输入您的账号信息登录系统
              </p>
            </CardHeader>
            <CardContent>
              {authErrorText ? (
                <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {authErrorText}
                </div>
              ) : null}
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* 门店选择 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    选择门店
                  </label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-between h-11 font-normal"
                      >
                        <span className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-muted-foreground" />
                          {selectedStore?.name ?? (isLoadingStores ? "加载门店..." : "暂无门店")}
                        </span>
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="max-h-80 w-[--radix-dropdown-menu-trigger-width] overflow-y-auto">
                      {stores.length === 0 && (
                        <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                          {isLoadingStores ? "正在加载门店" : "没有门店数据"}
                        </div>
                      )}
                      {stores.map((store) => (
                        <DropdownMenuItem
                          key={store.id}
                          onClick={() => setSelectedStore(store)}
                          className="cursor-pointer"
                        >
                          <Building2 className="h-4 w-4 mr-2" />
                          {store.name}
                          <span className="ml-auto text-xs text-muted-foreground">
                            门店管理
                          </span>
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {/* 用户名 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    用户名
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      type="text"
                      placeholder="请输入用户名"
                      className="pl-10 h-11"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>

                {/* 密码 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-foreground">
                    密码
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="请输入密码"
                      className="pl-10 pr-10 h-11"
                      value={formData.password}
                      onChange={(e) =>
                        setFormData({ ...formData, password: e.target.value })
                      }
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* 记住我和忘记密码 */}
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-input"
                    />
                    <span className="text-muted-foreground">记住登录状态</span>
                  </label>
                  <a
                    href="#"
                    className="text-sm text-primary hover:text-primary/80"
                  >
                    忘记密码?
                  </a>
                </div>

                {/* 登录按钮 */}
                <Button
                  type="submit"
                  className="w-full h-11"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      登录中...
                    </span>
                  ) : (
                    "登录"
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full h-11"
                  disabled={isLoading}
                  onClick={handleWecomLogin}
                >
                  <QrCode className="mr-2 h-4 w-4" />
                  企业微信扫码登录
                </Button>
              </form>

              {/* 底部信息 */}
              <div className="mt-6 text-center text-xs text-muted-foreground">
                登录即表示您同意我们的
                <a href="#" className="text-primary hover:underline mx-1">
                  服务条款
                </a>
                和
                <a href="#" className="text-primary hover:underline mx-1">
                  隐私政策
                </a>
              </div>
            </CardContent>
          </Card>

          {/* 版权信息 */}
          <p className="mt-8 text-center text-xs text-muted-foreground">
            &copy; 2024 电子档案工作台. 保留所有权利.
          </p>
        </div>
      </div>
    </div>
  )
}
