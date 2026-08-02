import { MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

type MobileSpecialSaleMarkerProps = {
  unitCode: string;
  selected?: boolean;
  highlighted?: boolean;
  amount?: number | null;
  className?: string;
  onSelect: () => void;
};

const money = (value: number) =>
  Number(value || 0).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

export function MobileSpecialSaleMarker({
  unitCode,
  selected = false,
  highlighted = false,
  amount,
  className,
  onSelect,
}: MobileSpecialSaleMarkerProps) {
  return (
    <button
      type="button"
      data-testid="mobile-special-sale-unit"
      aria-label={`选择${unitCode}逻辑柜位`}
      className={cn(
        "absolute right-4 top-4 z-20 w-44 rounded-xl border-2 border-dashed bg-amber-50/95 p-3 text-left shadow-lg backdrop-blur-sm transition hover:-translate-y-0.5 hover:border-amber-600 hover:shadow-xl",
        selected && "border-blue-600 bg-blue-50/95 ring-2 ring-blue-300",
        highlighted && !selected && "border-amber-700 bg-amber-100 ring-2 ring-amber-300",
        className,
      )}
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <span className="flex items-center gap-2">
        <span className="rounded-lg bg-amber-500 p-1.5 text-white">
          <MapPin className="h-4 w-4" />
        </span>
        <span>
          <span className="block text-sm font-bold text-slate-900">{unitCode}</span>
          <span className="block text-[11px] text-amber-800">逻辑柜位 · 不占固定铺位</span>
        </span>
      </span>
      {amount != null ? (
        <span className="mt-2 block border-t border-amber-200 pt-2 text-sm font-bold text-emerald-700">
          收益 ¥{money(amount)}
        </span>
      ) : (
        <span className="mt-2 block border-t border-amber-200 pt-2 text-xs text-slate-600">
          可绑定本楼层特卖合同
        </span>
      )}
    </button>
  );
}
