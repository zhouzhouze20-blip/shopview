import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Barcode,
  Boxes,
  Camera,
  Factory,
  LayoutGrid,
  Loader2,
  MapPin,
  PackageSearch,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import { useLocation } from "wouter";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { MobileInventoryDepartment, type DepartmentInventoryRow } from "@/components/mobile-inventory-department";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/contexts/AuthContext";
import { useModuleAccessLog } from "@/hooks/use-module-access-log";
import { apiGet } from "@/lib/api";
import { canAccessModule } from "@/lib/module-permissions";
import {
  normalizeScannedBarcode,
  ScanCancelledError,
  tryWeComBarcodeScan,
} from "@/lib/wecom-barcode-scan";

type InventoryRow = {
  store_display: string;
  floor_display: string;
  area_display: string;
  goods_code: string;
  barcode: string;
  brand_display: string;
  goods_name: string;
  specification: string | null;
  supplier_display: string;
  operation_method: string;
  group_display: string;
  subinventory_display: string;
  inventory_quantity: number;
  selling_price: number | null;
  retail_amount: number | null;
};

type InventoryLookupResponse = {
  query_code?: string;
  rows: InventoryRow[];
  summary: {
    total_count: number;
    inventory_quantity: number;
    retail_amount: number;
  };
  limit: number;
  offset: number;
  source_note: string;
};

type InventoryFilterOption = {
  value: string;
  label: string;
  code: string;
  name: string;
};

type InventoryFilterOptionsResponse = {
  options: InventoryFilterOption[];
};

type ScannerControls = { stop: () => void };
const SUPPLIER_PAGE_SIZE = 200;
const GROUP_PAGE_SIZE = 200;

const formatNumber = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(Number(value));
};

const formatSellingCalculation = (row: InventoryRow) => {
  if (row.selling_price === null || row.selling_price === undefined) return "—";
  const unitPrice = Number(row.selling_price);
  const quantity = Number(row.inventory_quantity);
  if (!Number.isFinite(unitPrice) || !Number.isFinite(quantity)) return "—";
  return `¥${formatNumber(unitPrice, 2)} × ${formatNumber(quantity, 4)} = ¥${formatNumber(unitPrice * quantity, 2)}`;
};

export default function MobileInventoryPage() {
  const { menuUser } = useAuth();
  const [, setLocation] = useLocation();
  const hasAccess = canAccessModule(menuUser, "mobile-inventory");
  const [activeTab, setActiveTab] = useState("product");
  const [inputCode, setInputCode] = useState("");
  const [submittedCode, setSubmittedCode] = useState("");
  const [supplierInput, setSupplierInput] = useState("");
  const [submittedSupplier, setSubmittedSupplier] = useState("");
  const [supplierError, setSupplierError] = useState<string | null>(null);
  const [groupInput, setGroupInput] = useState("");
  const [debouncedGroupInput, setDebouncedGroupInput] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<InventoryFilterOption | null>(null);
  const [submittedGroup, setSubmittedGroup] = useState<InventoryFilterOption | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [fromDepartment, setFromDepartment] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [scanStarting, setScanStarting] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const { recordQuery } = useModuleAccessLog({
    moduleId: "mobile-inventory",
    moduleName: "手机端实时库存查询",
    clientType: "mobile",
    enabled: hasAccess,
  });

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ exact_code: submittedCode, limit: "500" });
    return params.toString();
  }, [submittedCode]);

  const inventoryQuery = useQuery<InventoryLookupResponse>({
    queryKey: ["/api/sales/reports/inventory-lookup", queryString],
    queryFn: () => apiGet(`/api/sales/reports/inventory-lookup?${queryString}`),
    enabled: hasAccess && Boolean(submittedCode),
  });
  const refetchInventory = inventoryQuery.refetch;

  const supplierQuery = useInfiniteQuery<InventoryLookupResponse>({
    queryKey: ["/api/sales/reports/inventory-detail", "mobile-supplier", submittedSupplier],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({
        supplier: submittedSupplier,
        limit: String(SUPPLIER_PAGE_SIZE),
        offset: String(Number(pageParam) || 0),
      });
      return apiGet(`/api/sales/reports/inventory-detail?${params.toString()}`);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = Number(lastPage.offset || 0) + lastPage.rows.length;
      return nextOffset < Number(lastPage.summary.total_count || 0) ? nextOffset : undefined;
    },
    enabled: hasAccess && Boolean(submittedSupplier),
  });

  const supplierRows = useMemo(
    () => supplierQuery.data?.pages.flatMap((page) => page.rows) ?? [],
    [supplierQuery.data?.pages],
  );
  const supplierSummary = supplierQuery.data?.pages[0]?.summary;
  const supplierGroups = useMemo(() => {
    const groups = new Map<string, { supplier: string; rows: InventoryRow[]; quantity: number }>();
    supplierRows.forEach((row) => {
      const supplier = row.supplier_display || "未标记供应商";
      const current = groups.get(supplier) ?? { supplier, rows: [], quantity: 0 };
      current.rows.push(row);
      current.quantity += Number(row.inventory_quantity || 0);
      groups.set(supplier, current);
    });
    return Array.from(groups.values());
  }, [supplierRows]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedGroupInput(groupInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [groupInput]);

  const groupOptionsQuery = useQuery<InventoryFilterOptionsResponse>({
    queryKey: [
      "/api/sales/reports/inventory-detail/options",
      "mobile-group",
      debouncedGroupInput,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        field: "group",
        q: debouncedGroupInput,
        limit: "20",
      });
      return apiGet(`/api/sales/reports/inventory-detail/options?${params.toString()}`);
    },
    enabled:
      hasAccess &&
      activeTab === "group" &&
      Boolean(debouncedGroupInput) &&
      debouncedGroupInput === groupInput.trim() &&
      selectedGroup?.label !== groupInput.trim(),
  });

  const groupQuery = useInfiniteQuery<InventoryLookupResponse>({
    queryKey: [
      "/api/sales/reports/inventory-detail",
      "mobile-group",
      submittedGroup?.value ?? "",
    ],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({
        exact_group: submittedGroup?.value ?? "",
        limit: String(GROUP_PAGE_SIZE),
        offset: String(Number(pageParam) || 0),
      });
      return apiGet(`/api/sales/reports/inventory-detail?${params.toString()}`);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = Number(lastPage.offset || 0) + lastPage.rows.length;
      return nextOffset < Number(lastPage.summary.total_count || 0) ? nextOffset : undefined;
    },
    enabled: hasAccess && Boolean(submittedGroup?.value),
  });

  const groupRows = useMemo(
    () => groupQuery.data?.pages.flatMap((page) => page.rows) ?? [],
    [groupQuery.data?.pages],
  );
  const groupSummary = groupQuery.data?.pages[0]?.summary;
  const openDepartmentGroup = (row: DepartmentInventoryRow) => {
    const option = { value: row.group_code, code: row.group_code, name: row.group_name, label: row.group_display };
    setSelectedGroup(option);
    setGroupInput(option.label);
    setGroupError(null);
    setFromDepartment(true);
    setActiveTab("group");
    recordQuery({ query_type: "group_inventory", group_code: row.group_code, source: "department_inventory" });
    if (submittedGroup?.value === option.value) void groupQuery.refetch();
    else setSubmittedGroup(option);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const groupSupplierGroups = useMemo(() => {
    const groups = new Map<string, { supplier: string; rows: InventoryRow[]; quantity: number }>();
    groupRows.forEach((row) => {
      const supplier = row.supplier_display || "未标记供应商";
      const current = groups.get(supplier) ?? { supplier, rows: [], quantity: 0 };
      current.rows.push(row);
      current.quantity += Number(row.inventory_quantity || 0);
      groups.set(supplier, current);
    });
    return Array.from(groups.values());
  }, [groupRows]);

  const submitCode = useCallback((rawCode?: string) => {
    const normalized = normalizeScannedBarcode(rawCode ?? inputCode);
    if (!normalized) {
      setScanError("请输入商品条码后再查询");
      return;
    }
    setInputCode(normalized);
    setScanError(null);
    recordQuery({ query_type: "product_inventory", barcode: normalized });
    if (normalized === submittedCode) {
      void refetchInventory();
    } else {
      setSubmittedCode(normalized);
    }
  }, [inputCode, recordQuery, refetchInventory, submittedCode]);

  const startScan = async () => {
    if (!hasAccess || scanStarting) return;
    setScanStarting(true);
    setScanError(null);
    try {
      const wecomBarcode = await tryWeComBarcodeScan();
      if (wecomBarcode) {
        submitCode(wecomBarcode);
        return;
      }
      setCameraOpen(true);
    } catch (error) {
      if (error instanceof ScanCancelledError) return;
      setCameraOpen(true);
    } finally {
      setScanStarting(false);
    }
  };

  const submitSupplier = () => {
    const normalized = supplierInput.trim();
    if (!normalized) {
      setSupplierError("请输入供应商编码或名称后再查询");
      return;
    }
    setSupplierInput(normalized);
    setSupplierError(null);
    recordQuery({ query_type: "supplier_inventory", supplier_name: normalized });
    if (normalized === submittedSupplier) {
      void supplierQuery.refetch();
    } else {
      setSubmittedSupplier(normalized);
    }
  };

  const submitGroup = () => {
    if (!selectedGroup) {
      setGroupError("请先从匹配结果中选择一个柜组");
      return;
    }
    setGroupError(null);
    recordQuery({
      query_type: "group_inventory",
      group_code: selectedGroup.code || selectedGroup.value,
      group_name: selectedGroup.name || selectedGroup.label,
    });
    if (selectedGroup.value === submittedGroup?.value) {
      void groupQuery.refetch();
    } else {
      setSubmittedGroup(selectedGroup);
    }
  };

  useEffect(() => {
    if (!cameraOpen || !videoRef.current) return;
    let active = true;
    let scannerControls: ScannerControls | null = null;

    const startCamera = async () => {
      try {
        const { BrowserMultiFormatReader } = await import("@zxing/browser");
        if (!active || !videoRef.current) return;
        const reader = new BrowserMultiFormatReader();
        scannerControls = await reader.decodeFromConstraints(
          { audio: false, video: { facingMode: { ideal: "environment" } } },
          videoRef.current,
          (result, _error, controls) => {
            if (!active || !result) return;
            controls.stop();
            const barcode = normalizeScannedBarcode(result.getText());
            if (barcode) {
              setCameraOpen(false);
              submitCode(barcode);
            }
          },
        );
      } catch (error) {
        if (!active) return;
        const reason = error instanceof Error ? error.name : "CameraError";
        setScanError(
          reason === "NotAllowedError"
            ? "未获得摄像头权限，请在手机设置中允许访问，或改用手工输入"
            : "摄像头无法启动，请确认使用 HTTPS 或改用手工输入",
        );
        setCameraOpen(false);
      }
    };
    void startCamera();

    return () => {
      active = false;
      scannerControls?.stop();
      const stream = videoRef.current?.srcObject;
      if (stream instanceof MediaStream) stream.getTracks().forEach((track) => track.stop());
    };
  }, [cameraOpen, submitCode]);

  if (!hasAccess) {
    return (
      <main className="min-h-[100dvh] bg-slate-100 p-4 text-slate-900">
        <Button variant="ghost" className="mb-3" onClick={() => setLocation("/mobile")}>
          <ArrowLeft className="mr-2 h-4 w-4" />返回工作台
        </Button>
        <Card className="rounded-3xl border-0 shadow-lg">
          <CardContent className="px-6 py-12 text-center">
            <ShieldCheck className="mx-auto h-10 w-10 text-slate-400" />
            <div className="mt-4 font-semibold">暂无库存查询权限</div>
            <div className="mt-2 text-sm text-slate-500">请联系管理员同时开通“手机端实时库存查询”和“查看实时库存查询”权限。</div>
          </CardContent>
        </Card>
      </main>
    );
  }

  const rows = inventoryQuery.data?.rows ?? [];
  const firstRow = rows[0];
  const summary = inventoryQuery.data?.summary;

  return (
    <main className="min-h-[100dvh] bg-slate-100 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950 px-4 pb-4 pt-[max(0.75rem,env(safe-area-inset-top))] text-white shadow-sm">
        <div className="mx-auto flex max-w-xl items-center gap-3">
          <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={() => setLocation("/mobile")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="text-[10px] tracking-[0.16em] text-cyan-300">SHOPVIEW</div>
            <h1 className="text-lg font-semibold">库存查询</h1>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-xl px-4 pt-4">
        <Tabs
          value={activeTab}
          onValueChange={(value) => {
            setActiveTab(value);
            if (value !== "product") setCameraOpen(false);
          }}
        >
          <TabsList className="grid h-12 w-full grid-cols-4 rounded-2xl bg-slate-200 p-1">
            <TabsTrigger value="product" className="h-10 rounded-xl px-1 text-xs data-[state=active]:bg-white data-[state=active]:text-teal-800 sm:text-sm">单品查询</TabsTrigger>
            <TabsTrigger value="supplier" className="h-10 rounded-xl px-1 text-xs data-[state=active]:bg-white data-[state=active]:text-teal-800 sm:text-sm">供应商查询</TabsTrigger>
            <TabsTrigger value="group" className="h-10 rounded-xl px-1 text-xs data-[state=active]:bg-white data-[state=active]:text-teal-800 sm:text-sm">柜组查询</TabsTrigger>
            <TabsTrigger value="department" className="h-10 rounded-xl px-1 text-xs data-[state=active]:bg-white data-[state=active]:text-teal-800 sm:text-sm">部门查询</TabsTrigger>
          </TabsList>

          <TabsContent value="department" forceMount className="data-[state=inactive]:hidden">
            <MobileInventoryDepartment
              key={menuUser?.user_id}
              active={activeTab === "department" && hasAccess}
              userId={menuUser?.user_id}
              onDrilldown={openDepartmentGroup}
              onQuery={(department) => recordQuery({ query_type: "department_inventory", department_code: department.value, department_name: department.name })}
            />
          </TabsContent>

          <TabsContent value="product" className="space-y-4">
            <Card className="rounded-3xl border-0 shadow-md">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base"><PackageSearch className="h-5 w-5 text-cyan-700" />单品库存</CardTitle>
                <CardDescription>手工输入商品条码，或者调用摄像头扫描条形码。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="text-xs font-medium text-slate-600" htmlFor="mobile-inventory-code">商品条码/商品编码</label>
                <div className="flex gap-2">
                  <Input
                    id="mobile-inventory-code"
                    inputMode="numeric"
                    autoComplete="off"
                    enterKeyHint="search"
                    className="h-12 flex-1 rounded-xl text-base"
                    placeholder="请输入或扫描商品条码"
                    value={inputCode}
                    onChange={(event) => setInputCode(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") submitCode();
                    }}
                  />
                  <Button type="button" variant="outline" className="h-12 rounded-xl px-4" onClick={startScan} disabled={scanStarting}>
                    {scanStarting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Camera className="h-5 w-5" />}
                    <span className="sr-only">开始扫码</span>
                  </Button>
                </div>
                <Button className="h-11 w-full rounded-xl bg-cyan-700 hover:bg-cyan-800" onClick={() => submitCode()} disabled={inventoryQuery.isFetching}>
                  {inventoryQuery.isFetching ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                  查询库存
                </Button>
                {scanError && (
                  <div role="alert" className="flex gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{scanError}
                  </div>
                )}
              </CardContent>
            </Card>

            {!submittedCode ? (
              <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
                <Barcode className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                输入完整条码或点击摄像头按钮开始扫码
              </div>
            ) : inventoryQuery.isLoading ? (
              <div className="flex items-center justify-center rounded-3xl bg-white py-14 text-sm text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询库存…
              </div>
            ) : inventoryQuery.error ? (
              <div role="alert" className="rounded-3xl bg-red-50 px-5 py-10 text-center text-sm text-red-700">库存查询失败，请检查网络、权限或数据源。</div>
            ) : rows.length === 0 ? (
              <div className="rounded-3xl bg-white px-6 py-12 text-center shadow-sm">
                <PackageSearch className="mx-auto h-10 w-10 text-slate-300" />
                <div className="mt-3 font-medium">没有找到该商品的库存记录</div>
                <div className="mt-2 text-xs leading-5 text-slate-500">请核对条码；账号数据范围之外的库存也不会显示。</div>
              </div>
            ) : (
              <>
                <Card className="overflow-hidden rounded-3xl border-0 bg-gradient-to-br from-cyan-700 to-blue-800 text-white shadow-lg">
                  <CardContent className="p-5">
                    <div className="text-xs text-cyan-100">{firstRow.brand_display || "商品库存"}</div>
                    <div className="mt-1 text-xl font-semibold leading-7">{firstRow.goods_name || firstRow.goods_code}</div>
                    <div className="mt-2 text-xs text-cyan-100">商品编码 {firstRow.goods_code} · 主条码 {firstRow.barcode || "—"}</div>
                    {firstRow.specification && <div className="mt-1 text-xs text-cyan-100">规格 {firstRow.specification}</div>}
                    <div className="mt-5 grid grid-cols-2 gap-3">
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-cyan-100">库存数量</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{formatNumber(summary?.inventory_quantity, 4)}</div>
                      </div>
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-cyan-100">库存明细</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{Number(summary?.total_count || rows.length)}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <section className="space-y-3">
                  <div className="flex items-center justify-between px-1">
                    <h2 className="flex items-center gap-2 text-sm font-semibold"><Boxes className="h-4 w-4" />门店及柜组明细</h2>
                    <span className="text-xs text-slate-400">含零库存</span>
                  </div>
                  {rows.map((row, index) => (
                    <Card key={`${row.store_display}-${row.group_display}-${row.subinventory_display}-${index}`} className="rounded-2xl border-0 shadow-sm">
                      <CardContent className="space-y-3 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-start gap-2 text-sm font-semibold">
                              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-cyan-700" />
                              <span>{row.store_display || "未标记门店"}</span>
                            </div>
                            <div className="mt-1 pl-6 text-xs leading-5 text-slate-500">{[row.floor_display, row.area_display].filter(Boolean).join(" · ") || "—"}</div>
                          </div>
                          <div className={`shrink-0 rounded-xl px-3 py-2 text-right ${Number(row.inventory_quantity) > 0 ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                            <div className="text-[10px]">库存数量</div>
                            <div className="text-lg font-bold tabular-nums">{formatNumber(row.inventory_quantity, 4)}</div>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-x-3 gap-y-2 border-t pt-3 text-xs">
                          <div><span className="text-slate-400">柜组</span><div className="mt-1 font-medium text-slate-700">{row.group_display || "—"}</div></div>
                          <div><span className="text-slate-400">子库存</span><div className="mt-1 font-medium text-slate-700">{row.subinventory_display || "—"}</div></div>
                          <div><span className="text-slate-400">售价</span><div className="mt-1 font-medium text-slate-700">¥{formatNumber(row.selling_price, 2)}</div></div>
                          <div><span className="text-slate-400">经营方式</span><div className="mt-1 font-medium text-slate-700">{row.operation_method || "—"}</div></div>
                        </div>
                        <div className="text-xs leading-5 text-slate-500">供应商：{row.supplier_display || "—"}</div>
                      </CardContent>
                    </Card>
                  ))}
                </section>

                <div className="px-2 text-[11px] leading-5 text-slate-400">{inventoryQuery.data?.source_note}</div>
              </>
            )}
          </TabsContent>

          <TabsContent value="supplier" className="space-y-4">
            <Card className="rounded-3xl border-0 shadow-md">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base"><Factory className="h-5 w-5 text-indigo-700" />供应商库存</CardTitle>
                <CardDescription>输入供应商名称或编码，模糊查询其全部正库存明细。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="text-xs font-medium text-slate-600" htmlFor="mobile-inventory-supplier">供应商名称/编码</label>
                <Input
                  id="mobile-inventory-supplier"
                  autoComplete="off"
                  enterKeyHint="search"
                  className="h-12 rounded-xl text-base"
                  placeholder="请输入供应商名称或编码"
                  value={supplierInput}
                  onChange={(event) => setSupplierInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") submitSupplier();
                  }}
                />
                <Button className="h-11 w-full rounded-xl bg-indigo-700 hover:bg-indigo-800" onClick={submitSupplier} disabled={supplierQuery.isFetching && !supplierQuery.isFetchingNextPage}>
                  {supplierQuery.isFetching && !supplierQuery.isFetchingNextPage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                  查询供应商库存
                </Button>
                {supplierError && (
                  <div role="alert" className="flex gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{supplierError}
                  </div>
                )}
              </CardContent>
            </Card>

            {!submittedSupplier ? (
              <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
                <Factory className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                输入部分供应商名称或编码进行模糊查询
              </div>
            ) : supplierQuery.isLoading ? (
              <div className="flex items-center justify-center rounded-3xl bg-white py-14 text-sm text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询供应商库存…
              </div>
            ) : supplierQuery.error ? (
              <div role="alert" className="rounded-3xl bg-red-50 px-5 py-10 text-center text-sm text-red-700">供应商库存加载失败，请检查网络、权限或数据源。</div>
            ) : supplierRows.length === 0 ? (
              <div className="rounded-3xl bg-white px-6 py-12 text-center shadow-sm">
                <Factory className="mx-auto h-10 w-10 text-slate-300" />
                <div className="mt-3 font-medium">没有找到匹配的供应商库存</div>
                <div className="mt-2 text-xs leading-5 text-slate-500">请更换名称关键词；账号数据范围之外的库存不会显示。</div>
              </div>
            ) : (
              <>
                <Card className="overflow-hidden rounded-3xl border-0 bg-gradient-to-br from-indigo-700 to-violet-800 text-white shadow-lg">
                  <CardContent className="p-5">
                    <div className="text-xs text-indigo-100">供应商模糊查询：{submittedSupplier}</div>
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-indigo-100">匹配供应商</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{supplierGroups.length}</div>
                      </div>
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-indigo-100">库存明细</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{Number(supplierSummary?.total_count || supplierRows.length)}</div>
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-indigo-100">库存数量合计 {formatNumber(supplierSummary?.inventory_quantity, 4)}</div>
                  </CardContent>
                </Card>

                <section className="space-y-4">
                  {supplierGroups.map((group) => (
                    <Card key={group.supplier} className="overflow-hidden rounded-3xl border-0 shadow-sm">
                      <CardHeader className="border-b bg-indigo-50 pb-3">
                        <CardTitle className="text-base leading-6 text-indigo-950">{group.supplier}</CardTitle>
                        <CardDescription>当前已显示 {group.rows.length} 条 · 库存数量 {formatNumber(group.quantity, 4)}</CardDescription>
                      </CardHeader>
                      <CardContent className="divide-y p-0">
                        {group.rows.map((row, index) => (
                          <div key={`${row.goods_code}-${row.store_display}-${row.group_display}-${row.subinventory_display}-${index}`} className="space-y-3 p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="font-semibold leading-5 text-slate-900">{row.goods_name || row.goods_code}</div>
                                <div className="mt-1 break-all text-xs text-slate-500">商品 {row.goods_code} · 条码 {row.barcode || "—"}</div>
                              </div>
                              <div className="shrink-0 rounded-xl bg-emerald-50 px-3 py-2 text-right text-emerald-700">
                                <div className="text-[10px]">库存数量</div>
                                <div className="text-base font-bold tabular-nums">{formatNumber(row.inventory_quantity, 4)}</div>
                              </div>
                            </div>
                            <div className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                              <div className="font-medium text-slate-800">{row.store_display || "未标记门店"}</div>
                              <div>{[row.floor_display, row.area_display, row.group_display].filter(Boolean).join(" · ") || "—"}</div>
                              <div>子库存：{row.subinventory_display || "—"} · 售价：¥{formatNumber(row.selling_price, 2)}</div>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  ))}
                </section>

                <div className="space-y-2 text-center">
                  <div className="text-xs text-slate-500">已显示 {supplierRows.length} / {Number(supplierSummary?.total_count || supplierRows.length)} 条库存明细</div>
                  {supplierQuery.hasNextPage ? (
                    <Button variant="outline" className="h-11 w-full rounded-xl" onClick={() => supplierQuery.fetchNextPage()} disabled={supplierQuery.isFetchingNextPage}>
                      {supplierQuery.isFetchingNextPage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {supplierQuery.isFetchingNextPage ? "加载中…" : "继续加载库存明细"}
                    </Button>
                  ) : (
                    <div className="rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">已显示全部库存明细</div>
                  )}
                </div>

                <div className="px-2 text-[11px] leading-5 text-slate-400">{supplierQuery.data?.pages[0]?.source_note}</div>
              </>
            )}
          </TabsContent>

          <TabsContent value="group" className="space-y-4">
            {fromDepartment && (
              <Button variant="ghost" className="h-9 px-1 text-teal-800" onClick={() => { setActiveTab("department"); window.scrollTo({ top: 0 }); }}>
                <ArrowLeft className="mr-1 h-4 w-4" />返回部门库存列表
              </Button>
            )}
            <Card className="rounded-3xl border-0 shadow-md">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base"><LayoutGrid className="h-5 w-5 text-teal-700" />柜组库存</CardTitle>
                <CardDescription>模糊输入柜组名称或编码，选择柜组后查询全部正库存明细。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="text-xs font-medium text-slate-600" htmlFor="mobile-inventory-group">柜组名称/编码</label>
                <div className="relative">
                  <Input
                    id="mobile-inventory-group"
                    autoComplete="off"
                    enterKeyHint="search"
                    className="h-12 rounded-xl pr-10 text-base"
                    placeholder="输入部分柜组名称或编码"
                    value={groupInput}
                    onChange={(event) => {
                      setGroupInput(event.target.value);
                      setSelectedGroup(null);
                      setGroupError(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") submitGroup();
                    }}
                  />
                  {groupOptionsQuery.isFetching && (
                    <Loader2 className="absolute right-3 top-3.5 h-5 w-5 animate-spin text-slate-400" />
                  )}
                </div>

                {groupInput.trim() && selectedGroup?.label !== groupInput.trim() && (
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    {debouncedGroupInput !== groupInput.trim() || groupOptionsQuery.isLoading ? (
                      <div className="flex items-center justify-center px-4 py-6 text-sm text-slate-500">
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />正在匹配柜组…
                      </div>
                    ) : groupOptionsQuery.error ? (
                      <div className="px-4 py-5 text-center text-sm text-red-600">柜组匹配失败，请检查网络或权限。</div>
                    ) : (groupOptionsQuery.data?.options.length ?? 0) === 0 ? (
                      <div className="px-4 py-5 text-center text-sm text-slate-500">没有找到数据范围内的匹配柜组</div>
                    ) : (
                      <div className="max-h-64 divide-y overflow-y-auto">
                        {groupOptionsQuery.data?.options.map((option) => (
                          <button
                            key={option.value}
                            type="button"
                            className="block w-full px-4 py-3 text-left hover:bg-teal-50 active:bg-teal-100"
                            onClick={() => {
                              setSelectedGroup(option);
                              setGroupInput(option.label);
                              setGroupError(null);
                            }}
                          >
                            <div className="text-sm font-medium text-slate-900">{option.name || option.label}</div>
                            <div className="mt-1 text-xs text-slate-500">柜组编码 {option.code || option.value}</div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {selectedGroup && selectedGroup.label === groupInput.trim() && (
                  <div className="rounded-xl bg-teal-50 px-3 py-2 text-xs text-teal-800">
                    已选择：{selectedGroup.label}
                  </div>
                )}

                <Button className="h-11 w-full rounded-xl bg-teal-700 hover:bg-teal-800" onClick={submitGroup} disabled={groupQuery.isFetching && !groupQuery.isFetchingNextPage}>
                  {groupQuery.isFetching && !groupQuery.isFetchingNextPage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                  查询柜组库存
                </Button>
                {groupError && (
                  <div role="alert" className="flex gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{groupError}
                  </div>
                )}
                <div className="text-[11px] leading-5 text-slate-400">柜组候选和库存结果均受当前账号数据范围控制。</div>
              </CardContent>
            </Card>

            {!submittedGroup ? (
              <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
                <LayoutGrid className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                输入关键词，从数据范围内的匹配柜组中选择后查询
              </div>
            ) : groupQuery.isLoading ? (
              <div className="flex items-center justify-center rounded-3xl bg-white py-14 text-sm text-slate-500">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />正在查询柜组库存…
              </div>
            ) : groupQuery.error ? (
              <div role="alert" className="rounded-3xl bg-red-50 px-5 py-10 text-center text-sm text-red-700">柜组库存加载失败，请检查网络、权限或数据源。</div>
            ) : groupRows.length === 0 ? (
              <div className="rounded-3xl bg-white px-6 py-12 text-center shadow-sm">
                <LayoutGrid className="mx-auto h-10 w-10 text-slate-300" />
                <div className="mt-3 font-medium">该柜组没有正库存明细</div>
                <div className="mt-2 text-xs leading-5 text-slate-500">账号数据范围之外的库存不会显示。</div>
              </div>
            ) : (
              <>
                <Card className="overflow-hidden rounded-3xl border-0 bg-gradient-to-br from-teal-700 to-emerald-800 text-white shadow-lg">
                  <CardContent className="p-5">
                    <div className="text-xs text-teal-100">已选柜组</div>
                    <div className="mt-1 text-lg font-semibold leading-7">{submittedGroup.label}</div>
                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-teal-100">库存数量</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{formatNumber(groupSummary?.inventory_quantity, 4)}</div>
                      </div>
                      <div className="rounded-2xl bg-white/10 p-3">
                        <div className="text-xs text-teal-100">库存明细</div>
                        <div className="mt-1 text-2xl font-bold tabular-nums">{Number(groupSummary?.total_count || groupRows.length)}</div>
                      </div>
                      <div className="col-span-2 flex items-center justify-between rounded-2xl bg-white/10 px-3 py-2.5">
                        <div>
                          <div className="text-xs text-teal-100">总库存金额</div>
                          <div className="mt-0.5 text-[10px] text-teal-100/80">按零售价合计</div>
                        </div>
                        <div className="text-xl font-bold tabular-nums">¥{formatNumber(groupSummary?.retail_amount, 2)}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <section className="space-y-3">
                  {groupSupplierGroups.map((supplierGroup) => (
                    <Card key={supplierGroup.supplier} className="overflow-hidden rounded-2xl border-0 shadow-sm">
                      <CardHeader className="space-y-1 border-b bg-teal-50 px-4 py-3">
                        <CardTitle className="text-sm leading-5 text-teal-950">{supplierGroup.supplier}</CardTitle>
                        <CardDescription className="text-[11px] leading-4">
                          {supplierGroup.rows.length} 条明细 · 库存数量 {formatNumber(supplierGroup.quantity, 4)}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="divide-y p-0">
                        {supplierGroup.rows.map((row, index) => (
                          <div key={`${row.goods_code}-${row.subinventory_display}-${index}`} className="px-3 py-2.5">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="text-sm font-semibold leading-5 text-slate-900">{row.goods_name || row.goods_code}</div>
                                <div className="mt-0.5 break-all text-[11px] leading-4 text-slate-500">商品 {row.goods_code} · 条码 {row.barcode || "—"}</div>
                              </div>
                              <div className="shrink-0 rounded-lg bg-emerald-50 px-2 py-1 text-right text-emerald-700">
                                <div className="text-[9px] leading-3">库存数量</div>
                                <div className="text-sm font-bold leading-5 tabular-nums">{formatNumber(row.inventory_quantity, 4)}</div>
                              </div>
                            </div>
                            <div className="mt-1.5 flex flex-wrap gap-x-2 text-[11px] leading-4 text-slate-500">
                              <span>子库存：{row.subinventory_display || "—"}</span>
                              <span>售价：{formatSellingCalculation(row)}</span>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  ))}
                </section>

                <div className="space-y-2 text-center">
                  <div className="text-xs text-slate-500">已显示 {groupRows.length} / {Number(groupSummary?.total_count || groupRows.length)} 条库存明细</div>
                  {groupQuery.hasNextPage ? (
                    <Button variant="outline" className="h-11 w-full rounded-xl" onClick={() => groupQuery.fetchNextPage()} disabled={groupQuery.isFetchingNextPage}>
                      {groupQuery.isFetchingNextPage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      {groupQuery.isFetchingNextPage ? "加载中…" : "继续加载库存明细"}
                    </Button>
                  ) : (
                    <div className="rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">已显示全部库存明细</div>
                  )}
                </div>

                <div className="px-2 text-[11px] leading-5 text-slate-400">{groupQuery.data?.pages[0]?.source_note}</div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {cameraOpen && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black text-white">
          <div className="flex items-center justify-between px-4 pb-3 pt-[max(1rem,env(safe-area-inset-top))]">
            <div>
              <div className="font-semibold">扫描商品条形码</div>
              <div className="mt-1 text-xs text-white/60">将条码完整放入取景框内</div>
            </div>
            <Button variant="ghost" size="icon" className="text-white hover:bg-white/10 hover:text-white" onClick={() => setCameraOpen(false)}>
              <X className="h-6 w-6" />
            </Button>
          </div>
          <div className="relative flex flex-1 items-center justify-center overflow-hidden">
            <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
            <div className="pointer-events-none absolute h-40 w-[86%] max-w-md rounded-2xl border-2 border-cyan-300 shadow-[0_0_0_999px_rgba(0,0,0,0.42)]">
              <div className="absolute left-4 right-4 top-1/2 h-0.5 bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.9)]" />
            </div>
          </div>
          <div className="px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-4 text-center text-sm text-white/70">识别成功后会自动关闭并查询库存</div>
        </div>
      )}
    </main>
  );
}
