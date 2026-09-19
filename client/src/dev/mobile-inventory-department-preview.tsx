import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import MobileInventoryPage from "@/pages/mobile-inventory";
import "@/index.css";

const options = [
  { value: "D1", code: "D1", name: "化妆品部", label: "[D1] 化妆品部" },
  { value: "D2", code: "D2", name: "运动部", label: "[D2] 运动部" },
  { value: "EMPTY", code: "EMPTY", name: "空库存测试", label: "[EMPTY] 空库存测试" },
  { value: "ERROR", code: "ERROR", name: "异常测试", label: "[ERROR] 异常测试" },
];
const fixtureRows = Array.from({ length: 51 }, (_, index) => ({
  store_code: "601", store_display: "[601] 测试门店",
  supplier_code: `S${index}`, supplier_display: `[S${index}] ${index === 0 ? "测试香水化妆品（上海）有限公司" : "测试供应商"}`,
  group_code: `G${index}`, group_name: index === 0 ? "Christian dior迪奥厅" : "测试柜组",
  group_display: `[G${index}] ${index === 0 ? "Christian dior迪奥厅" : "测试柜组"}`,
  inventory_quantity: index === 0 ? 5954 : 10,
  retail_amount: index === 0 ? 595400 : 1000,
}));

window.fetch = async (input) => {
  const url = new URL(String(input), window.location.origin);
  let data: unknown = {};
  if (url.pathname === "/api/auth/me") data = {
    user_id: -1, username: "inventory-qa", status: "active", is_active: true,
    role_codes: [], role_names: [], permission_codes: ["mobile.inventory.view", "sales.inventory.view"],
  };
  else if (url.pathname.endsWith("inventory-departments")) data = { options };
  else if (url.pathname.endsWith("inventory-department-summary")) {
    const department = url.searchParams.get("department_code");
    if (department === "ERROR") return new Response(JSON.stringify({ detail: "模拟查询失败" }), { status: 503 });
    const offset = Number(url.searchParams.get("offset"));
    const rows = department === "EMPTY" ? [] : department === "D2" ? [{ ...fixtureRows[1], group_code: "SPORT", group_name: "运动柜组", group_display: "[SPORT] 运动柜组" }] : fixtureRows;
    data = {
      department_code: department, rows: rows.slice(offset, offset + 50), offset, limit: 50,
      summary: { total_count: rows.length, inventory_quantity: rows.reduce((s, row) => s + row.inventory_quantity, 0), retail_amount: rows.reduce((s, row) => s + row.retail_amount, 0) },
      source_note: "模拟数据，仅用于交互验证；金额按零售价合计。钻取显示所选柜组全部正库存明细。",
    };
  } else if (url.pathname.endsWith("inventory-detail")) {
    const code = url.searchParams.get("exact_group");
    const row = fixtureRows.find((item) => item.group_code === code) ?? fixtureRows[1];
    data = {
      rows: [{ goods_code: "TEST01", goods_name: "测试商品", barcode: "123456789", group_display: `[${code}] 测试柜组`, supplier_display: row.supplier_display, inventory_quantity: row.inventory_quantity, retail_amount: row.retail_amount, selling_price: 100, subinventory_display: "[1] 柜台" }],
      summary: { total_count: 1, inventory_quantity: row.inventory_quantity, retail_amount: row.retail_amount },
      limit: 200, offset: 0, source_note: `模拟数据，精确柜组：${code}`,
    };
  } else if (url.pathname.endsWith("inventory-detail/options")) data = { options: [] };
  return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
};

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}><AuthProvider><div className="bg-amber-100 px-4 py-1 text-xs">交互验证 · 模拟数据</div><MobileInventoryPage /></AuthProvider></QueryClientProvider>,
);
