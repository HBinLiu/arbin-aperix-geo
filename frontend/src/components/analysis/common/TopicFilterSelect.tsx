import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { ChevronDown, Hash } from "lucide-react";

import { Checkbox } from "@/components/ui/checkbox";
import { analysisFilterTriggerClass, analysisFilterTriggerOpenClass } from "@/components/ui/input";
import type { SubjectTopic } from "@/types";
import { cn } from "@/lib/utils";

type TopicFilterSelectProps = {
  topics: SubjectTopic[];
  value: string[];
  onChange: (topicIds: string[]) => void;
  className?: string;
  disabled?: boolean;
};

function topicFilterLabel(topics: SubjectTopic[], topicIds: string[]): string {
  if (topicIds.length === 0) return "所有主题";
  if (topicIds.length === 1) {
    return topics.find((topic) => topic.id === topicIds[0])?.name ?? "1 个主题";
  }
  return `已选 ${topicIds.length} 个主题`;
}

const triggerClassName = analysisFilterTriggerClass;

const optionClassName =
  "hover:bg-accent hover:text-foreground focus:bg-accent focus:text-foreground relative flex w-full cursor-default select-none items-center justify-start gap-2 rounded-sm py-1.5 pr-2 pl-2 text-left text-sm outline-hidden";

function activateOption(event: KeyboardEvent, action: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    action();
  }
}

export function TopicFilterSelect({
  topics,
  value,
  onChange,
  className,
  disabled = false,
}: TopicFilterSelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selectedSet = useMemo(() => new Set(value), [value]);
  const allSelected = value.length === 0;

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  function toggleTopic(topicId: string, checked: boolean) {
    if (checked) {
      onChange([...value, topicId]);
      return;
    }
    onChange(value.filter((id) => id !== topicId));
  }

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          triggerClassName,
          open && analysisFilterTriggerOpenClass,
          disabled && "opacity-60",
        )}
      >
        <Hash className="text-foreground font-medium size-3.5 shrink-0" aria-hidden />
        <span className="truncate text-left font-medium text-foreground">{topicFilterLabel(topics, value)}</span>
        <ChevronDown
          className={cn("size-4 shrink-0 opacity-50", open && "opacity-100")}
          aria-hidden
        />
      </button>

      {open ? (
        <div
          role="listbox"
          aria-multiselectable
          className="border-border absolute top-full left-0 z-50 mt-1 max-h-72 min-w-[var(--radix-select-trigger-width,12rem)] overflow-y-auto rounded-md border bg-muted-background p-1 text-foreground shadow-md"
        >
          <div
            role="option"
            aria-selected={allSelected}
            tabIndex={0}
            className={optionClassName}
            onClick={() => onChange([])}
            onKeyDown={(event) => activateOption(event, () => onChange([]))}
          >
            <Checkbox checked={allSelected} className="pointer-events-none shrink-0" aria-hidden tabIndex={-1} />
            <span className="min-w-0 flex-1 truncate text-left">所有主题</span>
          </div>

          {topics.map((topic) => {
            const checked = selectedSet.has(topic.id);
            return (
              <div
                key={topic.id}
                role="option"
                aria-selected={checked}
                tabIndex={0}
                className={optionClassName}
                onClick={() => toggleTopic(topic.id, !checked)}
                onKeyDown={(event) =>
                  activateOption(event, () => toggleTopic(topic.id, !checked))
                }
              >
                <Checkbox checked={checked} className="pointer-events-none shrink-0" aria-hidden tabIndex={-1} />
                <span className="min-w-0 flex-1 truncate text-left">{topic.name}</span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
