import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Building2, Users, FileText, CreditCard, BarChart3, Settings, ChevronLeft, Truck, HardHat, FileSpreadsheet, Activity } from "lucide-react";

interface NavigationItem {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  subItems?: NavigationItem[];
}

const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    name: "经营概览",
    icon: BarChart3,
    badge: "主页"
  },
  {
    id: "decoration-management",
    name: "装修管理",
    icon: HardHat,
    subItems: [
      { id: "decorations", name: "装修项目", icon: HardHat },
      { id: "decorations-todos", name: "装修待办", icon: FileText }
    ]
  },
  {
    id: "tenant-management",
    name: "品牌/商户管理",
    icon: Users,
    subItems: [
      { id: "manaframe", name: "柜位定义", icon: Building2 },
      { id: "suppliers", name: "供应商管理", icon: Truck }
    ]
  },
  {
    id: "contract-management",
    name: "合同管理",
    icon: FileText,
    subItems: [
      { id: "contracts", name: "合同台账", icon: FileText }
    ]
  },
  {
    id: "sales-management",
    name: "销售管理",
    icon: BarChart3,
    subItems: [
      { id: "sales-dashboard", name: "销售看板", icon: BarChart3 },
      {
        id: "sales-reports",
        name: "报表",
        icon: BarChart3,
        subItems: [{ id: "commodity-sales-detail", name: "商品销售明细", icon: FileText }],
      },
    ],
  },
  {
    id: "financial-management",
    name: "财务管理",
    icon: CreditCard,
    subItems: [{ id: "joint-settlement", name: "联营结算单管理", icon: FileSpreadsheet }]
  },
  {
    id: "system-management",
    name: "系统管理",
    icon: Settings,
    subItems: [
      {
        id: "floor-base-definitions",
        name: "楼层基础定义",
        icon: Building2,
        subItems: [
          { id: "floors", name: "楼层定义", icon: Building2 },
          { id: "base-maps", name: "底图管理", icon: Building2 },
          { id: "unit-map-versions", name: "柜位图版本", icon: Building2 },
          { id: "business-units", name: "经营单元设置", icon: Building2 },
          { id: "floor-area-report", name: "楼层面积报表", icon: BarChart3 },
        ],
      },
      { id: "user-role-scope", name: "用户角色及范围定义", icon: Users },
      { id: "audit-logs", name: "日志查询", icon: Activity }
    ]
  }
];

interface NavigationSidebarProps {
  activeModule?: string;
  onModuleChange?: (moduleId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function NavigationSidebar({ activeModule = "dashboard", onModuleChange, isCollapsed = false, onToggleCollapse }: NavigationSidebarProps) {
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

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
      <nav className="w-16 bg-slate-900 text-white flex flex-col" data-testid="navigation-sidebar-collapsed">
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
          {navigationItems.map((item) => (
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
    <nav className="w-64 bg-slate-900 text-white flex flex-col" data-testid="navigation-sidebar">
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white" data-testid="text-system-title">
              百货柜位管理系统
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Department Store Management
            </p>
          </div>
          <button
            onClick={onToggleCollapse}
            className="text-white hover:text-slate-300 transition-colors ml-2"
            data-testid="collapse-sidebar-btn"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {navigationItems.map((item) => (
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
        <div className="text-xs text-slate-400">
          当前用户: 系统管理员
        </div>
        <div className="text-xs text-slate-500 mt-1">
          版本: v1.0.0
        </div>
      </div>
    </nav>
  );
}
