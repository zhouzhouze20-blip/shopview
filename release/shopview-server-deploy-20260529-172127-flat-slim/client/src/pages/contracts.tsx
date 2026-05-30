import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent,
  type ReactNode,
  type WheelEvent,
} from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBaseMapsList, useFloorDictList } from "@/hooks/useBaseMaps";
import { BusinessUnitStatus, useBusinessUnits } from "@/hooks/useBusinessUnits";
import { useContractDetail, useContractsList, useUnitContracts, type ContractListItem } from "@/hooks/useContracts";
import { useGeoElements } from "@/hooks/useGeoElements";
import { useAlignTransform, useUnitMapVersions } from "@/hooks/useUnitMapVersions";
import { useStore } from "@/contexts/StoreContext";
import { resolveApiAssetUrl } from "@/lib/api";
import { getPathVisualCenter } from "@/lib/svg-path-center";
import { formatOperationMethod } from "@/lib/operation-method";
import { deriveSvgViewBox, extractSvgMetadataFromText } from "@/lib/svg-metadata";
import { cn } from "@/lib/utils";
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  HardHat,
  Map as MapIcon,
  MapPin,
  Maximize2,
  Minus,
  Plus,
  RefreshCw,
  RotateCcw,
} from "lucide-react";

function normalizeUnitCode(value?: string | null) {
  return (value || "").trim().toUpperCase().replace(/\s+/g, "");
}

function getFloorStoreRef(floor: { store_id?: string | null; building_code?: string | null }) {
  return floor.store_id?.trim() || floor.building_code?.trim() || "";
}

function fmtDate(value?: string | null) {
  if (!value) return "-";
  return value.slice(0, 10);
}

function fmtMoney(value?: number | null) {
  if (value == null) return "-";
  return Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function fmtPercent(value?: number | null) {
  if (value == null) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  const percentValue = Math.abs(numeric) <= 1 ? numeric * 100 : numeric;
  return `${percentValue.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}%`;
}

function fmtYesNo(value?: string | null) {
  const normalized = value?.trim().toUpperCase();
  if (!normalized) return "-";
  if (["Y", "1", "T"].includes(normalized)) return "是";
  if (["N", "0", "F"].includes(normalized)) return "否";
  return value;
}

function fmtSettlementMethod(value?: string | null) {
  const normalized = value?.trim().toUpperCase();
  if (!normalized) return "-";
  if (normalized === "0") return "每次";
  if (normalized === "1") return "一次";
  return value;
}

function fmtValue(value?: string | number | null) {
  if (value == null || value === "") return "-";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return value.slice(0, 10);
  if (typeof value === "number") return fmtMoney(value);
  return value;
}

function isFutureDate(value?: string | null) {
  if (!value) return false;
  return value.slice(0, 10) > new Date().toISOString().slice(0, 10);
}

function renderSupplierInfo(code?: string | null, name?: string | null) {
  const supplierCode = code?.trim();
  const supplierName = name?.trim();
  if (!supplierCode && !supplierName) return "-";

  return (
    <div className="space-y-1">
      <div>{supplierCode || "-"}</div>
      {supplierName ? <div className="text-xs text-muted-foreground">{supplierName}</div> : null}
    </div>
  );
}

function renderGroupInfo(code?: string | null, name?: string | null) {
  const groupCode = code?.trim();
  const groupName = name?.trim();
  if (!groupCode && !groupName) return "-";

  return (
    <div className="space-y-1">
      <div>{groupCode || "-"}</div>
      {groupName ? <div className="text-xs text-muted-foreground">{groupName}</div> : null}
    </div>
  );
}

function renderContractType(code?: string | null, name?: string | null) {
  const typeCode = code?.trim();
  const typeName = name?.trim();
  if (!typeCode && !typeName) return "-";
  return typeName ? `${typeName}${typeCode ? ` (${typeCode})` : ""}` : typeCode;
}

function getPrimaryGroupCode(item: ContractListItem) {
  return (
    String(item.group_codes || item.cmchar9 || "")
      .split(",")
      .map((value) => value.trim())
      .find(Boolean) || ""
  );
}

const STATUS_META: Record<
  BusinessUnitStatus,
  {
    label: string;
    fill: string;
    stroke: string;
    selectedFill: string;
    selectedStroke: string;
    badgeClassName: string;
  }
> = {
  ACTIVE: {
    label: "经营中",
    fill: "rgba(37,99,235,0.18)",
    stroke: "rgba(37,99,235,0.92)",
    selectedFill: "rgba(37,99,235,0.34)",
    selectedStroke: "rgba(30,64,175,1)",
    badgeClassName: "border-blue-200 bg-blue-50 text-blue-700",
  },
  FITOUT: {
    label: "装修中",
    fill: "rgba(245,158,11,0.22)",
    stroke: "rgba(217,119,6,0.95)",
    selectedFill: "rgba(245,158,11,0.38)",
    selectedStroke: "rgba(146,64,14,1)",
    badgeClassName: "border-amber-200 bg-amber-50 text-amber-700",
  },
  VACANT: {
    label: "空置",
    fill: "rgba(244,63,94,0.16)",
    stroke: "rgba(225,29,72,0.9)",
    selectedFill: "rgba(244,63,94,0.32)",
    selectedStroke: "rgba(159,18,57,1)",
    badgeClassName: "border-rose-200 bg-rose-50 text-rose-700",
  },
  INACTIVE: {
    label: "失效",
    fill: "rgba(100,116,139,0.16)",
    stroke: "rgba(71,85,105,0.9)",
    selectedFill: "rgba(100,116,139,0.3)",
    selectedStroke: "rgba(51,65,85,1)",
    badgeClassName: "border-slate-200 bg-slate-100 text-slate-700",
  },
};

const STATUS_LEGEND_ORDER: BusinessUnitStatus[] = ["ACTIVE", "FITOUT", "VACANT", "INACTIVE"];
const MAP_MIN_ZOOM = 1;
const MAP_MAX_ZOOM = 8;
const CONTRACT_STATUS_OPTIONS = [
  { value: "ALL", label: "全部状态" },
  { value: "Y", label: "已生效" },
  { value: "Q", label: "过期" },
  { value: "B", label: "未生效" },
  { value: "A", label: "已审批" },
  { value: "S", label: "停用" },
  { value: "N", label: "终止" },
];

function getStatusMeta(status?: string | null) {
  if (!status) return STATUS_META.INACTIVE;
  return STATUS_META[status as BusinessUnitStatus] ?? STATUS_META.INACTIVE;
}

function clampMapZoom(value: number) {
  return Math.min(MAP_MAX_ZOOM, Math.max(MAP_MIN_ZOOM, value));
}

function getPointerDistance(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) return 0;
  return Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y);
}

function getPointerMidpoint(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) return points[0] ?? { x: 0, y: 0 };
  return {
    x: (points[0].x + points[1].x) / 2,
    y: (points[0].y + points[1].y) / 2,
  };
}

type DetailColumn<Row> = {
  header: string;
  render: (row: Row) => ReactNode;
  className?: string;
};

function DetailTable<Row>({
  rows,
  columns,
  emptyText,
}: {
  rows: Row[];
  columns: DetailColumn<Row>[];
  emptyText: string;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.header} className={column.className}>
              {column.header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.length ? (
          rows.map((row, index) => (
            <TableRow key={index}>
              {columns.map((column) => (
                <TableCell key={column.header} className={column.className}>
                  {column.render(row)}
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell colSpan={columns.length} className="py-8 text-center text-muted-foreground">
              {emptyText}
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}

export type ContractsPageProps = {
  /** 从其他模块跳入合同台账时传入，挂载后自动打开对应合同明细弹窗 */
  openContractNoOnMount?: string | null;
  /** 明细弹窗已根据 openContractNoOnMount 打开后回调，用于清空父级状态避免重复触发 */
  onOpenContractNoConsumed?: () => void;
};

export default function ContractsPage({
  openContractNoOnMount,
  onOpenContractNoConsumed,
}: ContractsPageProps = {}) {
  const { selectedStoreId, stores, isLoading: storesLoading } = useStore();
  const floorsQuery = useFloorDictList();
  const floorOptions = useMemo(() => floorsQuery.data ?? [], [floorsQuery.data]);

  const [storeFilter, setStoreFilter] = useState("");
  const [floorId, setFloorId] = useState<number | undefined>(undefined);
  const [baseMapId, setBaseMapId] = useState<number | undefined>(undefined);
  const [versionId, setVersionId] = useState<number | undefined>(undefined);
  const [selectedGeoId, setSelectedGeoId] = useState<number | undefined>(undefined);
  const [selectedUnitId, setSelectedUnitId] = useState<number | undefined>(undefined);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedContractNo, setSelectedContractNo] = useState<string | undefined>(undefined);
  const [contractDetailOpen, setContractDetailOpen] = useState(false);
  const [reopenUnitDialogOnContractClose, setReopenUnitDialogOnContractClose] = useState(false);
  const [counterKeyword, setCounterKeyword] = useState("");
  const [listKeyword, setListKeyword] = useState("");
  const [listStatus, setListStatus] = useState("ALL");
  const [listGroupCode, setListGroupCode] = useState("");
  const [listPage, setListPage] = useState(0);
  const [listPageSize, setListPageSize] = useState(100);
  const [pageView, setPageView] = useState("list");
  const [resolvedSvgViewBox, setResolvedSvgViewBox] = useState<string | null>(null);
  const [mapFullscreenOpen, setMapFullscreenOpen] = useState(false);
  const [mapLandscapeOpen, setMapLandscapeOpen] = useState(false);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapPan, setMapPan] = useState({ x: 0, y: 0 });
  const mapPointersRef = useRef(new Map<number, { x: number; y: number }>());
  const mapGestureRef = useRef<{
    startDistance: number;
    startMidpoint: { x: number; y: number };
    startZoom: number;
    startPan: { x: number; y: number };
    lastPoint: { x: number; y: number } | null;
    moved: boolean;
  }>({
    startDistance: 0,
    startMidpoint: { x: 0, y: 0 },
    startZoom: 1,
    startPan: { x: 0, y: 0 },
    lastPoint: null,
    moved: false,
  });

  const unitsQuery = useBusinessUnits({ floorId });
  const baseMapsQuery = useBaseMapsList(floorId);
  const versionsQuery = useUnitMapVersions(floorId, baseMapId);
  const geoQuery = useGeoElements(versionId);
  const alignQuery = useAlignTransform(versionId);
  const contractsQuery = useUnitContracts(selectedUnitId);
  const contractsListQuery = useContractsList({
    keyword: listKeyword,
    status: listStatus,
    groupCode: listGroupCode,
    skip: listPage * listPageSize,
    limit: listPageSize,
  });
  const contractDetailQuery = useContractDetail(selectedContractNo);

  const unitRows = useMemo(() => unitsQuery.data ?? [], [unitsQuery.data]);
  const baseMapOptions = useMemo(() => baseMapsQuery.data ?? [], [baseMapsQuery.data]);
  const versionOptions = useMemo(() => versionsQuery.data ?? [], [versionsQuery.data]);
  const geoRows = useMemo(() => geoQuery.data ?? [], [geoQuery.data]);
  const storeOptions = useMemo(() => {
    const options = stores.map((store) => ({
      value: String(store.storeId),
      label: store.storeName || store.storeCode || String(store.storeId),
      code: store.storeCode ? String(store.storeCode) : "",
    }));
    const knownRefs = new Set(options.flatMap((store) => [store.value, store.code]).filter(Boolean));
    floorOptions.forEach((floor) => {
      const storeRef = getFloorStoreRef(floor);
      if (!storeRef || knownRefs.has(storeRef)) return;
      knownRefs.add(storeRef);
      options.push({ value: storeRef, label: `门店 ${storeRef}`, code: storeRef });
    });
    return options;
  }, [floorOptions, stores]);
  const selectedStoreOption = useMemo(
    () => storeOptions.find((store) => store.value === storeFilter),
    [storeFilter, storeOptions],
  );
  const visibleFloorOptions = useMemo(() => {
    if (!storeFilter) return [];
    return floorOptions.filter((floor) => {
      const storeRef = getFloorStoreRef(floor);
      if (!storeRef) return false;
      return storeRef === storeFilter || storeRef === selectedStoreOption?.code;
    });
  }, [floorOptions, selectedStoreOption?.code, storeFilter]);

  const selectedBaseMap = useMemo(
    () => baseMapOptions.find((item) => item.id === baseMapId),
    [baseMapOptions, baseMapId],
  );
  const selectedBaseMapUrl = useMemo(
    () => resolveApiAssetUrl(selectedBaseMap?.file_url),
    [selectedBaseMap?.file_url],
  );
  const unitCodeMap = useMemo(() => {
    const m = new Map<number, string>();
    unitRows.forEach((row) => m.set(row.id, row.unit_code));
    return m;
  }, [unitRows]);
  const unitStatusMap = useMemo(() => {
    const m = new Map<number, BusinessUnitStatus>();
    unitRows.forEach((row) => m.set(row.id, row.status));
    return m;
  }, [unitRows]);
  const normalizedUnitCodeMap = useMemo(() => {
    const m = new Map<number, string>();
    unitRows.forEach((row) => m.set(row.id, normalizeUnitCode(row.unit_code)));
    return m;
  }, [unitRows]);
  const selectedUnitCode = selectedUnitId ? unitCodeMap.get(selectedUnitId) : undefined;
  const selectedUnitStatus = selectedUnitId ? unitStatusMap.get(selectedUnitId) : undefined;
  const normalizedCounterKeyword = useMemo(() => normalizeUnitCode(counterKeyword), [counterKeyword]);

  useEffect(() => {
    const immediate = deriveSvgViewBox({
      viewBox: selectedBaseMap?.svg_viewbox ?? null,
      width: selectedBaseMap?.svg_width ?? null,
      height: selectedBaseMap?.svg_height ?? null,
    });
    setResolvedSvgViewBox(immediate);

    if (immediate || !selectedBaseMapUrl) return;

    let cancelled = false;
    fetch(selectedBaseMapUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`加载底图失败: ${response.status}`);
        }
        return response.text();
      })
      .then((text) => {
        const metadata = extractSvgMetadataFromText(text);
        const derived = deriveSvgViewBox(metadata);
        if (!cancelled) {
          setResolvedSvgViewBox(derived);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setResolvedSvgViewBox(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedBaseMap?.svg_height, selectedBaseMap?.svg_viewbox, selectedBaseMap?.svg_width, selectedBaseMapUrl]);

  const vb = useMemo(() => {
    const raw = (resolvedSvgViewBox || "").trim();
    if (!raw) return null;
    const parts = raw.split(/\s+/).map((x) => Number(x));
    if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
    return { x: parts[0], y: parts[1], w: parts[2], h: parts[3] };
  }, [resolvedSvgViewBox]);

  const align = useMemo(() => {
    const a = alignQuery.data;
    return {
      dx: a?.dx ?? 0,
      dy: a?.dy ?? 0,
      sx: a?.sx ?? 1,
      sy: a?.sy ?? 1,
      rotate: a?.rotate ?? 0,
    };
  }, [alignQuery.data]);

  const alignTransformText = useMemo(() => {
    if (!vb) return "";
    const cx = vb.x + vb.w / 2;
    const cy = vb.y + vb.h / 2;
    return `translate(${align.dx} ${align.dy}) rotate(${align.rotate} ${cx} ${cy}) scale(${align.sx} ${align.sy})`;
  }, [align, vb]);

  const labelPoints = useMemo(() => {
    return geoRows.map((g) => {
      const cx =
        g.centroid_x ??
        (g.bbox_minx != null && g.bbox_maxx != null ? (g.bbox_minx + g.bbox_maxx) / 2 : null);
      const cy =
        g.centroid_y ??
        (g.bbox_miny != null && g.bbox_maxy != null ? (g.bbox_miny + g.bbox_maxy) / 2 : null);
      if (cx == null || cy == null) {
        const fallback = getPathVisualCenter(g.path_data);
        if (!fallback) return { id: g.id, x: null as number | null, y: null as number | null };
        return { id: g.id, x: fallback.x, y: fallback.y };
      }
      return { id: g.id, x: cx, y: cy };
    });
  }, [geoRows]);

  const highlightedGeoIds = useMemo(() => {
    if (!normalizedCounterKeyword) return new Set<number>();
    return new Set(
      geoRows
        .filter((g) => (normalizedUnitCodeMap.get(g.unit_id) || "").includes(normalizedCounterKeyword))
        .map((g) => g.id),
    );
  }, [geoRows, normalizedCounterKeyword, normalizedUnitCodeMap]);

  const exactMatchedGeo = useMemo(() => {
    if (!normalizedCounterKeyword) return undefined;
    return geoRows.find((g) => (normalizedUnitCodeMap.get(g.unit_id) || "") === normalizedCounterKeyword);
  }, [geoRows, normalizedCounterKeyword, normalizedUnitCodeMap]);

  const highlightedCount = highlightedGeoIds.size;

  useEffect(() => {
    if (storeFilter || !storeOptions.length) return;
    const globalStoreValue = selectedStoreId ? String(selectedStoreId) : "";
    const globalStore = storeOptions.find((store) => store.value === globalStoreValue);
    const firstStoreWithFloors = storeOptions.find((store) =>
      floorOptions.some((floor) => {
        const storeRef = getFloorStoreRef(floor);
        return storeRef === store.value || storeRef === store.code;
      }),
    );
    setStoreFilter(globalStore?.value ?? firstStoreWithFloors?.value ?? storeOptions[0].value);
  }, [floorOptions, selectedStoreId, storeFilter, storeOptions]);

  useEffect(() => {
    if (!storeFilter) {
      setFloorId(undefined);
      return;
    }
    if (!visibleFloorOptions.length) {
      setFloorId(undefined);
      return;
    }
    if (floorId && visibleFloorOptions.some((floor) => floor.id === floorId)) return;
    setFloorId(visibleFloorOptions[0].id);
  }, [floorId, storeFilter, visibleFloorOptions]);

  useEffect(() => {
    setBaseMapId(undefined);
    setVersionId(undefined);
    setSelectedGeoId(undefined);
    setSelectedUnitId(undefined);
  }, [floorId]);

  useEffect(() => {
    if (!exactMatchedGeo) return;
    setSelectedGeoId(exactMatchedGeo.id);
    setSelectedUnitId(exactMatchedGeo.unit_id);
  }, [exactMatchedGeo]);

  useEffect(() => {
    if (!detailOpen || !selectedUnitId) return;
    contractsQuery.refetch();
  }, [detailOpen, selectedUnitId, contractsQuery.refetch]);

  useEffect(() => {
    setListPage(0);
  }, [listKeyword, listStatus, listGroupCode, listPageSize]);

  useEffect(() => {
    if (!baseMapOptions.length) {
      setBaseMapId(undefined);
      return;
    }
    if (baseMapId && baseMapOptions.some((item) => item.id === baseMapId)) return;
    const active = baseMapOptions.find((item) => item.is_active);
    setBaseMapId(active?.id ?? baseMapOptions[0].id);
  }, [baseMapId, baseMapOptions]);

  useEffect(() => {
    if (!versionOptions.length) {
      setVersionId(undefined);
      return;
    }
    if (versionId && versionOptions.some((item) => item.id === versionId)) return;
    const active = versionOptions.find((item) => item.is_active);
    setVersionId(active?.id ?? versionOptions[0].id);
  }, [versionId, versionOptions]);

  const selectGeo = (geoId: number, unitId: number) => {
    setSelectedGeoId(geoId);
    setSelectedUnitId(unitId);
    setDetailOpen(true);
    if (detailOpen && selectedUnitId === unitId) {
      contractsQuery.refetch();
    }
  };

  const detail = contractsQuery.data;
  const activeContract = detail?.active_contract;
  const contractRows = useMemo(() => {
    const rows = detail?.contracts ?? [];
    const seen = new Set<string>();
    return rows.filter((item) => {
      const key = normalizeUnitCode(item.cmcontno || item.cmfcontno || "");
      if (!key) return true;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [detail?.contracts]);
  const activeContractCount = useMemo(
    () => contractRows.filter((item) => item.is_current_effective).length,
    [contractRows],
  );
  const contractListRows = contractsListQuery.data?.items ?? [];
  const canGoPrevPage = listPage > 0;
  const canGoNextPage = contractListRows.length >= listPageSize;
  const detailUnitStatus = detail?.unit.status ?? selectedUnitStatus;
  const contractDetail = contractDetailQuery.data;
  const contractMain = contractDetail?.contmain;

  const startDecorationFromContract = (contractNo?: string | null) => {
    const normalized = contractNo?.trim();
    if (!normalized) return;
    window.location.href = `${window.location.pathname}?view=decorations&contract_no=${encodeURIComponent(normalized)}`;
  };

  const locateContractOnMap = (item: ContractListItem) => {
    const groupCode = getPrimaryGroupCode(item);
    if (!groupCode) return;
    const normalizedGroupCode = normalizeUnitCode(groupCode);
    const matchedGeo =
      geoRows.find((g) => (normalizedUnitCodeMap.get(g.unit_id) || "") === normalizedGroupCode) ??
      geoRows.find((g) => (normalizedUnitCodeMap.get(g.unit_id) || "").includes(normalizedGroupCode));

    setCounterKeyword(groupCode);
    setPageView("map");

    if (matchedGeo) {
      setSelectedGeoId(matchedGeo.id);
      setSelectedUnitId(matchedGeo.unit_id);
      setDetailOpen(true);
    }
  };

  const openContractDetail = (contractNo?: string | null) => {
    const normalized = (contractNo || "").trim();
    if (!normalized) return;
    setSelectedContractNo(normalized);
    setReopenUnitDialogOnContractClose(detailOpen);
    if (detailOpen) {
      setDetailOpen(false);
    }
    setContractDetailOpen(true);
  };

  useEffect(() => {
    const normalized = (openContractNoOnMount || "").trim();
    if (!normalized) return;
    setSelectedContractNo(normalized);
    setReopenUnitDialogOnContractClose(false);
    setDetailOpen(false);
    setContractDetailOpen(true);
    onOpenContractNoConsumed?.();
  }, [openContractNoOnMount, onOpenContractNoConsumed]);

  const resetMapView = () => {
    setMapZoom(1);
    setMapPan({ x: 0, y: 0 });
    mapPointersRef.current.clear();
    mapGestureRef.current = {
      startDistance: 0,
      startMidpoint: { x: 0, y: 0 },
      startZoom: 1,
      startPan: { x: 0, y: 0 },
      lastPoint: null,
      moved: false,
    };
  };

  const updateMapZoom = (nextZoom: number) => {
    setMapZoom(clampMapZoom(nextZoom));
  };

  const handleMapPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = { x: event.clientX, y: event.clientY };
    mapPointersRef.current.set(event.pointerId, point);
    const points = Array.from(mapPointersRef.current.values());

    mapGestureRef.current = {
      startDistance: getPointerDistance(points),
      startMidpoint: getPointerMidpoint(points),
      startZoom: mapZoom,
      startPan: mapPan,
      lastPoint: points.length === 1 ? point : null,
      moved: false,
    };
  };

  const handleMapPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!mapPointersRef.current.has(event.pointerId)) return;
    const point = { x: event.clientX, y: event.clientY };
    mapPointersRef.current.set(event.pointerId, point);
    const points = Array.from(mapPointersRef.current.values());
    const gesture = mapGestureRef.current;

    if (points.length >= 2) {
      const distance = getPointerDistance(points);
      const midpoint = getPointerMidpoint(points);
      const scale = gesture.startDistance > 0 ? distance / gesture.startDistance : 1;
      const nextZoom = clampMapZoom(gesture.startZoom * scale);
      gesture.moved = gesture.moved || Math.abs(distance - gesture.startDistance) > 4;
      setMapZoom(nextZoom);
      setMapPan({
        x: gesture.startPan.x + midpoint.x - gesture.startMidpoint.x,
        y: gesture.startPan.y + midpoint.y - gesture.startMidpoint.y,
      });
      return;
    }

    if (points.length === 1 && gesture.lastPoint) {
      const dx = point.x - gesture.lastPoint.x;
      const dy = point.y - gesture.lastPoint.y;
      if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
        gesture.moved = true;
      }
      gesture.lastPoint = point;
      setMapPan((current) => ({ x: current.x + dx, y: current.y + dy }));
    }
  };

  const handleMapPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    mapPointersRef.current.delete(event.pointerId);
    const points = Array.from(mapPointersRef.current.values());
    mapGestureRef.current.lastPoint = points.length === 1 ? points[0] : null;
    mapGestureRef.current.startPan = mapPan;
    mapGestureRef.current.startZoom = mapZoom;
  };

  const handleMapClickCapture = (event: MouseEvent<HTMLDivElement>) => {
    if (!mapGestureRef.current.moved) return;
    event.preventDefault();
    event.stopPropagation();
    mapGestureRef.current.moved = false;
  };

  const handleMapWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const direction = event.deltaY > 0 ? -0.15 : 0.15;
    updateMapZoom(mapZoom + direction);
  };

  const mapStatusText = normalizedCounterKeyword
    ? highlightedCount
      ? `搜索结果：${highlightedCount} 个`
      : `未找到柜位：${counterKeyword.trim()}`
    : selectedUnitCode
      ? `当前柜位：${selectedUnitCode}`
      : "点击柜位查看合同";

  const renderMapCanvas = (isFullscreen = false, mode: "default" | "landscape" = "default") => {
    if (!selectedBaseMapUrl) {
      return <div className="text-sm text-muted-foreground">当前楼层没有可用底图</div>;
    }
    if (!vb) {
      return <div className="text-sm text-muted-foreground">当前底图缺少有效 viewBox，无法叠加柜位图</div>;
    }
    const isLandscape = mode === "landscape";

    return (
      <div className={cn("overflow-hidden bg-white", isLandscape ? "flex h-full flex-col rounded-none border-0" : "rounded-lg border")}>
        <div className="flex flex-col gap-2 border-b px-3 py-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span>柜位数量：{geoRows.length}</span>
            <span>{mapStatusText}</span>
            <span>缩放：{Math.round(mapZoom * 100)}%</span>
          </div>
          <div className="flex items-center gap-1">
            <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={() => updateMapZoom(mapZoom - 0.5)}>
              <Minus className="h-4 w-4" />
            </Button>
            <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={() => updateMapZoom(mapZoom + 0.5)}>
              <Plus className="h-4 w-4" />
            </Button>
            <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={resetMapView}>
              <RotateCcw className="h-4 w-4" />
            </Button>
            {!isFullscreen ? (
              <Button type="button" variant="outline" size="icon" className="h-8 w-8" onClick={() => setMapFullscreenOpen(true)}>
                <Maximize2 className="h-4 w-4" />
              </Button>
            ) : null}
            {!isLandscape ? (
              <Button type="button" variant="outline" size="sm" className="h-8 px-2" onClick={() => setMapLandscapeOpen(true)}>
                横向查看
              </Button>
            ) : null}
          </div>
        </div>
        <div
          className={cn(
            "relative w-full touch-none select-none overflow-hidden bg-slate-50",
            isLandscape
              ? "min-h-0 flex-1"
              : isFullscreen
                ? "h-[72vh] sm:h-[78vh]"
                : "aspect-[16/10] min-h-[280px] max-sm:aspect-[16/9] max-sm:min-h-[360px]",
          )}
          onPointerDown={handleMapPointerDown}
          onPointerMove={handleMapPointerMove}
          onPointerUp={handleMapPointerUp}
          onPointerCancel={handleMapPointerUp}
          onClickCapture={handleMapClickCapture}
          onWheel={handleMapWheel}
        >
          <svg
            className="absolute inset-0 h-full w-full cursor-grab active:cursor-grabbing"
            viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
            preserveAspectRatio="xMidYMid meet"
            style={{
              transform: `translate(${mapPan.x}px, ${mapPan.y}px) scale(${mapZoom})`,
              transformOrigin: "center",
            }}
          >
            <image href={selectedBaseMapUrl} x={vb.x} y={vb.y} width={vb.w} height={vb.h} />
            <g transform={alignTransformText}>
              {geoRows.map((g) => {
                const isSelected = g.id === selectedGeoId;
                const isHighlighted = highlightedGeoIds.has(g.id);
                const statusMeta = getStatusMeta(unitStatusMap.get(g.unit_id));
                const fill = isSelected ? statusMeta.selectedFill : isHighlighted ? "rgba(250,204,21,0.4)" : statusMeta.fill;
                const stroke = isSelected
                  ? statusMeta.selectedStroke
                  : isHighlighted
                    ? "rgba(180,83,9,1)"
                    : statusMeta.stroke;
                return (
                  <path
                    key={g.id}
                    d={g.path_data}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={isSelected || isHighlighted ? 3 : 2}
                    vectorEffect="non-scaling-stroke"
                    className="cursor-pointer"
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      mapGestureRef.current.moved = false;
                    }}
                    onClick={(event) => {
                      event.stopPropagation();
                      selectGeo(g.id, g.unit_id);
                    }}
                  />
                );
              })}
              {labelPoints.map((point) => {
                if (point.x == null || point.y == null) return null;
                const geo = geoRows.find((item) => item.id === point.id);
                if (!geo) return null;
                const isSelected = geo.id === selectedGeoId;
                const isHighlighted = highlightedGeoIds.has(geo.id);
                const textValue = unitCodeMap.get(geo.unit_id) || `unit-${geo.unit_id}`;
                return (
                  <text
                    key={`label-${geo.id}`}
                    x={point.x}
                    y={point.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={isSelected || isHighlighted ? 32 : 28}
                    fontWeight={isSelected || isHighlighted ? 800 : 700}
                    fill={isHighlighted ? "#92400e" : "#0f172a"}
                    stroke="#ffffff"
                    strokeWidth={isSelected || isHighlighted ? 8 : 6}
                    paintOrder="stroke"
                    pointerEvents="none"
                  >
                    {textValue}
                  </text>
                );
              })}
            </g>
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="contracts-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">合同台账</h1>
          <p className="text-sm text-muted-foreground mt-1">选择门店和楼层，或输入柜位号，直接在图纸上定位并查看 ERP 合同</p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            contractsListQuery.refetch();
            if (selectedUnitId) contractsQuery.refetch();
          }}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          刷新合同
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>门店</Label>
            <Select
              value={storeFilter}
              onValueChange={(value) => {
                setStoreFilter(value);
                setCounterKeyword("");
              }}
              disabled={storesLoading || !storeOptions.length}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择门店" />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                {storeOptions.map((store) => (
                  <SelectItem key={store.value} value={store.value}>
                    {store.code ? `${store.code} ${store.label}` : store.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>楼层</Label>
            <Select
              value={floorId ? String(floorId) : ""}
              onValueChange={(v) => setFloorId(Number(v))}
              disabled={floorsQuery.isLoading || !visibleFloorOptions.length}
            >
              <SelectTrigger>
                <SelectValue placeholder={storeFilter ? "选择楼层" : "请先选择门店"} />
              </SelectTrigger>
              <SelectContent className="z-50 bg-white border shadow-xl">
                {visibleFloorOptions.map((f) => (
                  <SelectItem key={f.id} value={String(f.id)}>
                    {f.building_code}-{f.floor_code} {f.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {storeFilter && !visibleFloorOptions.length ? (
              <div className="text-xs text-muted-foreground">当前门店没有可用楼层</div>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label>柜位号</Label>
            <Input
              value={counterKeyword}
              onChange={(e) => setCounterKeyword(e.target.value)}
              placeholder="输入柜位号，如 A118 / B6-4A"
            />
            <div className="text-xs text-muted-foreground">
              {normalizedCounterKeyword
                ? highlightedCount
                  ? `已高亮 ${highlightedCount} 个匹配柜位`
                  : "当前楼层未找到匹配柜位"
                : "输入柜位号后，下方图纸会自动高亮对应柜位"}
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={pageView} onValueChange={setPageView} className="space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <TabsList className="grid w-full grid-cols-2 md:w-[360px]">
            <TabsTrigger value="list" className="gap-2">
              <FileText className="h-4 w-4" />
              合同列表
            </TabsTrigger>
            <TabsTrigger value="map" className="gap-2">
              <MapIcon className="h-4 w-4" />
              图纸定位
            </TabsTrigger>
          </TabsList>
          <div className="text-sm text-muted-foreground">
            列表 {contractListRows.length} 条
            {selectedUnitCode ? `；当前柜位 ${selectedUnitCode}` : ""}
          </div>
        </div>

        <TabsContent value="list" className="mt-0">
          <Card>
            <CardHeader>
              <CardTitle>合同列表</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="space-y-2 md:col-span-2">
                  <Label>合同搜索</Label>
                  <Input
                    value={listKeyword}
                    onChange={(e) => setListKeyword(e.target.value)}
                    placeholder="合同号、主题、供应商、品牌、柜组"
                  />
                </div>
                <div className="space-y-2">
                  <Label>合同状态</Label>
                  <Select value={listStatus} onValueChange={setListStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="全部状态" />
                    </SelectTrigger>
                    <SelectContent className="z-50 bg-white border shadow-xl">
                      {CONTRACT_STATUS_OPTIONS.map((item) => (
                        <SelectItem key={item.value} value={item.value}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>柜组编码</Label>
                  <Input
                    value={listGroupCode}
                    onChange={(e) => setListGroupCode(e.target.value)}
                    placeholder="如 6030106076"
                  />
                </div>
              </div>

              <div className="overflow-x-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">状态</TableHead>
                      <TableHead className="whitespace-nowrap">合同编号</TableHead>
                      <TableHead className="whitespace-nowrap">合同类型</TableHead>
                      <TableHead className="min-w-48">供应商</TableHead>
                      <TableHead className="whitespace-nowrap">经营方式</TableHead>
                      <TableHead className="min-w-52">主题</TableHead>
                      <TableHead className="min-w-40">柜组</TableHead>
                      <TableHead className="whitespace-nowrap">品牌</TableHead>
                      <TableHead className="whitespace-nowrap">生效日期</TableHead>
                      <TableHead className="whitespace-nowrap">失效日期</TableHead>
                      <TableHead className="whitespace-nowrap text-right">月目标销售额</TableHead>
                      <TableHead className="whitespace-nowrap">付款方式</TableHead>
                      <TableHead className="whitespace-nowrap">是否清算</TableHead>
                      <TableHead className="whitespace-nowrap">结算位置</TableHead>
                      <TableHead className="whitespace-nowrap">录入员</TableHead>
                      <TableHead className="whitespace-nowrap text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contractsListQuery.isLoading ? (
                      <TableRow>
                        <TableCell colSpan={16} className="py-8 text-center text-muted-foreground">
                          加载合同列表中...
                        </TableCell>
                      </TableRow>
                    ) : contractsListQuery.error ? (
                      <TableRow>
                        <TableCell colSpan={16} className="py-8 text-center text-red-600">
                          {contractsListQuery.error instanceof Error ? contractsListQuery.error.message : "合同列表加载失败"}
                        </TableCell>
                      </TableRow>
                    ) : contractListRows.length ? (
                      contractListRows.map((item) => (
                        <TableRow key={item.cmcontno}>
                          <TableCell>
                            <Badge variant={item.cmstatus === "Y" ? "default" : "secondary"}>{item.status_label || "-"}</Badge>
                          </TableCell>
                          <TableCell className="font-medium">
                            <Button
                              variant="link"
                              className="h-auto p-0 text-left font-medium"
                              onClick={() => openContractDetail(item.cmcontno)}
                            >
                              {item.cmcontno}
                            </Button>
                          </TableCell>
                          <TableCell>{renderContractType(item.cmtype, item.contract_type_name)}</TableCell>
                          <TableCell>{renderSupplierInfo(item.cmsupid, item.supplier_name)}</TableCell>
                          <TableCell>{formatOperationMethod(item.cmwmid)}</TableCell>
                          <TableCell>{fmtValue(item.cmtitle)}</TableCell>
                          <TableCell>{renderGroupInfo(item.group_codes, item.group_names)}</TableCell>
                          <TableCell>{fmtValue(item.cmppname || item.range_brands)}</TableCell>
                          <TableCell>{fmtDate(item.cmeffdate)}</TableCell>
                          <TableCell>{fmtDate(item.cmlapdate)}</TableCell>
                          <TableCell className="text-right">{fmtMoney(item.cmmoney)}</TableCell>
                          <TableCell>{fmtValue(item.cmpaycode)}</TableCell>
                          <TableCell>{item.is_clear == null ? "-" : item.is_clear ? "是" : "否"}</TableCell>
                          <TableCell>{fmtValue(item.cmjsmkt)}</TableCell>
                          <TableCell>{fmtValue(item.cminputor)}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={!getPrimaryGroupCode(item)}
                              onClick={() => locateContractOnMap(item)}
                            >
                              <MapPin className="mr-2 h-4 w-4" />
                              定位图纸
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={16} className="py-8 text-center text-muted-foreground">
                          未找到符合条件的合同
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
              <div className="flex flex-col gap-3 text-xs text-muted-foreground md:flex-row md:items-center md:justify-between">
                <div>
                  第 {listPage + 1} 页，当前显示 {contractListRows.length} 条；是否清算取自 contbd，结算位置取自 contmain.cmjsmkt。
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Select value={String(listPageSize)} onValueChange={(value) => setListPageSize(Number(value))}>
                    <SelectTrigger className="h-8 w-[112px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="z-50 bg-white border shadow-xl">
                      <SelectItem value="50">每页 50</SelectItem>
                      <SelectItem value="100">每页 100</SelectItem>
                      <SelectItem value="200">每页 200</SelectItem>
                      <SelectItem value="500">每页 500</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!canGoPrevPage || contractsListQuery.isLoading}
                    onClick={() => setListPage((page) => Math.max(0, page - 1))}
                  >
                    <ChevronLeft className="mr-1 h-4 w-4" />
                    上一页
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!canGoNextPage || contractsListQuery.isLoading}
                    onClick={() => setListPage((page) => page + 1)}
                  >
                    下一页
                    <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="map" className="mt-0">
          <Card>
            <CardHeader>
              <CardTitle>合同图</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                {STATUS_LEGEND_ORDER.map((status) => {
                  const meta = STATUS_META[status];
                  return (
                    <div key={status} className="inline-flex items-center gap-2 rounded-md border bg-slate-50 px-3 py-1.5">
                      <span
                        className="inline-block h-3 w-3 rounded-sm border"
                        style={{ backgroundColor: meta.fill, borderColor: meta.stroke }}
                      />
                      <span>{meta.label}</span>
                    </div>
                  );
                })}
                {normalizedCounterKeyword ? (
                  <div className="inline-flex items-center gap-2 rounded-md border bg-amber-50 px-3 py-1.5 text-amber-800">
                    <span className="inline-block h-3 w-3 rounded-sm border border-amber-700 bg-amber-300" />
                    <span>柜位号搜索高亮</span>
                  </div>
                ) : null}
              </div>
              {renderMapCanvas()}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={mapFullscreenOpen} onOpenChange={setMapFullscreenOpen}>
        <DialogContent className="h-[96vh] max-h-[96vh] w-[96vw] max-w-[96vw] overflow-hidden p-3 sm:p-5">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapIcon className="h-5 w-5" />
              合同图全屏
            </DialogTitle>
          </DialogHeader>
          {renderMapCanvas(true)}
        </DialogContent>
      </Dialog>

      <Dialog open={mapLandscapeOpen} onOpenChange={setMapLandscapeOpen}>
        <DialogContent className="h-[100dvh] max-h-[100dvh] w-[100dvw] max-w-[100dvw] overflow-hidden rounded-none border-0 p-0">
          <div className="relative h-[100dvh] w-[100dvw] overflow-hidden bg-white">
            <div className="hidden h-full w-full sm:block">
              {renderMapCanvas(true, "landscape")}
            </div>
            <div className="flex h-full w-full items-center justify-center overflow-hidden bg-white sm:hidden">
              <div className="h-[100dvw] w-[100dvh] origin-center rotate-90">
                {renderMapCanvas(true, "landscape")}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-5xl max-h-[86vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              柜位合同 {detail?.unit.unit_code || selectedUnitCode || ""}
            </DialogTitle>
          </DialogHeader>

          {contractsQuery.isLoading ? (
            <div className="py-10 text-center text-muted-foreground">加载合同中...</div>
          ) : contractsQuery.error ? (
            <div className="py-10 text-center text-red-600">
              {contractsQuery.error instanceof Error ? contractsQuery.error.message : "合同加载失败"}
            </div>
          ) : !detail ? (
            <div className="py-10 text-center text-muted-foreground">暂无数据</div>
          ) : (
            <div className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">柜位号</div>
                  <div className="text-lg font-semibold">{detail.unit.unit_code}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">经营状态</div>
                  <div className="mt-1">
                    <Badge variant="outline" className={cn("font-medium", getStatusMeta(detailUnitStatus).badgeClassName)}>
                      {getStatusMeta(detailUnitStatus).label}
                    </Badge>
                  </div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">楼层</div>
                  <div className="text-lg font-semibold">
                    {detail.unit.building_code || "-"}-{detail.unit.floor_code || "-"}
                  </div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">合同数</div>
                  <div className="text-lg font-semibold">{contractRows.length}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">正式生效</div>
                  <div className="text-lg font-semibold">{activeContractCount}</div>
                </div>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>正式生效合同</CardTitle>
                </CardHeader>
                <CardContent>
                  {activeContract ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">合同编号</div>
                        <Button
                          variant="link"
                          className="h-auto p-0 font-semibold text-left"
                          onClick={() => openContractDetail(activeContract.cmfcontno)}
                        >
                          {activeContract.cmfcontno}
                        </Button>
                      </div>
                      <div>
                        <div className="text-muted-foreground">主题</div>
                        <div className="font-semibold">{activeContract.cmtitle || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">供应商</div>
                        <div className="font-semibold">{renderSupplierInfo(activeContract.cmsupid, activeContract.supplier_name)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">有效期</div>
                        <div>{fmtDate(activeContract.cmeffdate)} 至 {fmtDate(activeContract.cmlapdate)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">品牌</div>
                        <div>{activeContract.cmppname || activeContract.cmfbrand || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">月目标销售额</div>
                        <div>{fmtMoney(activeContract.cmmoney)}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">当前柜位没有正式生效合同</div>
                  )}
                </CardContent>
              </Card>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>状态</TableHead>
                    <TableHead>合同编号</TableHead>
                    <TableHead>主题</TableHead>
                    <TableHead>供应商</TableHead>
                    <TableHead>品牌</TableHead>
                    <TableHead>合同有效期</TableHead>
                    <TableHead>经营范围有效期</TableHead>
                    <TableHead>面积</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contractRows.length ? (
                    contractRows.map((item) => (
                      <TableRow key={`${item.cmfcontno}-${item.cmfbrand || ""}`}>
                        <TableCell>
                          <Badge variant={item.is_current_effective ? "default" : "secondary"}>
                            {item.is_current_effective ? "正式生效" : item.status_label}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium">
                          <Button
                            variant="link"
                            className="h-auto p-0 text-left font-medium"
                            onClick={() => openContractDetail(item.cmfcontno)}
                          >
                            {item.cmfcontno}
                          </Button>
                        </TableCell>
                        <TableCell>{item.cmtitle || "-"}</TableCell>
                        <TableCell>{renderSupplierInfo(item.cmsupid, item.supplier_name)}</TableCell>
                        <TableCell>{item.cmppname || item.cmfbrand || "-"}</TableCell>
                        <TableCell>{fmtDate(item.cmeffdate)} 至 {fmtDate(item.cmlapdate)}</TableCell>
                        <TableCell>{fmtDate(item.cmfeffdate)} 至 {fmtDate(item.cmflapdate)}</TableCell>
                        <TableCell>{fmtMoney(item.cmfjzmj ?? item.cmfsymj ?? item.cmfzjmj)}</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={!isFutureDate(item.cmeffdate)}
                            onClick={() => startDecorationFromContract(item.cmfcontno)}
                          >
                            <HardHat className="mr-2 h-4 w-4" />
                            发起装修
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                        这个柜位没有匹配到 ERP 合同
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog
        open={contractDetailOpen}
        onOpenChange={(nextOpen) => {
          setContractDetailOpen(nextOpen);
          if (!nextOpen && reopenUnitDialogOnContractClose) {
            setDetailOpen(true);
            setReopenUnitDialogOnContractClose(false);
          }
        }}
      >
        <DialogContent className="max-w-6xl max-h-[88vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              合同明细 {selectedContractNo || ""}
            </DialogTitle>
          </DialogHeader>

          {contractDetailQuery.isLoading ? (
            <div className="py-10 text-center text-muted-foreground">加载合同明细中...</div>
          ) : contractDetailQuery.error ? (
            <div className="py-10 text-center text-red-600">
              {contractDetailQuery.error instanceof Error ? contractDetailQuery.error.message : "合同明细加载失败"}
            </div>
          ) : !contractDetail ? (
            <div className="py-10 text-center text-muted-foreground">暂无合同明细</div>
          ) : (
            <div className="space-y-5">
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  disabled={!isFutureDate(contractMain?.cmeffdate)}
                  onClick={() => startDecorationFromContract(contractDetail.contract_no)}
                >
                  <HardHat className="mr-2 h-4 w-4" />
                  发起装修流程
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">合同编号</div>
                  <div className="text-lg font-semibold">{contractDetail.contract_no}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">合同状态</div>
                  <div className="text-lg font-semibold">{contractMain?.status_label || "-"}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">主题</div>
                  <div className="text-sm font-semibold">{contractMain?.cmtitle || "-"}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">供应商</div>
                  <div className="text-sm font-semibold">{renderSupplierInfo(contractMain?.cmsupid, contractMain?.supplier_name)}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">品牌</div>
                  <div className="text-sm font-semibold">{contractMain?.cmppname || "-"}</div>
                </div>
                <div className="rounded border p-3">
                  <div className="text-xs text-muted-foreground">合同有效期</div>
                  <div className="text-sm font-semibold">
                    {fmtDate(contractMain?.cmeffdate)} 至 {fmtDate(contractMain?.cmlapdate)}
                  </div>
                </div>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>主合同信息</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">经营单元编码</div>
                    <div>{fmtValue(contractMain?.cmchar9)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">合同类型</div>
                    <div>{renderContractType(contractMain?.cmtype, contractMain?.contract_type_name)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">经营方式</div>
                    <div>{formatOperationMethod(contractMain?.cmwmid)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">月目标销售额</div>
                    <div>{fmtMoney(contractMain?.cmmoney)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">结算位置</div>
                    <div>{fmtValue(contractMain?.cmjsmkt)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">付款方式</div>
                    <div>{fmtValue(contractMain?.cmpaycode)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">签约日期</div>
                    <div>{fmtDate(contractMain?.signdate)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">交付日期</div>
                    <div>{fmtDate(contractMain?.deliverydate)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">装修期</div>
                    <div>{fmtDate(contractMain?.zxqsrq)} 至 {fmtDate(contractMain?.zxjzrq)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">联系方式</div>
                    <div>{fmtValue(contractMain?.cmtel || contractMain?.cmcontact)}</div>
                  </div>
                  <div className="md:col-span-2">
                    <div className="text-muted-foreground">合同标的</div>
                    <div>{fmtValue(contractMain?.cmobject)}</div>
                  </div>
                  <div className="md:col-span-2">
                    <div className="text-muted-foreground">备注</div>
                    <div>{fmtValue(contractMain?.cmmemo)}</div>
                  </div>
                </CardContent>
              </Card>

              <Tabs defaultValue="contmanaframe" className="space-y-4">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="contmanaframe">所属柜组 {contractDetail.counts.contmanaframe}</TabsTrigger>
                  <TabsTrigger value="contbd">保底 {contractDetail.counts.contbd}</TabsTrigger>
                  <TabsTrigger value="contcyclist">租赁周期费用 {contractDetail.counts.contcyclist}</TabsTrigger>
                  <TabsTrigger value="contsupcharge">供应商合同费用 {contractDetail.counts.contsupcharge}</TabsTrigger>
                </TabsList>

                <TabsContent value="contmanaframe">
                  <DetailTable
                    rows={contractDetail.contmanaframe}
                    emptyText="暂无经营范围明细"
                    columns={[
                      { header: "柜组", render: (row) => renderGroupInfo(row.cmfmfid, row.group_name) },
                      { header: "门店", render: (row) => fmtValue(row.cmfmarket) },
                      { header: "品牌", render: (row) => fmtValue(row.cmfbrand) },
                      { header: "扣率1", render: (row) => fmtPercent(row.cmfnum1) },
                      { header: "扣率2", render: (row) => fmtPercent(row.cmfnum2) },
                      { header: "扣率3", render: (row) => fmtPercent(row.cmfnum3) },
                      { header: "扣率4", render: (row) => fmtPercent(row.cmfnum4) },
                      { header: "扣率5", render: (row) => fmtPercent(row.cmfnum5) },
                      { header: "有效期", render: (row) => `${fmtDate(row.cmfeffdate)} 至 ${fmtDate(row.cmflapdate)}` },
                      { header: "契约面积", render: (row) => fmtMoney(row.cmfjzmj) },
                      { header: "实际面积", render: (row) => fmtMoney(row.cmfsymj) },
                      { header: "租金面积", render: (row) => fmtMoney(row.cmfzjmj) },
                      { header: "地址/区", render: (row) => [row.cmfaddr, row.cmfarea].filter(Boolean).join(" / ") || "-" },
                      { header: "备注", render: (row) => fmtValue(row.cmfmemo) },
                    ]}
                  />
                </TabsContent>

                <TabsContent value="contbd">
                  <DetailTable
                    rows={contractDetail.contbd}
                    emptyText="暂无保底超额明细"
                    columns={[
                      { header: "序号", render: (row) => fmtValue(row.cbseqno) },
                      { header: "柜组", render: (row) => renderGroupInfo(row.cbmfid, row.group_name) },
                      { header: "有效期", render: (row) => `${fmtDate(row.cbeffdate)} 至 ${fmtDate(row.cblapdate)}` },
                      { header: "是否保底", render: (row) => fmtYesNo(row.cbisrunbd) },
                      { header: "是否清算", render: (row) => fmtYesNo(row.cbisrunqs) },
                      { header: "保底额", render: (row) => fmtMoney(row.cbsum) },
                      { header: "保底比率", render: (row) => fmtPercent(row.cbrate) },
                      { header: "保底毛利", render: (row) => fmtMoney(row.cbprofit) },
                      { header: "租金单价", render: (row) => fmtMoney(row.cbrentprice) },
                      { header: "管理费单价", render: (row) => fmtMoney(row.cbnamaprice) },
                      { header: "推广费单价", render: (row) => fmtMoney(row.cbpopprice) },
                      { header: "销售考核", render: (row) => fmtMoney(row.cbsalekh) },
                      { header: "完成金额", render: (row) => fmtMoney(row.xssr) },
                    ]}
                  />
                </TabsContent>

                <TabsContent value="contcyclist">
                  <DetailTable
                    rows={contractDetail.contcyclist}
                    emptyText="暂无周期费用明细"
                    columns={[
                      { header: "序号", render: (row) => fmtValue(row.cclseqno) },
                      { header: "项目编号", render: (row) => fmtValue(row.cclitemid) },
                      { header: "柜组", render: (row) => renderGroupInfo(row.cclmfid, row.group_name) },
                      { header: "有效期", render: (row) => `${fmtDate(row.ccleffdate)} 至 ${fmtDate(row.ccllapdate)}` },
                      { header: "单位", render: (row) => fmtValue(row.cclitemunit) },
                      { header: "单价", render: (row) => fmtMoney(row.cclitemprice) },
                      { header: "总金额", render: (row) => fmtMoney(row.cclsumamount) },
                      { header: "预收类型", render: (row) => fmtValue(row.cclystype) },
                      { header: "月数", render: (row) => fmtValue(row.cclysnum) },
                      { header: "免除", render: (row) => fmtValue(row.cclisfree) },
                    ]}
                  />
                </TabsContent>

                <TabsContent value="contsupcharge">
                  <div className="overflow-x-auto">
                    <DetailTable
                      rows={contractDetail.contsupcharge}
                      emptyText="暂无供应商费用明细"
                      columns={[
                        { header: "行号", render: (row) => fmtValue(row.cscrowno), className: "whitespace-nowrap" },
                        { header: "ID", render: (row) => fmtValue(row.cscchargecode), className: "whitespace-nowrap" },
                        { header: "柜组", render: (row) => renderGroupInfo(row.cscmfid, row.group_name), className: "min-w-32" },
                        { header: "费用项目", render: (row) => fmtValue(row.cscchargename), className: "min-w-40 whitespace-nowrap" },
                        { header: "是否帐扣", render: (row) => fmtYesNo(row.cscisdeduct), className: "whitespace-nowrap" },
                        { header: "结算方式", render: (row) => fmtSettlementMethod(row.cscismcjs), className: "whitespace-nowrap" },
                        { header: "是否返还型费用", render: (row) => fmtYesNo(row.cscisret), className: "whitespace-nowrap" },
                        { header: "返还日期", render: (row) => fmtDate(row.cscretdate), className: "whitespace-nowrap" },
                        { header: "生效日期", render: (row) => fmtDate(row.csceffdate), className: "whitespace-nowrap" },
                        { header: "失效日期", render: (row) => fmtDate(row.csclapdate), className: "whitespace-nowrap" },
                        { header: "指标", render: (row) => fmtMoney(row.cscvalue), className: "whitespace-nowrap" },
                      ]}
                    />
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
