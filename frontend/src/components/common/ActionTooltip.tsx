import type { ReactElement } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function ActionTooltip({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactElement;
  className?: string;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="top" sideOffset={6} className={cn("text-sm font-semibold", className)}>
        {label}
      </TooltipContent>
    </Tooltip>
  );
}
