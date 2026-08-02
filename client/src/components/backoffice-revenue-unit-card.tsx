import { Building2 } from "lucide-react";
import { cn } from "@/lib/utils";

type BackofficeRevenueUnitCardProps = {
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

export function BackofficeRevenueUnitCard({
  unitCode,
  selected = false,
  highlighted = false,
  amount,
  className,
  onSelect,
}: BackofficeRevenueUnitCardProps) {
  return (
    <button
      type="button"
      data-testid="backoffice-revenue-unit"
      aria-label={`选择${unitCode}逻辑柜位`}
      className={cn(
        "w-72 rounded-xl border-2 border-dashed border-violet-400 bg-violet-50 p-4 text-left shadow-md transition hover:-translate-y-0.5 hover:border-violet-600 hover:shadow-lg",
        selected && "border-blue-600 bg-blue-50 ring-2 ring-blue-300",
        highlighted && !selected && "border-violet-700 bg-violet-100 ring-2 ring-violet-300",
        className,
      )}
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <span className="flex items-center gap-3">
        <span className="rounded-lg bg-violet-600 p-2 text-white">
          <Building2 className="h-5 w-5" />
        </span>
        <span>
          <span className="block text-base font-bold text-slate-900">{unitCode}</span>
          <span className="block text-xs text-violet-800">店级逻辑柜位 · 不归属实体楼层</span>
        </span>
      </span>
      {amount != null ? (
        <span className="mt-3 block border-t border-violet-200 pt-3 text-sm font-bold text-emerald-700">
          收益 ¥{money(amount)}
        </span>
      ) : (
        <span className="mt-3 block border-t border-violet-200 pt-3 text-xs text-slate-600">
          可绑定本门店后台部门合同
        </span>
      )}
    </button>
  );
}
