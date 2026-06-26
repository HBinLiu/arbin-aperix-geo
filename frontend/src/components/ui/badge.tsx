import * as React from "react"
import { cva } from "class-variance-authority"

import { isNeutralDelta } from "@/lib/analysis/format"
import { cn } from "@/lib/utils"

export type SemanticBadgeVariant = "success" | "error" | "gray" | "primary" | "warning" | "info";

export type DeltaFormat = "percent" | "score" | "sentiment"

const DELTA_THRESHOLDS: Record<DeltaFormat, number> = {
  percent: 0.05,
  score: 0.005,
  sentiment: 0.05,
}

const DELTA_DECIMALS: Record<DeltaFormat, number> = {
  percent: 1,
  score: 2,
  sentiment: 1,
}

const semanticBadgeVariants = cva(
  [
    "inline-flex w-fit shrink-0 items-center justify-center gap-1 whitespace-nowrap",
    "rounded-full border border-transparent px-2 py-0.5 text-xs font-medium",
    "[&>svg]:pointer-events-none [&>svg]:size-3",
  ].join(" "),
  {
    variants: {
      variant: {
        info: "bg-info/12 text-info",
        success: "bg-success/12 text-success",
        error: "bg-error/12 text-error",
        gray: "bg-background text-muted-foreground",
        primary: "bg-primary/12 text-primary",
        warning: "bg-warning/12 text-warning",
      },
    },
    defaultVariants: {
      variant: "gray",
    },
  },
)

const dotVariantClass: Record<SemanticBadgeVariant, string> = {
  success: "bg-success",
  error: "bg-error",
  gray: "bg-muted-foreground",
  primary: "bg-primary",
  warning: "bg-warning",
  info: "bg-info",
}

function semanticVariantFromDelta(delta: number): SemanticBadgeVariant {
  if (delta > 0) return "success"
  if (delta < 0) return "error"
  return "gray"
}

function semanticVariantFromDeltaText(text: string): SemanticBadgeVariant {
  if (isNeutralDelta(text)) return "gray"
  if (text.startsWith("+")) return "success"
  if (text.startsWith("-")) return "error"
  return "gray"
}

export function computeDeltaValue(
  current: number | null | undefined,
  previous: number | null | undefined,
  format: DeltaFormat,
): number | null {
  if (current == null || previous == null) return null
  const raw = current - previous
  return format === "percent" ? raw * 100 : raw
}

function shouldHideDeltaBadge(text: string | null | undefined): boolean {
  if (text == null) return true
  const trimmed = text.trim()
  if (!trimmed) return true
  if (isNeutralDelta(trimmed)) return true
  return false
}

export function formatDeltaValue(delta: number, format: DeltaFormat): string {
  const threshold = DELTA_THRESHOLDS[format]
  const decimals = DELTA_DECIMALS[format]

  if (Math.abs(delta) < threshold) {
    if (format === "percent") return "0%"
    return (0).toFixed(decimals)
  }

  const sign = delta > 0 ? "+" : ""
  if (format === "percent") {
    return `${sign}${delta.toFixed(decimals)}%`
  }
  return `${sign}${delta.toFixed(decimals)}`
}

export type DeltaBadgeProps = {
  className?: string
  format?: DeltaFormat
} & (
  | {
      current: number | null | undefined
      previous: number | null | undefined
      delta?: never
    }
  | {
      delta: string | null | undefined
      current?: never
      previous?: never
      format?: never
    }
)

/** 环比：float 差值格式化为 ±%，正 success / 负 error / 0 灰 */
export function DeltaBadge({
  current,
  previous,
  delta,
  format = "percent",
  className,
}: DeltaBadgeProps) {
  if (delta !== undefined) {
    if (delta == null || shouldHideDeltaBadge(delta)) return null
    return (
      <TextBadge variant={semanticVariantFromDeltaText(delta)} className={cn("tabular-nums", className)}>
        {delta}
      </TextBadge>
    )
  }

  const deltaValue = computeDeltaValue(current, previous, format)
  if (deltaValue == null) return null
  if (Math.abs(deltaValue) < DELTA_THRESHOLDS[format]) return null

  const text = formatDeltaValue(deltaValue, format)
  const variant = semanticVariantFromDelta(deltaValue)

  return (
    <TextBadge variant={variant} className={cn("tabular-nums", className)}>
      {text}
    </TextBadge>
  )
}

/** 固定尺寸的 delta 占位槽，避免有无 badge 时单元格/行高变化 */
export function DeltaBadgeSlot({
  delta,
  className,
}: {
  delta: string | null | undefined
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex h-5 min-w-[2.75rem] shrink-0 items-center justify-start",
        className,
      )}
    >
      <DeltaBadge delta={delta} />
    </span>
  )
}

type DotBadgeProps = {
  variant: SemanticBadgeVariant
  children: React.ReactNode
  className?: string
}

/** 小圆点 + 文案 */
export function DotBadge({ variant, children, className }: DotBadgeProps) {
  return (
    <span
      data-slot="dot-badge"
      className={cn(
        semanticBadgeVariants({ variant }),
        "gap-1.5 font-semibold",
        className,
      )}
    >
      <span
        className={cn("inline-block size-2 shrink-0 rounded-full", dotVariantClass[variant])}
        aria-hidden
      />
      {children}
    </span>
  )
}

type TextBadgeProps = React.ComponentPropsWithoutRef<"span"> & {
  variant: SemanticBadgeVariant
}

export const TextBadge = React.forwardRef<HTMLSpanElement, TextBadgeProps>(
  function TextBadge({ variant, children, className, ...props }, ref) {
    return (
      <span
        ref={ref}
        data-slot="text-badge"
        className={cn(semanticBadgeVariants({ variant }), className)}
        {...props}
      >
        {children}
      </span>
    )
  },
)
TextBadge.displayName = "TextBadge"
