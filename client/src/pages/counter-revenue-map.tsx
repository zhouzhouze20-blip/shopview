import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

type CounterStatus = "occupied" | "vacant";

interface RevenueCounter {
  id: string;
  brand: string;
  target: number;
  actual: number;
  status: CounterStatus;
}

interface RevenueUnit extends RevenueCounter {
  x: number;
  y: number;
  w: number;
  h: number;
}

const TOTAL_COUNTERS = 306;
const OCCUPIED_COUNTERS = 283;
const FLOOR_PLAN_IMAGE = "/floorplans/1f-plan.png";

const units: RevenueUnit[] = [
  { id: "A101", brand: "BALLY", target: 62000, actual: 52600, status: "occupied", x: 6, y: 12, w: 9, h: 10 },
  { id: "A102", brand: "NIKE", target: 88000, actual: 91000, status: "occupied", x: 17, y: 12, w: 10, h: 10 },
  { id: "A103", brand: "MUJI", target: 74000, actual: 66200, status: "occupied", x: 29, y: 12, w: 10, h: 10 },
  { id: "A104", brand: "CHANEL", target: 96000, actual: 101400, status: "occupied", x: 41, y: 12, w: 11, h: 10 },
  { id: "A105", brand: "空厅", target: 68000, actual: 0, status: "vacant", x: 54, y: 12, w: 10, h: 10 },
  { id: "A106", brand: "FILA", target: 56000, actual: 49200, status: "occupied", x: 66, y: 12, w: 9, h: 10 },
  { id: "A107", brand: "BALLY", target: 72000, actual: 68400, status: "occupied", x: 22, y: 15, w: 10, h: 8 },
  { id: "A112", brand: "PAUL&SHARK", target: 76000, actual: 70200, status: "occupied", x: 25, y: 85, w: 12, h: 9 },

  { id: "B201", brand: "ZARA", target: 82000, actual: 73800, status: "occupied", x: 8, y: 26, w: 12, h: 12 },
  { id: "B202", brand: "Apple", target: 110000, actual: 118800, status: "occupied", x: 22, y: 26, w: 12, h: 12 },
  { id: "B203", brand: "Lululemon", target: 76000, actual: 64200, status: "occupied", x: 36, y: 26, w: 11, h: 12 },
  { id: "B204", brand: "空厅", target: 66000, actual: 0, status: "vacant", x: 50, y: 26, w: 10, h: 12 },
  { id: "B205", brand: "ANTA", target: 64000, actual: 60800, status: "occupied", x: 62, y: 26, w: 11, h: 12 },
  { id: "B206", brand: "BOSE", target: 58000, actual: 60300, status: "occupied", x: 75, y: 26, w: 12, h: 12 },

  { id: "C301", brand: "H&M", target: 72000, actual: 60500, status: "occupied", x: 6, y: 42, w: 14, h: 14 },
  { id: "C302", brand: "Coach", target: 86000, actual: 77400, status: "occupied", x: 22, y: 42, w: 12, h: 14 },
  { id: "C303", brand: "LEGO", target: 64000, actual: 69800, status: "occupied", x: 36, y: 42, w: 11, h: 14 },
  { id: "C304", brand: "空厅", target: 60000, actual: 0, status: "vacant", x: 49, y: 42, w: 10, h: 14 },
  { id: "C305", brand: "BOSS", target: 92000, actual: 98400, status: "occupied", x: 61, y: 42, w: 12, h: 14 },
  { id: "C306", brand: "UNIQLO", target: 78000, actual: 75700, status: "occupied", x: 75, y: 42, w: 13, h: 14 },

  { id: "D401", brand: "adidas", target: 68000, actual: 57100, status: "occupied", x: 10, y: 60, w: 12, h: 12 },
  { id: "D402", brand: "空厅", target: 52000, actual: 0, status: "vacant", x: 24, y: 60, w: 10, h: 12 },
  { id: "D403", brand: "MUJI", target: 70000, actual: 73500, status: "occupied", x: 36, y: 60, w: 12, h: 12 },
  { id: "D404", brand: "NIKE", target: 82000, actual: 75900, status: "occupied", x: 50, y: 60, w: 12, h: 12 },
  { id: "D405", brand: "ZARA", target: 74000, actual: 70300, status: "occupied", x: 64, y: 60, w: 12, h: 12 },
  { id: "D406", brand: "空厅", target: 58000, actual: 0, status: "vacant", x: 78, y: 60, w: 10, h: 12 },
];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(value);

const getPerformanceTone = (status: CounterStatus, ratio: number) => {
  if (status === "vacant") {
    return { background: "#f1f5f9", border: "#e2e8f0" };
  }
  if (ratio < 0.85) {
    return { background: "#ffe4e6", border: "#fecdd3" };
  }
  if (ratio <= 1) {
    return { background: "#fef3c7", border: "#fde68a" };
  }
  return { background: "#d1fae5", border: "#a7f3d0" };
};

export default function CounterRevenueMapPage() {
  const [selectedCounter, setSelectedCounter] = useState<RevenueUnit | null>(null);
  const [clickCoords, setClickCoords] = useState<{ x: number; y: number } | null>(null);

  const selectedRatio = useMemo(() => {
    if (!selectedCounter || selectedCounter.target === 0) return 0;
    return selectedCounter.actual / selectedCounter.target;
  }, [selectedCounter]);

  const selectedProgress = Math.min(selectedRatio * 100, 100);
  const marketingIncome = selectedCounter ? Math.round(selectedCounter.actual * 0.05) : 0;
  const isPanelOpen = Boolean(selectedCounter || clickCoords);

  return (
    <div className="w-full p-6 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">柜位收益图</h1>
          <p className="text-sm text-slate-500 mt-1">以完成率着色的柜位平面图模拟，点击柜位查看收益详情。</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-slate-900 text-white">实时监控</Badge>
          <Badge variant="outline" className="border-slate-200 text-slate-600">
            经营数据
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">总位</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-slate-900">{TOTAL_COUNTERS}</div>
            <p className="text-xs text-slate-500 mt-1">整体铺位规模</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">已租</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-emerald-600">{OCCUPIED_COUNTERS}</div>
            <p className="text-xs text-slate-500 mt-1">收入来源核心区</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-500">空置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold text-slate-500">
              {TOTAL_COUNTERS - OCCUPIED_COUNTERS}
            </div>
            <p className="text-xs text-slate-500 mt-1">待招商空厅</p>
          </CardContent>
        </Card>
      </div>

      <div className="relative">
        <Card className="overflow-hidden">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>空间映射布局</CardTitle>
              <p className="text-sm text-slate-500 mt-1">完成率低于 85% 为红色，85%-100% 为黄色，超过 100% 为绿色。</p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <span>&lt; 85%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span>85%-100%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span>&gt; 100%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span>空厅</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4">
              <div
                className="MapContainer relative w-full overflow-hidden rounded-lg bg-white shadow-sm"
                onClick={(event) => {
                  const bounds = event.currentTarget.getBoundingClientRect();
                  const x = ((event.clientX - bounds.left) / bounds.width) * 100;
                  const y = ((event.clientY - bounds.top) / bounds.height) * 100;
                  setClickCoords({ x, y });
                  console.log(`点击位置: x=${x.toFixed(2)}%, y=${y.toFixed(2)}%`);
                }}
              >
                <img
                  src={FLOOR_PLAN_IMAGE}
                  alt="1F 平面图"
                  className="block w-full h-auto pointer-events-none"
                />
                {units.map((unit) => {
                  const ratio = unit.target === 0 ? 0 : unit.actual / unit.target;
                  const tileTone = getPerformanceTone(unit.status, ratio);
                  const isSelected = selectedCounter?.id === unit.id;

                  return (
                    <div
                      key={unit.id}
                      onClick={() => setSelectedCounter(unit)}
                      style={{
                        left: `${unit.x}%`,
                        top: `${unit.y}%`,
                        width: `${unit.w}%`,
                        height: `${unit.h}%`,
                        opacity: 0.6,
                        transform: "translate(-50%, -50%)",
                        backgroundColor: tileTone.background,
                        borderColor: tileTone.border,
                      }}
                      className={cn(
                        "absolute rounded-md border px-2 py-1 text-center text-[10px] leading-tight transition-shadow",
                        isSelected ? "ring-2 ring-slate-900/60" : "hover:shadow-sm"
                      )}
                    >
                      <div className="font-semibold text-slate-500">{unit.id}</div>
                      <div className={cn("font-semibold", unit.status === "vacant" && "text-slate-400")}>
                        {unit.status === "vacant" ? "空厅" : unit.brand}
                      </div>
                      <div className="text-slate-500">
                        {unit.status === "vacant" ? "待招商" : `完成率 ${Math.round(ratio * 100)}%`}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <div
          className={cn(
            "absolute right-0 top-0 h-full w-full max-w-sm transform bg-white shadow-xl transition-transform duration-300 sm:w-[360px]",
            isPanelOpen ? "translate-x-0" : "translate-x-full"
          )}
        >
          <div className="flex h-full flex-col border-l border-slate-200 p-6">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-slate-500">柜位详情</div>
                <h2 className="text-xl font-semibold text-slate-900 mt-1">
                  {selectedCounter?.brand || "空厅"}
                </h2>
                {selectedCounter && (
                  <Badge
                    className={cn(
                      "mt-2",
                      selectedCounter.status === "vacant"
                        ? "bg-slate-100 text-slate-500"
                        : "bg-emerald-100 text-emerald-700"
                    )}
                  >
                    {selectedCounter.status === "vacant" ? "空厅" : "已租"}
                  </Badge>
                )}
              </div>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => {
                  setSelectedCounter(null);
                  setClickCoords(null);
                }}
                className="text-slate-500 hover:text-slate-800"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="mt-6 space-y-4">
              {clickCoords && (
                <div className="rounded-lg border border-dashed border-slate-200 p-4">
                  <div className="text-xs text-slate-500">点击坐标（百分比）</div>
                  <div className="mt-2 flex items-center justify-between text-sm text-slate-600">
                    <span>left</span>
                    <span className="font-semibold text-slate-900">{clickCoords.x.toFixed(2)}%</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-sm text-slate-600">
                    <span>top</span>
                    <span className="font-semibold text-slate-900">{clickCoords.y.toFixed(2)}%</span>
                  </div>
                </div>
              )}
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="text-xs text-slate-500">收益目标</div>
                <div className="text-lg font-semibold text-slate-900">
                  ¥{formatCurrency(selectedCounter?.target ?? 0)}
                </div>
                <div className="mt-3 text-xs text-slate-500">实收</div>
                <div className="text-lg font-semibold text-slate-900">
                  ¥{formatCurrency(selectedCounter?.actual ?? 0)}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm text-slate-600">
                  <span>应收账款完成率</span>
                  <span className="font-semibold text-slate-900">
                    {Math.round(selectedRatio * 100)}%
                  </span>
                </div>
                <Progress value={selectedProgress} className="h-3 bg-slate-100" />
                <div className="text-xs text-slate-500">
                  {selectedRatio >= 1 ? "超额完成" : "努力达成"} · 目标完成进度
                </div>
              </div>

              <div className="rounded-lg border border-dashed border-slate-200 p-4">
                <div className="text-xs text-slate-500">营销沉淀收益</div>
                <div className="text-lg font-semibold text-slate-900">
                  ¥{formatCurrency(marketingIncome)}
                </div>
                <p className="text-xs text-slate-500 mt-1">按实收的 5% 固定计算</p>
              </div>
            </div>

            {!selectedCounter && (
              <div className="mt-6 text-sm text-slate-400">点击柜位查看收益数据</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
