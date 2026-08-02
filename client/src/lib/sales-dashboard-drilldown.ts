export type SalesDrilldownTab = "stores" | "departments" | "groups" | "department-products" | "tickets";

export type SalesDepartmentLike = {
  department_code?: string | null;
  department_name?: string | null;
};

export type SalesProductTicketLike = {
  goods_code?: string | null;
  barcode?: string | null;
  supplier_code?: string | null;
};

export type ReceiptProductLike = {
  name?: unknown;
  goods_name?: unknown;
  goods_code?: unknown;
  code?: unknown;
  barcode?: unknown;
};

export type ProductTicketParams = {
  goods_code?: string;
  barcode?: string;
  supplier_code?: string;
};

export function isSupermarketDepartment(department: SalesDepartmentLike | null | undefined): boolean {
  const code = String(department?.department_code ?? "").trim();
  const name = String(department?.department_name ?? "").trim();
  return /超市|生鲜/.test(name) || /^601010[46]/.test(code);
}

export function getDepartmentDrilldownTab(_department: SalesDepartmentLike | null | undefined): SalesDrilldownTab {
  return "groups";
}

export function getGroupDrilldownTab(department: SalesDepartmentLike | null | undefined): SalesDrilldownTab {
  return isSupermarketDepartment(department) ? "department-products" : "tickets";
}

export function buildProductTicketParams(product: SalesProductTicketLike | null | undefined): ProductTicketParams {
  if (!product) return {};
  const params: ProductTicketParams = {};
  const goodsCode = String(product.goods_code ?? "").trim();
  const barcode = String(product.barcode ?? "").trim();
  const supplierCode = String(product.supplier_code ?? "").trim();
  if (goodsCode) params.goods_code = goodsCode;
  if (barcode) params.barcode = barcode;
  if (supplierCode) params.supplier_code = supplierCode;
  return params;
}

export function getReceiptProductDisplay(row: ReceiptProductLike | null | undefined): {
  name: string;
  identifiers: string[];
} {
  const name = String(row?.name || row?.goods_name || row?.goods_code || row?.code || "-").trim() || "-";
  const goodsCode = String(row?.goods_code ?? row?.code ?? "").trim();
  const barcode = String(row?.barcode ?? "").trim();
  const identifiers: string[] = [];
  if (goodsCode) identifiers.push(`商品编码：${goodsCode}`);
  if (barcode && barcode !== goodsCode) identifiers.push(`条码：${barcode}`);
  return { name, identifiers };
}

type StoreScope = { store_id?: string | number | null; store_name?: string | null } | null | undefined;
type DepartmentScope = {
  department_code?: string | number | null;
  department_name?: string | null;
} | null | undefined;

function normalizeScopeName(value: unknown): string {
  return String(value ?? "").trim().replace(/（/g, "(").replace(/）/g, ")");
}

export function isCosmeticsRetailPriceScope(store: StoreScope, department: DepartmentScope): boolean {
  if (!store || !department) return false;
  const storeId = String(store.store_id ?? "").trim();
  const departmentCode = String(department.department_code ?? "").trim();
  const storeName = normalizeScopeName(store.store_name);
  const departmentName = normalizeScopeName(department.department_name);

  const isShoppingCenterCosmetics =
    (["1", "601"].includes(storeId) || storeName === "常州购物中心") &&
    (departmentCode === "6010101" || departmentName === "中心一部(化妆)");
  const isNewCenturyCosmetics =
    (["3", "603"].includes(storeId) || ["常州新世纪", "常州新世纪商城"].includes(storeName)) &&
    (departmentCode === "6030101" || departmentName === "新世纪一部(化妆)");

  return isShoppingCenterCosmetics || isNewCenturyCosmetics;
}
