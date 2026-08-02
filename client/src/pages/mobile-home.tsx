import { CircleDollarSign, FileText, LayoutGrid, LogOut, PackageSearch, ShieldCheck, TrendingUp } from "lucide-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import { canAccessModule } from "@/lib/module-permissions";

const MOBILE_MODULES = [
  {
    id: "mobile-sales-dashboard",
    title: "销售",
    description: "查看销售、毛利、小票与柜组明细",
    path: "/mobile/sales",
    icon: TrendingUp,
    iconClassName: "bg-blue-600 text-white",
  },
  {
    id: "mobile-contracts",
    title: "合同",
    description: "查询合同台账、状态、期限与合同明细",
    path: "/mobile/contracts",
    icon: FileText,
    iconClassName: "bg-teal-600 text-white",
  },
  {
    id: "mobile-inventory",
    title: "库存查询",
    description: "手工输入或扫描商品条码查询实时库存",
    path: "/mobile/inventory",
    icon: PackageSearch,
    iconClassName: "bg-cyan-700 text-white",
  },
  {
    id: "mobile-revenue-dashboard",
    title: "收益",
    description: "查看门店、部门、柜位收益及费用明细",
    path: "/mobile/revenue",
    icon: CircleDollarSign,
    iconClassName: "bg-amber-600 text-white",
  },
] as const;

export default function MobileHomePage() {
  const { user, menuUser, logout } = useAuth();
  const [, setLocation] = useLocation();
  const accessibleModules = MOBILE_MODULES.filter((module) => canAccessModule(menuUser, module.id));

  useModuleAccessLog({
    moduleId: "mobile-home",
    moduleName: "手机端工作台",
    clientType: "mobile",
  });

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="bg-gradient-to-br from-slate-950 via-slate-900 to-teal-950 px-5 pb-8 pt-[max(1rem,env(safe-area-inset-top))] text-white shadow-md">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-white/10">
              <LayoutGrid className="h-5 w-5 text-teal-200" />
            </div>
            <div>
              <div className="text-[10px] font-medium tracking-[0.16em] text-teal-200">SHOPVIEW</div>
              <h1 className="text-lg font-semibold">移动工作台</h1>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-full text-white hover:bg-white/10 hover:text-white"
            onClick={() => logout()}
            aria-label="退出登录"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-5">
          <div className="text-sm text-slate-300">欢迎回来</div>
          <div className="mt-1 text-xl font-semibold">{user?.real_name || user?.username}</div>
          <div className="mt-2 text-xs text-slate-400">请选择要进入的业务模块</div>
        </div>
      </header>

      <div className="mx-auto -mt-4 max-w-xl space-y-4 px-4">
        <Card className="rounded-3xl border-0 shadow-lg">
          <CardContent className="p-4">
            <div className="mb-3 flex items-center justify-between px-1">
              <h2 className="text-sm font-semibold text-slate-950">业务应用</h2>
              <span className="text-[11px] text-slate-400">按账号权限展示</span>
            </div>

            {accessibleModules.length ? (
              <div className="grid grid-cols-4 gap-x-2 gap-y-4 py-1">
                {accessibleModules.map((module) => {
                  const Icon = module.icon;
                  return (
                    <button
                      key={module.id}
                      type="button"
                      className="group flex min-w-0 flex-col items-center rounded-2xl px-1 py-2 text-center transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2 active:scale-95"
                      onClick={() => setLocation(module.path)}
                      aria-label={`${module.title}：${module.description}`}
                    >
                      <div className={`grid h-14 w-14 shrink-0 place-items-center rounded-2xl shadow-sm transition group-active:shadow-none ${module.iconClassName}`}>
                        <Icon className="h-7 w-7" />
                      </div>
                      <div className="mt-2 w-full whitespace-nowrap text-[13px] font-medium leading-5 text-slate-800">{module.title}</div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-2xl bg-slate-50 px-5 py-10 text-center">
                <ShieldCheck className="mx-auto h-9 w-9 text-slate-400" />
                <div className="mt-3 text-sm font-medium text-slate-700">暂无可访问的手机模块</div>
                <div className="mt-2 text-xs leading-5 text-slate-500">请联系管理员开通相应的手机端模块权限。</div>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex items-center justify-center gap-2 py-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4" /> 手机端模块权限与业务数据范围共同控制
        </div>
      </div>
    </main>
  );
}
