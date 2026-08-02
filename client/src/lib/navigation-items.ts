import type React from "react";
import { Activity, BarChart3, Building2, Calculator, CircleDollarSign, CreditCard, FileSpreadsheet, FileText, FolderClosed, HardHat, Settings, Shield, Target, TicketPercent, Truck, Users, Warehouse } from "lucide-react";

export interface NavigationItem {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  subItems?: NavigationItem[];
}

export const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    name: "经营概览",
    icon: BarChart3,
    badge: "主页",
  },
  {
    id: "decoration-management",
    name: "装修管理",
    icon: HardHat,
    subItems: [
      { id: "decorations", name: "装修项目", icon: HardHat },
      { id: "decorations-todos", name: "装修待办", icon: FileText },
    ],
  },
  {
    id: "tenant-management",
    name: "品牌/商户管理",
    icon: Users,
    subItems: [
      { id: "manaframe", name: "柜位定义", icon: Building2 },
      { id: "suppliers", name: "供应商管理", icon: Truck },
    ],
  },
  {
    id: "contract-management",
    name: "合同管理",
    icon: FileText,
    subItems: [
      { id: "contracts", name: "合同台账", icon: FileText },
      { id: "contract-unit-bindings", name: "合同柜位绑定", icon: Building2 },
    ],
  },
  {
    id: "sales-management",
    name: "销售管理",
    icon: BarChart3,
    subItems: [
      { id: "sales-dashboard", name: "销售看板", icon: BarChart3 },
      { id: "category-performance", name: "品类主管绩效", icon: Target },
      {
        id: "activity-analysis-group",
        name: "活动分析",
        icon: TicketPercent,
        subItems: [
          { id: "activity-analysis", name: "通用活动分析", icon: TicketPercent },
          { id: "points-activity-analysis", name: "中心年中庆活动", icon: Calculator },
          { id: "star-diamond-analysis", name: "中心星钻会员", icon: Users },
        ],
      },
      {
        id: "member-analysis-group",
        name: "会员经营分析",
        icon: Users,
        subItems: [
          { id: "brand-member-analysis", name: "品牌会员分析", icon: Users },
        ],
      },
      {
        id: "sales-reports",
        name: "报表",
        icon: BarChart3,
        subItems: [
          {
            id: "new-century-reports",
            name: "新世纪报表",
            icon: FolderClosed,
            subItems: [
              { id: "daily-sales-followup", name: "OD0001 销售逐日跟进表", icon: FileSpreadsheet },
              { id: "od0002-sales-gross-profit", name: "OD0002 门店销售毛利汇总表", icon: FileSpreadsheet },
              { id: "od0004-monthly-followup", name: "OD0004 销售逐月跟进表", icon: FileSpreadsheet },
              { id: "od0005-micro-mall-brand-sales", name: "OD0005 微商城品牌销售统计", icon: FileSpreadsheet },
              { id: "hdyy01-group-operation-analysis", name: "HDYY01柜组经营分析表", icon: FileSpreadsheet },
            ],
          },
          {
            id: "center-reports",
            name: "中心报表",
            icon: FolderClosed,
            subItems: [
              { id: "daily-sales-followup", name: "OD0001 销售逐日跟进表", icon: FileSpreadsheet },
              { id: "od0002-sales-gross-profit", name: "OD0002 门店销售毛利汇总表", icon: FileSpreadsheet },
              { id: "od0003-center-sales-followup", name: "OD0003 中心销售跟进表", icon: FileSpreadsheet },
              { id: "od0004-monthly-followup", name: "OD0004 销售逐月跟进表", icon: FileSpreadsheet },
              { id: "od0005-micro-mall-brand-sales", name: "OD0005 微商城品牌销售统计", icon: FileSpreadsheet },
              { id: "hy0001-key-brand-member", name: "HY0001 重点品牌会员消费情况", icon: FileSpreadsheet },
              { id: "hdyy01-group-operation-analysis", name: "HDYY01柜组经营分析表", icon: FileSpreadsheet },
            ],
          },
          {
            id: "building-reports",
            name: "大楼报表",
            icon: FolderClosed,
            subItems: [
              { id: "daily-sales-followup", name: "OD0001 销售逐日跟进表", icon: FileSpreadsheet },
              { id: "od0002-sales-gross-profit", name: "OD0002 门店销售毛利汇总表", icon: FileSpreadsheet },
              { id: "od0004-monthly-followup", name: "OD0004 销售逐月跟进表", icon: FileSpreadsheet },
              { id: "od0005-micro-mall-brand-sales", name: "OD0005 微商城品牌销售统计", icon: FileSpreadsheet },
              { id: "hdyy01-group-operation-analysis", name: "HDYY01柜组经营分析表", icon: FileSpreadsheet },
              { id: "non-rental-monthly-revenue", name: "非租赁品牌月度收益表", icon: FileSpreadsheet },
            ],
          },
          {
            id: "other-reports",
            name: "其他",
            icon: FolderClosed,
            subItems: [
              { id: "commodity-sales-detail", name: "商品销售明细", icon: FileText },
              { id: "settled-gross-profit-ranking", name: "结算后销售毛利排行表", icon: FileSpreadsheet },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "inventory-management",
    name: "库存管理",
    icon: Warehouse,
    subItems: [
      { id: "inventory-detail", name: "实时库存查询", icon: FileSpreadsheet },
      { id: "historical-inventory-detail", name: "历史库存明细报表", icon: FileSpreadsheet },
      { id: "inventory-movement-detail", name: "进销存明细报表", icon: FileSpreadsheet },
    ],
  },
  {
    id: "financial-management",
    name: "财务管理",
    icon: CreditCard,
    subItems: [
      { id: "merchant-planning", name: "招商规划", icon: Target },
      {
        id: "revenue-management",
        name: "收益管理",
        icon: CircleDollarSign,
        subItems: [
          { id: "revenue-map", name: "收益地图", icon: CircleDollarSign },
          { id: "revenue-dashboard", name: "收益看板", icon: BarChart3 },
        ],
      },
      { id: "joint-renewal-revenue", name: "联营续签收益分析", icon: FileSpreadsheet },
      { id: "joint-settlement", name: "联营结算单管理", icon: FileSpreadsheet },
      {
        id: "activity-settlement",
        name: "活动结算",
        icon: TicketPercent,
        subItems: [
          { id: "voucher-match", name: "凭证匹配", icon: FileSpreadsheet },
          { id: "confirmed-revenue-daily", name: "确认收入占比", icon: CircleDollarSign },
          { id: "coupon-monthly-balance", name: "卡券月结", icon: CircleDollarSign },
        ],
      },
    ],
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
          { id: "floor-area-report", name: "楼层在营及空置面积报表", icon: BarChart3 },
        ],
      },
      { id: "user-role-scope", name: "用户角色及范围定义", icon: Users },
      { id: "wecom-rules", name: "企微授权规则", icon: Shield },
      { id: "audit-logs", name: "日志查询", icon: Activity },
    ],
  },
];
