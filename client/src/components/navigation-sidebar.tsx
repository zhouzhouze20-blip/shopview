import { useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Check, ChevronDown, ChevronLeft, Eye, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { APP_BRAND } from "@/lib/app-branding";
import { APP_VERSION } from "@/lib/app-version";
import { filterAccessibleModuleTree, isAdminUser } from "@/lib/module-permissions";
import { filterAdminViewUsers, getNextAdminViewSearchState } from "@/lib/admin-view-search";
import { navigationItems } from "@/lib/navigation-items";

interface NavigationSidebarProps {
  activeModule?: string;
  onModuleChange?: (moduleId: string) => void | Promise<void>;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
}

export default function NavigationSidebar({ activeModule = "dashboard", onModuleChange, isCollapsed = false, onToggleCollapse, className }: NavigationSidebarProps) {
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [adminViewSearchInput, setAdminViewSearchInput] = useState("");
  const [adminViewSearchKeyword, setAdminViewSearchKeyword] = useState("");
  const [adminViewOpen, setAdminViewOpen] = useState(false);
  const adminViewSearchComposingRef = useRef(false);
  const { user, menuUser, adminViewUsers, adminViewUser, adminViewLoading, setAdminViewUserId } = useAuth();
  const visibleNavigationItems = useMemo(() => filterAccessibleModuleTree(navigationItems, menuUser), [menuUser]);
  const canUseAdminView = isAdminUser(user);
  const adminViewOptions = useMemo(
    () => adminViewUsers.filter((candidate) => candidate.user_id !== user?.user_id),
    [adminViewUsers, user?.user_id],
  );
  const filteredAdminViewOptions = useMemo(() => {
    return filterAdminViewUsers(adminViewOptions, adminViewSearchKeyword);
  }, [adminViewOptions, adminViewSearchKeyword]);

  const selectedAdminViewLabel = adminViewUser
    ? adminViewUser.real_name || adminViewUser.username
    : "退出代看，查看管理员菜单";

  const handleAdminViewSearchChange = (value: string) => {
    setAdminViewSearchKeyword((currentKeyword) => {
      const next = getNextAdminViewSearchState({
        currentKeyword,
        inputValue: value,
        isComposing: adminViewSearchComposingRef.current,
      });
      setAdminViewSearchInput(next.inputText);
      return next.keyword;
    });
  };

  const handleAdminViewSelect = (userId: number | null) => {
    setAdminViewUserId(userId);
    setAdminViewOpen(false);
    setAdminViewSearchInput("");
    setAdminViewSearchKeyword("");
  };

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleItemClick = (itemId: string, hasSubItems: boolean) => {
    if (hasSubItems) {
      toggleExpanded(itemId);
    } else {
      onModuleChange?.(itemId);
    }
  };

  if (isCollapsed) {
    return (
      <nav className={cn("w-16 bg-slate-900 text-white flex flex-col", className)} data-testid="navigation-sidebar-collapsed">
        <div className="p-4 border-b border-slate-800 flex justify-center">
          <button
            onClick={onToggleCollapse}
            className="text-white hover:text-slate-300 transition-colors"
            data-testid="expand-sidebar-btn"
          >
            <ChevronLeft className="w-6 h-6 rotate-180" />
          </button>
        </div>
        <div className="flex-1 py-4">
          {visibleNavigationItems.map((item) => (
            <div key={item.id} className="mb-1">
              <button
                onClick={() => !item.subItems && onModuleChange?.(item.id)}
                className={`w-full flex items-center justify-center px-4 py-3 hover:bg-slate-800 transition-colors ${
                  activeModule === item.id ? "bg-slate-800 border-r-2 border-blue-500" : ""
                }`}
                data-testid={`nav-item-${item.id}-collapsed`}
                title={item.name}
              >
                <item.icon className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      </nav>
    );
  }

  return (
    <nav className={cn("w-64 bg-slate-900 text-white flex flex-col", className)} data-testid="navigation-sidebar">
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white" data-testid="text-system-title">
              {APP_BRAND.zhName}
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              {APP_BRAND.enName}
            </p>
          </div>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="text-white hover:text-slate-300 transition-colors ml-2"
              data-testid="collapse-sidebar-btn"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {visibleNavigationItems.map((item) => (
          <div key={item.id} className="mb-1">
            <button
              onClick={() => handleItemClick(item.id, !!item.subItems)}
              className={`w-full flex items-center justify-between px-6 py-3 text-left hover:bg-slate-800 transition-colors ${
                activeModule === item.id ? "bg-slate-800 border-r-2 border-blue-500" : ""
              }`}
              data-testid={`nav-item-${item.id}`}
            >
              <div className="flex items-center space-x-3">
                <item.icon className="w-5 h-5" />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
              <div className="flex items-center space-x-2">
                {item.badge && (
                  <Badge variant="secondary" className="text-xs bg-blue-600 text-white">
                    {item.badge}
                  </Badge>
                )}
                {item.subItems && (
                  <svg
                    className={`w-4 h-4 transition-transform ${
                      expandedItems.includes(item.id) ? "rotate-90" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                )}
              </div>
            </button>

            {item.subItems && expandedItems.includes(item.id) && (
              <div className="bg-slate-800">
                {item.subItems.map((subItem) => (
                  <div key={subItem.id}>
                    <button
                      onClick={() => handleItemClick(subItem.id, !!subItem.subItems)}
                      className={`w-full flex items-center justify-between px-12 py-2 text-left hover:bg-slate-700 transition-colors ${
                        activeModule === subItem.id ? "bg-slate-700 border-r-2 border-blue-400" : ""
                      }`}
                      data-testid={`nav-subitem-${subItem.id}`}
                    >
                      <div className="flex items-center">
                        <subItem.icon className="w-4 h-4 mr-3" />
                        <span className="text-sm">{subItem.name}</span>
                      </div>
                      {subItem.subItems && (
                        <svg
                          className={`w-3 h-3 transition-transform ${
                            expandedItems.includes(subItem.id) ? "rotate-90" : ""
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      )}
                    </button>
                    {subItem.subItems && expandedItems.includes(subItem.id) && (
                      <div className="bg-slate-700/50">
                        {subItem.subItems.map((leaf) => (
                          <button
                            key={leaf.id}
                            onClick={() => handleItemClick(leaf.id, false)}
                            className={`w-full flex items-center px-16 py-2 text-left hover:bg-slate-700 transition-colors ${
                              activeModule === leaf.id ? "bg-slate-700 border-r-2 border-blue-400" : ""
                            }`}
                            data-testid={`nav-subitem-${subItem.id}-${leaf.id}`}
                          >
                            <leaf.icon className="w-4 h-4 mr-3" />
                            <span className="text-sm">{leaf.name}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="p-6 border-t border-slate-800">
        {canUseAdminView && (
          <div className="mb-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
              <Eye className="h-3.5 w-3.5" />
              <span>管理员代看</span>
            </div>
            <Popover open={adminViewOpen} onOpenChange={setAdminViewOpen}>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  disabled={adminViewLoading}
                  className="h-9 w-full justify-between border-slate-700 bg-slate-950 px-3 text-left text-xs font-normal text-slate-100 hover:bg-slate-900 hover:text-white disabled:opacity-60"
                  aria-label="选择代看用户"
                >
                  <span className="truncate">{adminViewLoading ? "加载用户..." : selectedAdminViewLabel}</span>
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-60" />
                </Button>
              </PopoverTrigger>
              <PopoverContent
                align="start"
                className="w-[var(--radix-popover-trigger-width)] border border-slate-200 bg-white p-0 text-slate-900 shadow-xl"
              >
                <div className="border-b border-slate-200 p-2">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
                    <Input
                      value={adminViewSearchInput}
                      onChange={(event) => handleAdminViewSearchChange(event.target.value)}
                      onCompositionStart={() => {
                        adminViewSearchComposingRef.current = true;
                      }}
                      onCompositionEnd={(event) => {
                        adminViewSearchComposingRef.current = false;
                        handleAdminViewSearchChange(event.currentTarget.value);
                      }}
                      placeholder="搜索用户名/姓名"
                      className="h-8 pl-8 text-xs"
                    />
                  </div>
                </div>
                <div className="max-h-64 overflow-y-auto p-1">
                  <button
                    type="button"
                    onClick={() => handleAdminViewSelect(null)}
                    className="flex w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-xs text-slate-900 outline-none hover:bg-slate-100 focus:bg-slate-100"
                  >
                    <Check className={cn("h-3.5 w-3.5", !adminViewUser ? "opacity-100" : "opacity-0")} />
                    <span className="truncate">退出代看，查看管理员菜单</span>
                  </button>
                  {filteredAdminViewOptions.map((candidate) => {
                    const label = candidate.real_name || candidate.username;
                    const meta = [
                      candidate.real_name && candidate.username ? candidate.username : null,
                      candidate.role_names?.length ? candidate.role_names.join("、") : null,
                    ].filter(Boolean).join(" / ");

                    return (
                      <button
                        key={candidate.user_id}
                        type="button"
                        onClick={() => handleAdminViewSelect(candidate.user_id)}
                        className="flex w-full items-start gap-2 rounded-sm px-2 py-2 text-left text-xs text-slate-900 outline-none hover:bg-slate-100 focus:bg-slate-100"
                      >
                        <Check className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", adminViewUser?.user_id === candidate.user_id ? "opacity-100" : "opacity-0")} />
                        <span className="min-w-0">
                          <span className="block truncate">{label}</span>
                          {meta ? <span className="block truncate text-[11px] text-slate-500">{meta}</span> : null}
                        </span>
                      </button>
                    );
                  })}
                  {!filteredAdminViewOptions.length ? (
                    <div className="px-8 py-3 text-xs text-slate-500">没有匹配用户</div>
                  ) : null}
                </div>
              </PopoverContent>
            </Popover>
            {adminViewUser ? (
              <div className="rounded border border-amber-400/30 bg-amber-400/10 px-2 py-1.5 text-[11px] leading-4 text-amber-100">
                菜单和数据范围按 {adminViewUser.real_name || adminViewUser.username} 计算，登录身份仍为管理员。
              </div>
            ) : null}
          </div>
        )}
        <div className="text-xs text-slate-400">
          当前用户: {user?.real_name || user?.username || "已登录"}
        </div>
        {adminViewUser ? (
          <div className="mt-1 text-xs text-amber-200">
            代看菜单: {adminViewUser.real_name || adminViewUser.username}
          </div>
        ) : null}
        <div className="text-xs text-slate-500 mt-1">
          版本: v{APP_VERSION}
        </div>
      </div>
    </nav>
  );
}
