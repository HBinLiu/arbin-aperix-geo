import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const inputElevationShadowClass = "shadow-[var(--input-elevation-shadow)]";

const inputFieldGlowClass = cn(
  inputElevationShadowClass,
  "focus-visible:border-primary focus-visible:shadow-none focus-visible:ring-[3px] focus-visible:ring-primary/30",
);

const inputGroupGlowClass = cn(
  inputElevationShadowClass,
  "focus-within:border-primary focus-within:shadow-none focus-within:ring-[3px] focus-within:ring-primary/30",
);

const inputGroupShellClass = cn(
  "border-input bg-muted-background min-w-0 overflow-hidden rounded-md border",
  "transition-[color,box-shadow,border-color]",
  inputGroupGlowClass,
);

/** 与 Input / SelectTrigger 外框一致（仅 ui/select 引用） */
export const inputControlClass = cn(
  "border-input bg-muted-background w-full min-w-0 rounded-md border text-sm md:text-sm",
  "placeholder:text-muted-foreground",
  "transition-[color,box-shadow,border-color] outline-hidden",
  inputFieldGlowClass,
  "disabled:cursor-not-allowed disabled:opacity-50",
);

/** 分析页 FilterBar 自定义触发器（平台 / 主题 / 日期等） */
export const analysisFilterTriggerClass = cn(
  "border-border inline-flex h-9 w-auto items-center gap-2 rounded-lg border bg-muted-background px-3 text-sm font-normal",
  "transition-[color,box-shadow,border-color] outline-hidden",
  inputElevationShadowClass,
  "focus:border-primary focus:shadow-none focus:ring-[3px] focus:ring-primary/30",
  "focus-visible:border-primary focus-visible:shadow-none focus-visible:ring-[3px] focus-visible:ring-primary/30",
);

export const analysisFilterTriggerOpenClass =
  "border-primary shadow-none ring-[3px] ring-primary/30";

const inputVariants = cva(
  cn(inputControlClass, "mx-0.5 flex file:border-0 file:bg-transparent file:text-sm file:font-medium"),
  {
    variants: {
      variant: {
        default: "",
        merged:
          "mx-0 border-0 bg-muted-background focus-visible:border-transparent focus-visible:shadow-none focus-visible:ring-0",
      },
      controlSize: {
        default: "h-10 px-3 py-2",
        sm: "h-9 px-3 py-1",
      },
    },
    defaultVariants: {
      variant: "default",
      controlSize: "default",
    },
  },
);

export type InputProps = Omit<React.ComponentProps<"input">, "size"> &
  VariantProps<typeof inputVariants>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, controlSize, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(inputVariants({ variant, controlSize }), className)}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";

/** 合并双列输入外框（竞品 / 提示词表格行） */
function InputGroup({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn(inputGroupShellClass, className)} {...props} />;
}

export { Input, InputGroup };
