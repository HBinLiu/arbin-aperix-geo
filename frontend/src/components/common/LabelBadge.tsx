import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

export type LabelBadgeVariant = "primary" | "green" | "red" | "orange" | "muted";

const VARIANT_STYLES: Record<LabelBadgeVariant, string> = {
  primary: "bg-primary/10 text-primary",
  green: "bg-emerald-50 text-emerald-600",
  red: "bg-red-50 text-red-600",
  orange: "bg-orange-50 text-orange-600",
  muted: "bg-muted text-muted-foreground",
};

type LabelBadgeProps = {
  children: React.ReactNode;
  variant?: LabelBadgeVariant;
  className?: string;
} & ComponentPropsWithoutRef<"span">;

/** 小号标签，用于排名「拥有」、状态提示等。 */
export function LabelBadge({
  children,
  variant = "primary",
  className,
  ...props
}: LabelBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium",
        VARIANT_STYLES[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
