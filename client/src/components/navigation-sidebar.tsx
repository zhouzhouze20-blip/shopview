import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Building2, Users, FileText, CreditCard, BarChart3, Settings, Home } from "lucide-react";

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
    name: "可视化驾驶舱",
    icon: BarChart3,
    badge: "主页"
  },
  {
    id: "space-management",
    name: "铺位资源管理",
    icon: Building2,
    subItems: [
      { id: "floor-plan", name: "楼层平面图", icon: Home },
      { id: "halls", name: "厅房管理", icon: Building2 },
      { id: "floors", name: "楼层管理", icon: Building2 },
      { id: "space-assets", name: "空间资产", icon: Building2 }
    ]
  },
  {
    id: "tenant-management",
    name: "品牌/商户管理",
    icon: Users,
    subItems: [
      { id: "tenants", name: "商户档案", icon: Users },
      { id: "brands", name: "品牌档案", icon: Users }
    ]
  },
  {
    id: "contract-management",
    name: "合同管理",
    icon: FileText,
    subItems: [
      { id: "contracts", name: "合同台账", icon: FileText },
      { id: "rent-terms", name: "租金条款", icon: FileText }
    ]
  },
  {
    id: "financial-management",
    name: "财务管理",
    icon: CreditCard,
    subItems: [
      { id: "bills", name: "账单管理", icon: CreditCard },
      { id: "reports", name: "财务报表", icon: BarChart3 }
    ]
  },
  {
    id: "system-management",
    name: "系统管理",
    icon: Settings,
    subItems: [
      { id: "users", name: "用户管理", icon: Users },
      { id: "roles", name: "角色权限", icon: Settings }
    ]
  }
];

interface NavigationSidebarProps {
  activeModule?: string;
  onModuleChange?: (moduleId: string) => void;
}

export default function NavigationSidebar({ activeModule = "floor-plan", onModuleChange }: NavigationSidebarProps) {
  const [expandedItems, setExpandedItems] = useState<string[]>(["space-management"]);

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

  return (
    <nav className="w-64 bg-slate-900 text-white flex flex-col" data-testid="navigation-sidebar">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white" data-testid="text-system-title">
          商业地产资源管理系统
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Commercial Real Estate Management
        </p>
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
                  <button
                    key={subItem.id}
                    onClick={() => handleItemClick(subItem.id, false)}
                    className={`w-full flex items-center px-12 py-2 text-left hover:bg-slate-700 transition-colors ${
                      activeModule === subItem.id ? "bg-slate-700 border-r-2 border-blue-400" : ""
                    }`}
                    data-testid={`nav-subitem-${subItem.id}`}
                  >
                    <subItem.icon className="w-4 h-4 mr-3" />
                    <span className="text-sm">{subItem.name}</span>
                  </button>
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