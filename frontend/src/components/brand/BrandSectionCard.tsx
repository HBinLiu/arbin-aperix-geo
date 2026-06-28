import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type BrandSectionCardProps = {
  title: string;
  description: string;
  actionLabel?: string;
  actionIcon?: ReactNode;
  actionVariant?: "default" | "outline";
  actionDisabled?: boolean;
  onAction?: () => void;
  headerActions?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
};

/** 品牌页配置区块卡片（平台 / 提示词 / 竞品等）。 */
export function BrandSectionCard({
  title,
  description,
  actionLabel,
  actionIcon,
  actionVariant = "outline",
  actionDisabled = false,
  onAction,
  headerActions,
  footer,
  children,
  className,
}: BrandSectionCardProps) {
  const hasContent = Boolean(children);
  const hasFooter = Boolean(footer);
  const hasBody = hasContent || hasFooter;

  return (
    <section
      className={cn(
        "border-border w-full max-w-5xl rounded-lg border bg-muted-background shadow-xs",
        hasBody && "p-5 sm:p-6",
        className,
      )}
    >
      <div
        className={cn(
          "border-border bg-background/50 flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5 sm:py-3.5",
          hasBody
            ? "-mx-5 -mt-5 rounded-t-lg border-b sm:-mx-6 sm:-mt-6"
            : "rounded-lg",
        )}
      >
        <div className="min-w-0">
          <h3 className="text-base font-semibold tracking-tight">{title}</h3>
          <p className="text-muted-foreground mt-1 text-sm leading-relaxed">{description}</p>
        </div>
        {headerActions ? (
          <div className="flex shrink-0 items-center gap-2">{headerActions}</div>
        ) : actionLabel && onAction ? (
          <Button
            type="button"
            variant={actionVariant}
            className="shrink-0 gap-1.5"
            disabled={actionDisabled}
            onClick={onAction}
          >
            {actionIcon}
            {actionLabel}
          </Button>
        ) : null}
      </div>

      {hasContent ? <div className="pt-5">{children}</div> : null}

      {hasFooter ? (
        <p className={cn("text-muted-foreground text-xs", hasContent ? "mt-3" : "pt-5")}>{footer}</p>
      ) : null}
    </section>
  );
}
