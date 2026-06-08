import { Flag } from "lucide-react";

import { FilterSelect } from "@/components/analysis/common/AnalysisFilterBar";
import { SelectItem } from "@/components/ui/select";
import type { DiagnosisPriorityFilter } from "@/lib/diagnosis";
import type { OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

const PRIORITY_BADGE: Record<
  OpportunityPriority,
  { label: string; dotClass: string; textClass: string; pillClass: string }
> = {
  high: {
    label: "高",
    dotClass: "bg-red-500",
    textClass: "text-red-600",
    pillClass: "bg-red-50",
  },
  medium: {
    label: "中",
    dotClass: "bg-amber-500",
    textClass: "text-amber-600",
    pillClass: "bg-amber-50",
  },
  low: {
    label: "低",
    dotClass: "bg-emerald-500",
    textClass: "text-emerald-600",
    pillClass: "bg-emerald-50",
  },
};

const PRIORITY_DISPLAY: Record<DiagnosisPriorityFilter, string> = {
  all: "所有行动优先级",
  high: "高 行动优先级",
  medium: "中 行动优先级",
  low: "低 行动优先级",
};

function PriorityFilterLabel({ priority }: { priority: OpportunityPriority }) {
  const meta = PRIORITY_BADGE[priority];
  return (
    <span className="inline-flex items-center gap-2 text-xs">
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium",
          meta.pillClass,
          meta.textClass,
        )}
      >
        <span className={cn("size-1.5 rounded-full", meta.dotClass)} aria-hidden />
        {meta.label}
      </span>
      <span className="text-foreground">行动优先级</span>
    </span>
  );
}

type DiagnosisPrioritySelectProps = {
  value: DiagnosisPriorityFilter;
  onChange: (value: DiagnosisPriorityFilter) => void;
  className?: string;
};

/** 诊断中心行动优先级筛选 */
export function DiagnosisPrioritySelect({
  value,
  onChange,
  className,
}: DiagnosisPrioritySelectProps) {
  return (
    <FilterSelect
      icon={Flag}
      value={value}
      displayValue={PRIORITY_DISPLAY[value]}
      placeholder="所有行动优先级"
      title="行动优先级筛选"
      onValueChange={(next) => onChange(next as DiagnosisPriorityFilter)}
      className={className}
    >
      <SelectItem value="all" className="text-xs">
        所有行动优先级
      </SelectItem>
      {(["high", "medium", "low"] as const).map((priority) => (
        <SelectItem key={priority} value={priority} className="text-xs">
          <PriorityFilterLabel priority={priority} />
        </SelectItem>
      ))}
    </FilterSelect>
  );
}
