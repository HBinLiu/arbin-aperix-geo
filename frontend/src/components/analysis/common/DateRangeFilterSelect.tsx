import { useEffect, useMemo, useState } from "react";
import { zhCN } from "date-fns/locale";
import { Calendar as CalendarIcon, ChevronDown } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  ANALYSIS_DATE_PRESETS,
  dateRangeDays,
  formatDateRangeLabel,
  isoToLocalDate,
  localDatesToIso,
} from "@/lib/analysis";
import { cn } from "@/lib/utils";

type DateRangeFilterSelectProps = {
  from: string;
  to: string;
  onChange: (range: { from: string; to: string }) => void;
  className?: string;
  disabled?: boolean;
};

type DraftAnchors = {
  start?: Date;
  end?: Date;
};

const triggerClassName = cn(
  "border-border inline-flex h-9 w-auto items-center gap-2 rounded-lg border bg-white px-3 text-sm font-normal shadow-none",
  "hover:border-border hover:shadow-none",
  "focus:border-border focus:shadow-none focus:ring-0 focus:outline-hidden",
  "focus-visible:border-border focus-visible:shadow-none focus-visible:ring-0",
);

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function orderedRange(start: Date, end: Date): { from: Date; to: Date } {
  return start <= end ? { from: start, to: end } : { from: end, to: start };
}

function anchorsToRange(anchors: DraftAnchors): DateRange | undefined {
  const { start, end } = anchors;
  if (!start && !end) return undefined;
  if (start && end) {
    const { from, to } = orderedRange(start, end);
    return { from, to };
  }
  if (start) return { from: start, to: undefined };
  return { from: undefined, to: end };
}

function isSingleDay(anchors: DraftAnchors): boolean {
  const { start, end } = anchors;
  if (!start) return false;
  if (!end) return true;
  return sameDay(start, end);
}

function isoToAnchors(from: string, to: string): DraftAnchors {
  const start = isoToLocalDate(from);
  const end = isoToLocalDate(to);
  if (sameDay(start, end)) return { start };
  return { start, end };
}

export function DateRangeFilterSelect({
  from,
  to,
  onChange,
  className,
  disabled = false,
}: DateRangeFilterSelectProps) {
  const [open, setOpen] = useState(false);
  const [draftAnchors, setDraftAnchors] = useState<DraftAnchors>(() => isoToAnchors(from, to));
  const [currentMonth, setCurrentMonth] = useState(() => isoToLocalDate(to));
  const draftRange = useMemo(() => anchorsToRange(draftAnchors), [draftAnchors]);

  useEffect(() => {
    if (!open) return;
    setDraftAnchors(isoToAnchors(from, to));
    setCurrentMonth(isoToLocalDate(to));
  }, [open, from, to]);

  function applyPreset(days: number) {
    onChange(dateRangeDays(days));
  }

  function applyRange(rangeStart: Date, rangeEnd: Date) {
    const { from, to } = orderedRange(rangeStart, rangeEnd);
    setDraftAnchors({ start: from, end: to });
    onChange(localDatesToIso(from, to));
  }

  function handleDayClick(day: Date) {
    const { start, end } = draftAnchors;

    // 单日范围：再次点击同一天 → 取消选中
    if (isSingleDay(draftAnchors) && start && sameDay(start, day)) {
      setDraftAnchors({});
      return;
    }

    // 多日范围：点击开始/结束端点 → 收缩为当天范围
    if (start && end && !sameDay(start, end)) {
      const { from, to } = orderedRange(start, end);
      if (sameDay(day, from) || sameDay(day, to)) {
        applyRange(day, day);
        return;
      }
      applyRange(from, day);
      return;
    }

    // 无选中 → 当天范围
    if (!start && !end) {
      applyRange(day, day);
      return;
    }

    // 其余：以已有开始日为锚，结束日设为点击日
    applyRange(start ?? day, day);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        <button
          type="button"
          className={cn(
            triggerClassName,
            open && "border-border shadow-none ring-0",
            disabled && "opacity-60",
            className,
          )}
        >
          <CalendarIcon className="text-foreground font-medium size-4 shrink-0" aria-hidden />
          <span className="truncate text-left font-medium text-foreground">{formatDateRangeLabel(from, to)}</span>
          <ChevronDown
            className={cn("size-4 shrink-0 opacity-50", open && "opacity-100")}
            aria-hidden
          />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto min-w-[17.5rem] bg-white p-0">
        <Card className="gap-0 border-0 bg-white py-0 shadow-none">
          <CardContent className="p-0">
            <Calendar
              mode="range"
              locale={zhCN}
              weekStartsOn={1}
              selected={draftRange}
              onSelect={() => undefined}
              onDayClick={handleDayClick}
              month={currentMonth}
              onMonthChange={setCurrentMonth}
              disabled={{ after: new Date() }}
              formatters={{
                formatCaption: (date) => `${date.getFullYear()}年${date.getMonth() + 1}月`,
              }}
              classNames={{
                month: "flex w-full flex-col gap-2",
                week: "mt-1 flex w-full",
              }}
              className="w-full bg-white p-2 [--cell-size:--spacing(9)]"
            />
          </CardContent>
          <CardFooter className="flex flex-col items-center gap-1 border-t">
            {ANALYSIS_DATE_PRESETS.map((preset) => (
              <button
                key={preset.days}
                type="button"
                className="text-primary hover:bg-accent w-full rounded-sm px-2 py-1 text-sm font-semibold transition-colors"
                onClick={() => applyPreset(preset.days)}
              >
                {preset.label}
              </button>
            ))}
          </CardFooter>
        </Card>
      </PopoverContent>
    </Popover>
  );
}
