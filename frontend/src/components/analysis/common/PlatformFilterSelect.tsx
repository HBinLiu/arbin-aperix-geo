import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Bot, ChevronDown } from "lucide-react";

import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Checkbox } from "@/components/ui/checkbox";
import { analysisFilterTriggerClass, analysisFilterTriggerOpenClass } from "@/components/ui/input";
import type { SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type PlatformFilterSelectProps = {
  platforms: SamplingPlatform[];
  value: string[];
  onChange: (platformIds: string[]) => void;
  className?: string;
  disabled?: boolean;
};

const MAX_TRIGGER_ICONS = 4;

function platformFilterLabel(platforms: SamplingPlatform[], platformIds: string[]): string {
  if (platformIds.length === 0) return "所有平台";
  if (platformIds.length === 1) {
    return platforms.find((platform) => platform.platform === platformIds[0])?.label ?? "平台";
  }
  return "平台";
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

function PlatformFilterTriggerIcons({
  platforms,
  platformIds,
}: {
  platforms: SamplingPlatform[];
  platformIds: string[];
}) {
  if (platformIds.length === 0) {
    return <Bot className="text-foreground size-4 shrink-0" aria-hidden />;
  }

  const selected = platformIds
    .map((id) => platforms.find((platform) => platform.platform === id))
    .filter((platform): platform is SamplingPlatform => platform != null);

  if (selected.length === 1) {
    return (
      <PlatformLogo
        provider={selected[0].platform}
        label={selected[0].label}
        className="size-4 shrink-0 rounded-sm"
      />
    );
  }

  const visible = selected.slice(0, MAX_TRIGGER_ICONS);
  const overflow = selected.length - visible.length;

  return (
    <span className="inline-flex shrink-0 items-center gap-1">
      {visible.map((platform) => (
        <PlatformLogo
          key={platform.platform}
          provider={platform.platform}
          label={platform.label}
          className="size-4 shrink-0 rounded-sm"
        />
      ))}
      {overflow > 0 ? (
        <span className="text-muted-foreground text-xs font-medium tabular-nums">
          +{overflow}
        </span>
      ) : null}
    </span>
  );
}

export function PlatformFilterSelect({
  platforms,
  value,
  onChange,
  className,
  disabled = false,
}: PlatformFilterSelectProps) {
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

  function togglePlatform(platformId: string, checked: boolean) {
    if (checked) {
      onChange([...value, platformId]);
      return;
    }
    onChange(value.filter((id) => id !== platformId));
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
        <PlatformFilterTriggerIcons platforms={platforms} platformIds={value} />
        <span className="truncate text-left font-medium text-foreground">
          {platformFilterLabel(platforms, value)}
        </span>
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
            <span className="min-w-0 flex-1 truncate text-left">所有平台</span>
          </div>

          {platforms.map((platform) => {
            const checked = selectedSet.has(platform.platform);
            return (
              <div
                key={platform.platform}
                role="option"
                aria-selected={checked}
                tabIndex={0}
                className={optionClassName}
                onClick={() => togglePlatform(platform.platform, !checked)}
                onKeyDown={(event) =>
                  activateOption(event, () => togglePlatform(platform.platform, !checked))
                }
              >
                <Checkbox checked={checked} className="pointer-events-none shrink-0" aria-hidden tabIndex={-1} />
                <PlatformLogo
                  provider={platform.platform}
                  label={platform.label}
                  className="size-5 shrink-0 rounded-sm"
                />
                <span className="min-w-0 flex-1 truncate text-left">{platform.label}</span>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
