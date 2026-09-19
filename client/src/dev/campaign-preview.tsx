// Isolated UI fixtures; not imported by the production application.
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import CouponCampaignsPage from "@/pages/activity-analysis/campaigns";
import { Toaster } from "@/components/ui/toaster";
import "@/index.css";

const campaign = { id: 1, name: "七夕四券（模拟验证）", store_code: "601", start_date: "2026-08-14", end_date: "2026-08-19", coupon_types: ["B", "E", "H", "M"], erp_activity_id: "2205", notes: "模拟数据" };
const report = { scope: campaign, generated_at: "2026-08-31T08:00:00Z", summary: { issued_members: 2, used_members: 2, net_linked_sales: 36271, net_coupon_amount: 700 },
  coupons: [{ coupon_type: "H", source_name: "后台充券", issued_count: 2, preissued_count: 1, net_linked_sales: 36271 }],
  members: [{ member_no: "TEST-001", member_level: "黑钻", issued_count: 5, use_tickets: 4, return_tickets: 3, net_linked_sales: 29800, own_store_net_sales: 29800 },
    { member_no: "TEST-002", member_level: "普通", use_tickets: 5, return_tickets: 0, net_linked_sales: 6471, own_store_net_sales: 0 }],
  member_levels: [{ member_level: "黑钻", members: 1, used_members: 1, net_linked_sales: 29800 }],
  tickets: [{ billno: "TEST-T001", coupon_type: "H", member_no: "TEST-002", checkout_member_no: "TEST-003", member_match: "不一致", ticket_kind: "销售", linked_sales: 6471 }],
  brands: [{ coupon_type: "H", brand_code: "TEST-BRAND", net_linked_sales: 36271 }], quality: { returns_linked_by_coupon_log: 1 },
  sales_lift: { status: "estimated", method: "前4周同星期参与范围基准 + 同部门非参与柜组期间校准", baseline_weeks: 4, day_count: 6,
    activity_start_date: "2026-08-14", activity_end_date: "2026-08-19",
    baseline_periods: [
      { week_no: 1, start_date: "2026-08-07", end_date: "2026-08-12" },
      { week_no: 2, start_date: "2026-07-31", end_date: "2026-08-05" },
      { week_no: 3, start_date: "2026-07-24", end_date: "2026-07-29" },
      { week_no: 4, start_date: "2026-07-17", end_date: "2026-07-22" },
    ],
    treatment_group_count: 156, mapped_treatment_group_count: 155, department_count: 9, control_group_count: 1072,
    actual_sales: 6179029.24, same_weekday_baseline_sales: 3445656.20, raw_change_rate: 79.33,
    control_actual_sales: 3428917.54, control_baseline_sales: 2121238.00, control_change_rate: 61.65,
    expected_sales: 5569799.78, estimated_increment: 609229.46, estimated_growth_rate: 10.94,
    caveats: ["试算值不是结算结果，也不能单独证明活动因果增量。", "往期活动未建档，前4周同星期可能包含未识别促销。"] },
  ownership: { status: 'unconfirmed', status_label: '候选范围，未人工确认', version: 0, fingerprint: 'a'.repeat(64),
    storage_ready: true, can_confirm: true, candidate_assets: 2, report_assets: 2, confirmed_assets: 0,
    unconfirmed_added: 2, confirmed_missing: 0, missing_erp_period: 2, conflicting_erp_period: 0, note: '',
    basis: '按门店、券种及初始发券有效期选候选资产；ERP规则编号不等于券资产归属。', change_basis: '新增候选不自动加入。' },
  member_source: { status: 'ready', source: 'CRM当前会员ODS（模拟）', matched: 2, unresolved: 0, history_basis: '当前等级不是活动时等级；历史等级尚未接入' },
  assets: [{ coupon_type: 'H', asset_id: 'TEST-A001', issue_id: 'TEST-I001', member_no: 'TEST-002', valid_from: '2026-08-14', valid_to: '2026-08-19', erp_period: '0', in_report: true }],
  coupon_flows: [{ coupon_type: 'H', asset_id: 'TEST-A001', flow_id: 'TEST-F001', action: 'O', amount: 200, flow_date: '2026-08-15', billno: 'TEST-T001', match_count: 1 }],
  brand_details: [{ billno: 'TEST-T001', coupon_type: 'H', brand_code: 'TEST-BRAND', supplier_code: 'TEST-SUPPLIER', ticket_kind: '销售', allocation: 1, linked_sales: 6471 }],
  post_activity_returns: { observed_through: '2026-09-06', return_tickets: 1, return_sales: -100, reference_net_sales: 36171,
    basis: '按原小票追溯活动后的退货。', caveat: '不改写活动期，不等于券费用或供应商应扣额。',
    details: [{ billno: 'TEST-R001', original_billno: 'TEST-T001', sale_date: '2026-08-21', brand_code: 'TEST-BRAND', supplier_code: 'TEST-SUPPLIER', sales: -100 }] },
  definitions: ["模拟交互数据，不代表真实活动结果。", "按持券人分析，销售退货沿原小票扣减。"] };
window.fetch = async (input, init) => {
  const url = new URL(String(input), window.location.origin);
  if (!url.pathname.startsWith("/api/activity-analysis/campaigns")) throw new Error("预览页不允许访问其他接口");
  if (url.pathname.endsWith("/options")) return Response.json({ stores: [{ store_code: "601", store_name: "测试门店" }], can_manage: true });
  if (url.pathname.endsWith("/refresh")) return Response.json({ detail: "模拟ERP连接未配置，旧快照保留" }, { status: 502 });
  if (url.pathname.endsWith("/report")) return Response.json(report);
  if (url.pathname.endsWith('/ownership/confirm')) {
    const payload=JSON.parse(String(init?.body));
    Object.assign(report.ownership, { status: 'confirmed', status_label: '已人工确认', version: 1, confirmed_assets: 2, unconfirmed_added: 0, note: payload.note });
    return Response.json({ version: 1 });
  }
  if (init?.method === "POST") return Response.json({ ...campaign, ...JSON.parse(String(init.body)) });
  return Response.json([campaign]);
};
createRoot(document.getElementById("root")!).render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
  <div className="bg-amber-100 p-2 text-center text-sm">模拟数据 · 仅用于页面交互验证 · 不连接业务接口</div><CouponCampaignsPage /><Toaster />
</QueryClientProvider>);
