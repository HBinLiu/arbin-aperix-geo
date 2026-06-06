import { Check, ChevronDown, Settings2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  PLATFORM_MATRIX_METRICS,
  PLATFORM_MATRIX_ROW_OPTIONS,
} from "@/lib/analysis/platform";
import type { PlatformMatrixMetricId, PlatformMatrixRowDimension } from "@/types";
import { cn } from "@/lib/utils";

type PlatformMatrixConfigProps = {
  rowDimension: PlatformMatrixRowDimension;
  metricId: PlatformMatrixMetricId;
  onRowDimensionChange: (value: PlatformMatrixRowDimension) => void;
  onMetricChange: (value: PlatformMatrixMetricId) => void;
};

function ConfigOption({
  label,
  selected,
  onSelect,
}: {
  label: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className="hover:bg-muted/80 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors"
      onClick={onSelect}
    >
      <span className="flex size-4 shrink-0 items-center justify-center">
        {selected ? <Check className="text-foreground size-4" aria-hidden /> : null}
      </span>
      <span className="font-xs font-normal">{label}</span>
    </button>
  );
}

export function PlatformMatrixConfig({
  rowDimension,
  metricId,
  onRowDimensionChange,
  onMetricChange,
}: PlatformMatrixConfigProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  return (
    <div ref={rootRef} className="relative shrink-0 self-center">
      <Button
        type="button"
        variant="primaryOutline"
        size="sm"
        className="h-9 items-center gap-1.5 px-3"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((prev) => !prev)}
      >
        <Settings2 className="size-3.5 shrink-0" aria-hidden />
        配置
        <ChevronDown
          className={cn("size-3.5 shrink-0 transition-transform", open && "rotate-180")}
          aria-hidden
        />
      </Button>

      {open ? (
        <div
          role="menu"
          className="border-border absolute top-[calc(100%+0.375rem)] right-0 z-20 w-45 rounded-lg border bg-white p-2 shadow-lg"
        >
          <p className="text-foreground p-1 text-sm font-bold">行</p>
          <div className="mb-2">
            {PLATFORM_MATRIX_ROW_OPTIONS.map((option) => (
              <ConfigOption
                key={option.id}
                label={option.label}
                selected={rowDimension === option.id}
                onSelect={() => {
                  onRowDimensionChange(option.id);
                  setOpen(false);
                }}
              />
            ))}
          </div>
          <p className="text-foreground p-1 text-sm font-bold">值</p>
          <div>
            {PLATFORM_MATRIX_METRICS.map((option) => (
              <ConfigOption
                key={option.id}
                label={option.label}
                selected={metricId === option.id}
                onSelect={() => {
                  onMetricChange(option.id);
                  setOpen(false);
                }}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
