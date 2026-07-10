import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import type { ComponentPropsWithoutRef, ComponentRef, ReactElement, ReactNode } from "react";
import { forwardRef } from "react";

export const TooltipProvider = TooltipPrimitive.Provider;

export const Tooltip = TooltipPrimitive.Root;

export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = forwardRef<
  ComponentRef<typeof TooltipPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(function TooltipContent({ className = "", side = "top", sideOffset = 6, children, ...props }, ref) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        ref={ref}
        side={side}
        sideOffset={sideOffset}
        className={`pricing-tooltip-content ${className}`.trim()}
        {...props}
      >
        {children}
        <TooltipPrimitive.Arrow className="pricing-tooltip-arrow" width={10} height={5} />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  );
});

type ActionTooltipProps = {
  label: string;
  children: ReactElement;
  className?: string;
};

export function ActionTooltip({ label, children, className = "" }: ActionTooltipProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent className={className}>{label}</TooltipContent>
    </Tooltip>
  );
}

type ActionTooltipProviderProps = {
  children: ReactNode;
};

export function ActionTooltipProvider({ children }: ActionTooltipProviderProps) {
  return (
    <TooltipProvider delayDuration={0} skipDelayDuration={0} disableHoverableContent>
      {children}
    </TooltipProvider>
  );
}
