import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Loader2 } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiGet } from "@/lib/api";

export type InventoryFilterField = "supplier" | "group" | "goods_code" | "goods_name" | "barcode";

export type InventoryFilterOption = {
  value: string;
  label: string;
  code: string;
  name: string;
};

type InventoryFilterOptionsResponse = {
  options: InventoryFilterOption[];
};

type InventoryFilterDates = {
  start_date: string;
  end_date: string;
};

export function InventoryFilterAutocomplete({
  field,
  label,
  placeholder,
  inputMode,
  displayValue,
  filterValue,
  onInputChange,
  onSelect,
  optionsEndpoint,
  dates,
  inputIdPrefix = "inventory",
}: {
  field: InventoryFilterField;
  label: string;
  placeholder: string;
  inputMode?: "numeric";
  displayValue: string;
  filterValue: string;
  onInputChange: (value: string) => void;
  onSelect: (option: InventoryFilterOption) => void;
  optionsEndpoint: string;
  dates?: InventoryFilterDates;
  inputIdPrefix?: string;
}) {
  const [focused, setFocused] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(displayValue.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [displayValue]);

  const optionQueryString = useMemo(() => {
    const query = new URLSearchParams({ field, q: debouncedSearch, limit: "20" });
    if (dates) {
      query.set("start_date", dates.start_date);
      query.set("end_date", dates.end_date);
    }
    return query.toString();
  }, [debouncedSearch, dates, field]);
  const optionsQuery = useQuery<InventoryFilterOptionsResponse>({
    queryKey: [optionsEndpoint, optionQueryString],
    queryFn: () => apiGet(`${optionsEndpoint}?${optionQueryString}`),
    enabled: focused
      && debouncedSearch.length > 0
      && (!dates || Boolean(dates.start_date && dates.end_date)),
  });

  const showOptions = focused && displayValue.trim().length > 0;
  const inputId = `${inputIdPrefix}-${field.replace("_", "-")}`;
  const alignOptionsRight = field === "goods_name" || field === "barcode";

  return (
    <div className="relative space-y-2">
      <Label htmlFor={inputId}>{label}</Label>
      <Input
        id={inputId}
        value={displayValue}
        onChange={(event) => onInputChange(event.target.value)}
        onFocus={(event) => {
          setFocused(true);
          if (displayValue !== filterValue) event.currentTarget.select();
        }}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        inputMode={inputMode}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showOptions}
        aria-controls={`${inputId}-options`}
      />
      {showOptions && (
        <div
          id={`${inputId}-options`}
          role="listbox"
          className={`absolute top-full z-50 mt-1 max-h-72 w-[520px] max-w-[calc(100vw-2rem)] overflow-y-auto rounded-md border bg-white p-1 shadow-lg ${alignOptionsRight ? "right-0" : "left-0"}`}
        >
          {optionsQuery.isFetching ? (
            <div className="flex items-center justify-center px-3 py-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />正在匹配…
            </div>
          ) : optionsQuery.data?.options.length ? (
            optionsQuery.data.options.map((option) => (
              <button
                key={`${option.value}-${option.label}`}
                type="button"
                role="option"
                aria-selected={filterValue === option.value}
                className="flex w-full items-start gap-2 rounded px-2 py-2 text-left text-sm hover:bg-slate-100"
                onMouseDown={(event) => {
                  event.preventDefault();
                  onSelect(option);
                  setFocused(false);
                }}
              >
                <Check className={`mt-0.5 h-4 w-4 shrink-0 ${filterValue === option.value ? "opacity-100" : "opacity-0"}`} />
                <span className="min-w-0 whitespace-normal break-words leading-5">{option.label}</span>
              </button>
            ))
          ) : debouncedSearch === displayValue.trim() ? (
            <div className="px-3 py-6 text-center text-sm text-muted-foreground">没有匹配项</div>
          ) : (
            <div className="px-3 py-6 text-center text-sm text-muted-foreground">正在输入…</div>
          )}
        </div>
      )}
    </div>
  );
}
