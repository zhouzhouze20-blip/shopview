import { useState, useEffect, useRef, useMemo, useCallback, Component, ReactNode } from "react";
import { useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import NavigationSidebar from "@/components/navigation-sidebar";
import BaseMapsPage from "@/pages/base-maps";
import UnitMapVersionsPage from "@/pages/unit-map-versions";
import BusinessUnitsPage from "@/pages/business-units";
import FloorAreaReportPage from "@/pages/floor-area-report";
import TenantsPage from "./tenants";
import CountersPage from "./counters";
import FloorsPage from "./floors";
import ContractsPage from "./contracts";
import SalesDashboardPage from "./sales-dashboard";
import ActivityAnalysisPage from "./activity-analysis";
import CommoditySalesDetailReportPage from "./sales-reports/commodity-sales-detail";
import JointSettlementStatementsPage from "./joint-settlement-statements";
import ManaframePage from "./manaframe";
import SuppliersPage from "./suppliers";
import SystemConfigPage from "./system-config";
import DecorationsPage from "./decorations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  aggregateStoreSummaries,
  useContractDashboardSummary,
  useExpiringContractsThisMonth,
  useSalesDashboardOverview,
} from "@/hooks/useHomeDashboard";
import { cn } from "@/lib/utils";
import { apiPost } from "@/lib/api";
import { useStore } from "@/contexts/StoreContext";
import { useAuth } from "@/contexts/AuthContext";
import { useIsMobile } from "@/hooks/use-mobile";
import {
  Building2,
  Users,
  FileText,
  BarChart3,
  Calendar,
  CheckCircle,
  Clock,
  Plus,
  Edit,
  Trash2,
  Upload,
  Image,
  ChevronRight,
  Loader2,
  Menu,
} from "lucide-react";

// 内容区错误边界：捕获切换时的 removeChild 等错误，避免整页白屏
class ContentErrorBoundary extends Component<{ children: ReactNode; activeModule: string }> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidUpdate(prev: { activeModule: string }) {
    if (prev.activeModule !== this.props.activeModule && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-slate-600">
          <p className="mb-2">页面切换时出现异常</p>
          <Button variant="outline" size="sm" onClick={() => this.setState({ hasError: false })}>
            重试
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}

// 品牌管理页面组件
function BrandsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">品牌档案</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>TechWorld</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-600">专业电子产品零售</p>
            <div className="mt-2 text-sm text-slate-500">分类: 电子产品</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>时尚佳人</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-slate-600">时尚女装品牌</p>
            <div className="mt-2 text-sm text-slate-500">分类: 服装</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const homeMoney = (n: number) =>
  new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 }).format(n);

function fmtDashDate(value?: string | null) {
  if (!value) return "—";
  return value.slice(0, 10);
}

const MODULE_LABELS: Record<string, string> = {
  dashboard: "经营概览",
  decorations: "装修项目",
  "decorations-todos": "装修待办",
  manaframe: "柜位定义",
  suppliers: "供应商管理",
  contracts: "合同台账",
  "sales-dashboard": "销售看板",
  "activity-analysis": "活动分析",
  "commodity-sales-detail": "商品销售明细",
  "joint-settlement": "联营结算单管理",
  floors: "楼层定义",
  "base-maps": "底图管理",
  "unit-map-versions": "柜位图版本",
  "business-units": "经营单元设置",
  "floor-area-report": "楼层面积报表",
  "user-role-scope": "用户角色及范围定义",
  users: "用户",
  roles: "角色",
  departments: "部门定义",
  "contract-permissions": "业务范围",
  "audit-logs": "日志查询",
};

const recordModuleAccess = (moduleId: string) => {
  void apiPost("/api/system/module-access-log", {
    module_id: moduleId,
    module_name: MODULE_LABELS[moduleId] || moduleId,
  }).catch(() => {
    // 日志失败不阻断模块切换。
  });
};

function yoyPercent(current: number, prior: number): number | null {
  if (prior <= 0 || !Number.isFinite(prior)) return null;
  return ((current - prior) / prior) * 100;
}

function formatYoy(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function yoyColorClass(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "text-slate-500";
  if (pct > 0) return "text-red-600";
  if (pct < 0) return "text-emerald-600";
  return "text-slate-500";
}

// 系统总览页面组件（销售 + 合同概览，自上而下）
function SystemOverview({
  onModuleChange,
  onNavigateToContractDetail,
}: {
  onModuleChange: (moduleId: string) => void | Promise<void>;
  /** 跳转合同台账并打开指定合同明细 */
  onNavigateToContractDetail?: (contractNo: string) => void;
}) {
  const [expiringDialogOpen, setExpiringDialogOpen] = useState(false);
  const salesQuery = useSalesDashboardOverview();
  const contractQuery = useContractDashboardSummary();
  const expiringListQuery = useExpiringContractsThisMonth(expiringDialogOpen);
  const currAgg = useMemo(
    () => aggregateStoreSummaries(salesQuery.currentQuery.data),
    [salesQuery.currentQuery.data],
  );
  const priorAgg = useMemo(
    () => aggregateStoreSummaries(salesQuery.priorQuery.data),
    [salesQuery.priorQuery.data],
  );
  const salesMargin =
    currAgg.effective_sales > 0 ? (currAgg.net_profit / currAgg.effective_sales) * 100 : 0;
  const salesYoy = yoyPercent(currAgg.effective_sales, priorAgg.effective_sales);
  const profitYoy = yoyPercent(currAgg.net_profit, priorAgg.net_profit);
  const { meta } = salesQuery;

  const goSales = () => void onModuleChange("sales-dashboard");
  const goContracts = () => void onModuleChange("contracts");

  return (
    <>
    <div className="space-y-4 p-4 sm:space-y-6 sm:p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 sm:text-3xl">经营概览</h1>
        <p className="mt-1 text-sm text-muted-foreground">以下为当前账号数据范围内的汇总，点击卡片进入对应模块。</p>
      </div>

      <div className="flex flex-col gap-4 sm:gap-6">
        <Card
          className="cursor-pointer border-2 border-transparent transition-colors hover:border-slate-300 hover:bg-slate-50/80"
          onClick={goSales}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              goSales();
            }
          }}
        >
          <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-2">
            <div className="min-w-0 space-y-1">
              <CardTitle className="text-lg font-semibold">销售概览</CardTitle>
              <p className="text-xs text-muted-foreground">
                财务月第 {meta.window.index} 期 · 本期 {meta.periodStart}～{meta.periodEnd}（按财务月口径累计至今日）
              </p>
              <p className="text-[11px] text-muted-foreground">
                上年同期区间 {meta.priorPeriodStart}～{meta.priorPeriodEnd}（自然日天数与本期对齐）
                {salesQuery.priorError ? " · 同期数据未加载" : null}
              </p>
            </div>
            <BarChart3 className="h-8 w-8 shrink-0 text-blue-600" />
          </CardHeader>
          <CardContent className="space-y-4">
            {salesQuery.isLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground py-6 justify-center">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>加载销售数据…</span>
              </div>
            ) : salesQuery.currentError ? (
              <p className="text-sm text-amber-700 py-4">
                无法加载销售汇总（可能无「销售查看」权限或接口异常）。仍可点击下方尝试打开销售看板。
              </p>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 sm:gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground">销售收入</div>
                    <div className="text-xl font-bold tabular-nums sm:text-2xl">{homeMoney(currAgg.effective_sales)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">毛利</div>
                    <div className="text-xl font-bold tabular-nums text-slate-900 sm:text-2xl">{homeMoney(currAgg.net_profit)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">毛利率</div>
                    <div className="text-xl font-semibold tabular-nums">
                      {currAgg.effective_sales > 0 ? `${salesMargin.toFixed(1)}%` : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">小票数</div>
                    <div className="text-xl font-semibold tabular-nums">
                      {new Intl.NumberFormat("zh-CN").format(currAgg.ticket_count)}
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-2 sm:grid-cols-2 lg:grid-cols-4 sm:gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground">月同期销售</div>
                    <div className="text-lg font-semibold tabular-nums text-slate-800">
                      {salesQuery.priorError ? "—" : homeMoney(priorAgg.effective_sales)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">月同期毛利</div>
                    <div className="text-lg font-semibold tabular-nums text-slate-800">
                      {salesQuery.priorError ? "—" : homeMoney(priorAgg.net_profit)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">销售同比</div>
                    <div
                      className={`text-lg font-bold tabular-nums ${yoyColorClass(salesQuery.priorError ? null : salesYoy)}`}
                    >
                      {salesQuery.priorError ? "—" : formatYoy(salesYoy)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">毛利同比</div>
                    <div
                      className={`text-lg font-bold tabular-nums ${yoyColorClass(salesQuery.priorError ? null : profitYoy)}`}
                    >
                      {salesQuery.priorError ? "—" : formatYoy(profitYoy)}
                    </div>
                  </div>
                </div>
              </>
            )}
            <div className="flex items-center justify-between text-sm text-blue-700 pt-2 border-t border-slate-100">
              <span>进入销售看板</span>
              <ChevronRight className="h-4 w-4" />
            </div>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer border-2 border-transparent transition-colors hover:border-slate-300 hover:bg-slate-50/80"
          onClick={goContracts}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              goContracts();
            }
          }}
        >
          <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-2">
            <div className="min-w-0 space-y-1">
              <CardTitle className="text-lg font-semibold">合同概览</CardTitle>
              <p className="text-xs text-muted-foreground">
                统计截止 {contractQuery.data?.as_of_date ?? "—"}，与合同台账权限范围一致
              </p>
            </div>
            <FileText className="h-8 w-8 shrink-0 text-violet-600" />
          </CardHeader>
          <CardContent className="space-y-4">
            {contractQuery.isLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground py-6 justify-center">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>加载合同指标…</span>
              </div>
            ) : contractQuery.isError ? (
              <p className="text-sm text-amber-700 py-4">
                无法加载合同指标（可能无「合同查看」权限或接口异常）。仍可点击下方打开合同台账。
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <div className="text-xs text-muted-foreground">在营合同</div>
                  <div className="text-2xl font-bold tabular-nums">
                    {contractQuery.data?.active_in_operation ?? 0}
                    <span className="text-sm font-normal text-muted-foreground ml-1">份</span>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">本月新增</div>
                  <div className="text-2xl font-bold tabular-nums text-slate-800">
                    {contractQuery.data?.new_this_month ?? 0}
                    <span className="text-sm font-normal text-muted-foreground ml-1">份</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">按录入日期</p>
                </div>
                <div
                  className={cn(
                    "rounded-lg border border-transparent p-3 -m-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-violet-400",
                    "cursor-pointer hover:bg-amber-50/90 hover:border-amber-200",
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpiringDialogOpen(true);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      setExpiringDialogOpen(true);
                    }
                  }}
                  aria-label="查看本月即将到期合同明细"
                >
                  <div className="text-xs text-muted-foreground">本月将到期</div>
                  <div className="text-2xl font-bold tabular-nums text-amber-800">
                    {contractQuery.data?.expiring_this_month ?? 0}
                    <span className="text-sm font-normal text-muted-foreground ml-1">份</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">在营且失效日在本月 · 点击查看明细</p>
                </div>
              </div>
            )}
            <div className="flex items-center justify-between text-sm text-violet-800 pt-2 border-t border-slate-100">
              <span>进入合同台账</span>
              <ChevronRight className="h-4 w-4" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <Dialog open={expiringDialogOpen} onOpenChange={setExpiringDialogOpen}>
      <DialogContent className="max-w-5xl max-h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-2 shrink-0">
          <DialogTitle>本月即将到期合同</DialogTitle>
          <p className="text-sm text-muted-foreground font-normal">
            与「本月将到期」计数同一口径：在营且失效日期落在本月；按失效日先后排列。
          </p>
        </DialogHeader>
        <div className="px-6 pb-6 flex-1 min-h-0 overflow-auto">
          {expiringListQuery.isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin shrink-0" />
              <span>加载中…</span>
            </div>
          ) : expiringListQuery.isError ? (
            <p className="text-sm text-destructive py-6">加载失败，请稍后重试。</p>
          ) : !expiringListQuery.data?.items?.length ? (
            <p className="text-sm text-muted-foreground py-8 text-center">暂无本月即将到期的合同。</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[140px]">合同号</TableHead>
                  <TableHead>主题</TableHead>
                  <TableHead className="w-[110px]">生效日</TableHead>
                  <TableHead className="w-[110px]">失效日</TableHead>
                  <TableHead className="w-[120px]">供应商</TableHead>
                  <TableHead>柜组</TableHead>
                  <TableHead className="w-[88px] text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {expiringListQuery.data.items.map((row) => (
                  <TableRow key={row.cmcontno}>
                    <TableCell className="font-medium">
                      <Button
                        variant="link"
                        className="h-auto p-0 font-mono text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpiringDialogOpen(false);
                          onNavigateToContractDetail?.(row.cmcontno);
                        }}
                      >
                        {row.cmcontno}
                      </Button>
                    </TableCell>
                    <TableCell className="max-w-[220px]">
                      <Button
                        variant="link"
                        className="h-auto min-h-0 p-0 text-left font-normal text-sm whitespace-normal line-clamp-2"
                        title={row.cmtitle ?? undefined}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpiringDialogOpen(false);
                          onNavigateToContractDetail?.(row.cmcontno);
                        }}
                      >
                        {row.cmtitle ?? "—"}
                      </Button>
                    </TableCell>
                    <TableCell className="tabular-nums text-sm">{fmtDashDate(row.cmeffdate)}</TableCell>
                    <TableCell className="tabular-nums text-sm font-medium text-amber-900">
                      {fmtDashDate(row.cmlapdate)}
                    </TableCell>
                    <TableCell className="text-sm">
                      <span className="line-clamp-2" title={row.supplier_name ?? row.cmsupid ?? undefined}>
                        {row.supplier_name?.trim() || row.cmsupid?.trim() || "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm max-w-[200px]">
                      <span className="line-clamp-2" title={row.group_names ?? row.group_codes ?? undefined}>
                        {row.group_names?.trim() || row.group_codes?.trim() || "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpiringDialogOpen(false);
                          onNavigateToContractDetail?.(row.cmcontno);
                        }}
                      >
                        查看明细
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
    </>
  );
}

export default function MainDashboard() {
  const [activeModule, setActiveModule] = useState("dashboard");
  const [location] = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const hasSyncedUrlRef = useRef(false);
  /** 从经营概览等处跳入合同时传入，由 ContractsPage 消费后清空 */
  const [contractsInitialContractNo, setContractsInitialContractNo] = useState<string | null>(null);
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();

  const handleContractsJumpConsumed = useCallback(() => {
    setContractsInitialContractNo(null);
  }, []);

  // 使用全局门店状态
  const { selectedStoreId } = useStore();

  // 仅首次进入本页时根据 URL 设置模块，之后不再覆盖用户点击的菜单
  useEffect(() => {
    if (hasSyncedUrlRef.current) return;
    hasSyncedUrlRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get('view');
    if (viewParam) {
      setActiveModule(viewParam);
    }
  }, []);

  useEffect(() => {
    if (!isMobile && mobileMenuOpen) {
      setMobileMenuOpen(false);
    }
  }, [isMobile, mobileMenuOpen]);

  const renderContent = () => {
    switch (activeModule) {
      case "dashboard":
        return (
          <SystemOverview
            onModuleChange={handleModuleChange}
            onNavigateToContractDetail={(contractNo) => {
              const no = contractNo.trim();
              if (!no) return;
              setContractsInitialContractNo(no);
              void handleModuleChange("contracts");
            }}
          />
        );
      case "counters":
        return <CountersPage />;
      case "tenants":
        return <TenantsPage selectedStoreId={selectedStoreId ?? undefined} />;
      case "floors":
        return <FloorsPage />;
      case "base-maps":
        return <BaseMapsPage />;
      case "unit-map-versions":
        return <UnitMapVersionsPage />;
      case "business-units":
        return <BusinessUnitsPage />;
      case "floor-area-report":
        return <FloorAreaReportPage />;
      case "brands":
        return <BrandsPage />;
      case "suppliers":
        return <SuppliersPage />;
      case "manaframe":
        return <ManaframePage />;
      case "contracts":
        return (
          <ContractsPage
            openContractNoOnMount={contractsInitialContractNo}
            onOpenContractNoConsumed={handleContractsJumpConsumed}
          />
        );
      case "sales-dashboard":
        return <SalesDashboardPage />;
      case "activity-analysis":
        return <ActivityAnalysisPage />;
      case "commodity-sales-detail":
        return <CommoditySalesDetailReportPage />;
      case "decorations":
        return <DecorationsPage initialTab="projects" />;
      case "decorations-todos":
        return <DecorationsPage initialTab="todos" />;
      case "joint-settlement":
        return <JointSettlementStatementsPage />;
      case "user-role-scope":
        return <SystemConfigPage initialTab="users" />;
      case "users":
        return <SystemConfigPage initialTab="users" />;
      case "roles":
        return <SystemConfigPage initialTab="roles" />;
      case "departments":
        return <SystemConfigPage initialTab="departments" />;
      case "contract-permissions":
        return <SystemConfigPage initialTab="contract-permissions" />;
      case "audit-logs":
        return <SystemConfigPage initialTab="audit-logs" />;
      default:
        return (
          <SystemOverview
            onModuleChange={handleModuleChange}
            onNavigateToContractDetail={(contractNo) => {
              const no = contractNo.trim();
              if (!no) return;
              setContractsInitialContractNo(no);
              void handleModuleChange("contracts");
            }}
          />
        );
    }
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const { toast } = useToast();

  const exitFullscreenSafely = () => {
    if (!document.fullscreenElement) return Promise.resolve(true);

    return new Promise<boolean>((resolve) => {
      let settled = false;
      let timeoutId: number | undefined;

      const finish = (result: boolean) => {
        if (settled) return;
        settled = true;
        if (timeoutId !== undefined) window.clearTimeout(timeoutId);
        document.removeEventListener("fullscreenchange", handleFullscreenChange);
        resolve(result);
      };

      const handleFullscreenChange = () => {
        if (!document.fullscreenElement) finish(true);
      };

      document.addEventListener("fullscreenchange", handleFullscreenChange);
      timeoutId = window.setTimeout(() => {
        finish(!document.fullscreenElement);
      }, 1500);

      try {
        const result = document.exitFullscreen();
        if (result && typeof result.then === "function") {
          result.catch(() => finish(!document.fullscreenElement));
        }
      } catch {
        finish(!document.fullscreenElement);
      }
    });
  };

  // 切换模块：非全屏时直接切换；全屏时先退出全屏再切换
  const handleModuleChange = async (moduleId: string) => {
    if (document.fullscreenElement) {
      const exited = await exitFullscreenSafely();
      if (!exited) {
        toast({
          title: "请先退出全屏",
          description: "当前全屏未能自动退出，请按 Esc 退出全屏后再切换模块。",
          variant: "destructive",
        });
        return;
      }
    }
    recordModuleAccess(moduleId);
    setActiveModule(moduleId);
  };

  const handleMobileModuleChange = async (moduleId: string) => {
    await handleModuleChange(moduleId);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row" data-testid="main-dashboard">
      <div className="hidden shrink-0 md:flex">
        <NavigationSidebar
          activeModule={activeModule}
          onModuleChange={handleModuleChange}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={handleToggleSidebar}
          className="h-screen"
        />
      </div>

      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-[86vw] max-w-[22rem] p-0 sm:max-w-sm [&>button]:text-white [&>button]:hover:text-slate-200">
          <SheetHeader className="sr-only">
            <SheetTitle>移动端导航</SheetTitle>
          </SheetHeader>
          <NavigationSidebar
            activeModule={activeModule}
            onModuleChange={handleMobileModuleChange}
            className="h-full w-full"
          />
        </SheetContent>
      </Sheet>

      <main className="min-w-0 flex-1 overflow-auto" data-testid="main-content">
        {/* 顶部栏：桌面显示账号信息，手机显示菜单和当前模块 */}
        <div className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b bg-white px-4 py-3 md:px-6 md:py-4">
          <div className="flex min-w-0 items-center gap-3 md:hidden">
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9 shrink-0"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="打开导航菜单"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-900">百货柜位管理系统</div>
              <div className="truncate text-xs text-muted-foreground">{MODULE_LABELS[activeModule] || activeModule}</div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="min-w-0 text-right">
              <div className="max-w-[5rem] truncate text-sm font-medium text-slate-900 sm:max-w-none">{user?.real_name || user?.username}</div>
              <div className="hidden text-xs text-muted-foreground sm:block">{user?.role_names?.join(" / ") || "已登录"}</div>
            </div>
            <Button variant="outline" size="sm" onClick={() => logout()}>
              退出登录
            </Button>
          </div>
        </div>

        {/* key 强制按模块完整卸载再挂载；错误边界兜底 removeChild 等异常 */}
        <ContentErrorBoundary activeModule={activeModule}>
          <div key={activeModule} className="min-h-0 flex-1">
            {renderContent()}
          </div>
        </ContentErrorBoundary>
      </main>
    </div>
  );
}
