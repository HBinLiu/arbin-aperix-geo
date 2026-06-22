import type { ReactNode } from "react";

import { platformAccent, platformLogoSrc } from "@/lib/brand";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type PlatformLogoProps = {
  provider: string;
  label: string;
  className?: string;
};

export function PlatformLogo({ provider, label, className }: PlatformLogoProps) {
  const src = platformLogoSrc(provider);

  if (src) {
    return (
      <img
        src={src}
        alt={label}
        className={cn("size-8 shrink-0 rounded-md object-contain", className)}
      />
    );
  }

  return (
    <span
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-md border text-xs font-bold",
        platformAccent(provider),
        className,
      )}
    >
      {label.slice(0, 1)}
    </span>
  );
}

const DEFAULT_MAX_VISIBLE = 4;

type PlatformLogoGroupProps = {
  providers: string[];
  platforms?: SamplingPlatform[];
  maxVisible?: number;
  className?: string;
  logoClassName?: string;
  showTooltip?: boolean;
};

/** 多平台 logo 叠放；空列表显示 —，超出 maxVisible 显示 +N */
export function PlatformLogoGroup({
  providers,
  platforms = [],
  maxVisible = DEFAULT_MAX_VISIBLE,
  className,
  logoClassName,
  showTooltip = true,
}: PlatformLogoGroupProps) {
  let content: ReactNode;

  if (providers.length === 0) {
    content = "-";
  } else {
    const resolved = providers.map((provider) => resolvePlatformMeta(provider, platforms));
    const visible = resolved.slice(0, maxVisible);
    const overflow = resolved.length - visible.length;

    const icons = (
      <div className={cn("flex items-center -space-x-1", className)}>
        {visible.map((meta) => (
          <PlatformLogo
            key={meta.platform}
            provider={meta.platform}
            label={meta.label}
            className={logoClassName}
          />
        ))}
        {overflow > 0 ? (
          <span className="text-muted-foreground pl-2 text-xs font-medium tabular-nums">
            +{overflow}
          </span>
        ) : null}
      </div>
    );

    content = !showTooltip ? (
      icons
    ) : (
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className="inline-flex cursor-default items-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            tabIndex={0}
            role="img"
            aria-label={`${resolved.length} 个平台`}
            onClick={(event) => event.stopPropagation()}
          >
            {icons}
          </span>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          sideOffset={8}
          showArrow={false}
          className="border-border w-auto min-w-48 border bg-white px-3 py-2.5 text-foreground shadow-lg"
        >
          <ul className="flex flex-col gap-2">
            {resolved.map((meta) => (
              <li key={meta.platform} className="flex items-center gap-2">
                <PlatformLogo provider={meta.platform} label={meta.label} className="size-4" />
                <span className="text-sm font-normal">{meta.label}</span>
              </li>
            ))}
          </ul>
        </TooltipContent>
      </Tooltip>
    );
  }

  return <div className="flex items-center">{content}</div>;
}
