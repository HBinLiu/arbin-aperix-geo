import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";

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

const NON_CLEARABLE_TYPES = new Set([
  "file",
  "hidden",
  "checkbox",
  "radio",
  "range",
  "color",
  "submit",
  "button",
  "reset",
  "image",
]);

export type InputProps = Omit<React.ComponentProps<"input">, "size"> &
  VariantProps<typeof inputVariants> & {
    /** 有内容时显示圆角清除按钮。默认：普通文本开，merged / 特殊 type 关。 */
    clearable?: boolean;
  };

function shouldEnableClearable(
  clearable: boolean | undefined,
  type: string,
  variant: InputProps["variant"],
): boolean {
  if (clearable != null) return clearable;
  if (variant === "merged") return false;
  return !NON_CLEARABLE_TYPES.has(type);
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      variant,
      controlSize,
      type = "text",
      clearable,
      value,
      defaultValue,
      onChange,
      disabled,
      readOnly,
      ...props
    },
    ref,
  ) => {
    const enableClearable = shouldEnableClearable(clearable, type, variant);
    const isControlled = value !== undefined;
    const [uncontrolled, setUncontrolled] = React.useState(() => String(defaultValue ?? ""));
    const currentValue = isControlled ? String(value ?? "") : uncontrolled;
    const showClear = enableClearable && !disabled && !readOnly && currentValue.length > 0;

    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      if (!isControlled) setUncontrolled(event.target.value);
      onChange?.(event);
    };

    const handleClear = () => {
      if (disabled || readOnly) return;
      if (!isControlled) setUncontrolled("");
      onChange?.({
        target: { value: "" },
        currentTarget: { value: "" },
      } as React.ChangeEvent<HTMLInputElement>);
    };

    if (!enableClearable) {
      return (
        <input
          type={type}
          className={cn(inputVariants({ variant, controlSize }), className)}
          ref={ref}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          disabled={disabled}
          readOnly={readOnly}
          {...props}
        />
      );
    }

    return (
      <div className="relative z-0 w-full min-w-0">
        <input
          type={type}
          className={cn(inputVariants({ variant, controlSize }), className, showClear && "pr-9")}
          ref={ref}
          disabled={disabled}
          readOnly={readOnly}
          {...props}
          {...(isControlled
            ? { value, onChange: handleChange }
            : { value: uncontrolled, onChange: handleChange })}
        />
        {showClear ? (
          <span
            className={cn(
              "absolute inset-y-0 right-2.5 z-10 flex items-center",
              controlSize === "sm" && "right-2",
            )}
          >
            <button
              type="button"
              tabIndex={-1}
              onClick={handleClear}
              className="text-muted-foreground hover:text-foreground border-border flex size-5 items-center justify-center rounded-full border"
              aria-label="清除"
            >
              <X className="size-3" strokeWidth={2.5} aria-hidden />
            </button>
          </span>
        ) : null}
      </div>
    );
  },
);
Input.displayName = "Input";

/** 合并双列输入外框（竞品 / 提示词表格行） */
function InputGroup({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn(inputGroupShellClass, className)} {...props} />;
}

export { Input, InputGroup };
