import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Input, type InputProps } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const setupControlOpen =
  "data-[state=open]:border-primary data-[state=open]:ring-[3px] data-[state=open]:ring-primary/30";

/** 为 Select 的 focus ring / 阴影预留垂直空间；水平由 Input 默认 mx-0.5 负责 */
export const setupControlShellClass = "relative w-full min-w-0 overflow-visible p-0.5";

/** 提示词阶段：与 InputGroup 对齐，不额外 padding */
export const setupPromptControlShellClass = "relative w-full min-w-0 overflow-visible";

type SetupControlShell = "setup" | "prompt";

function setupControlShell(shell: SetupControlShell): string {
  return shell === "prompt" ? setupPromptControlShellClass : setupControlShellClass;
}

export function SetupFieldGroup({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("ml-0.5 space-y-2 overflow-visible", className)}>{children}</div>;
}

export function SetupFieldLabel({
  icon: Icon,
  htmlFor,
  children,
}: {
  icon: LucideIcon;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="text-foreground flex items-center gap-2 text-sm font-medium px-1"
    >
      <Icon className="text-muted-foreground h-[18px] w-[18px] shrink-0" aria-hidden />
      {children}
    </label>
  );
}

type SetupTextInputProps = Omit<InputProps, "className"> & {
  leading?: ReactNode;
  /** setup：默认带 p-0.5；prompt：提示词阶段无 padding */
  shell?: SetupControlShell;
};

/** 网站 URL / 品牌名等单行输入（h-9、左侧图标，对齐竞品） */
export function SetupTextInput({
  leading,
  shell = "setup",
  className,
  containerClassName,
  ...props
}: SetupTextInputProps & { className?: string; containerClassName?: string }) {
  return (
    <div className={cn(setupControlShell(shell), containerClassName)}>
      {leading ? (
        <div className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">{leading}</div>
      ) : null}
      <Input
        controlSize="sm"
        className={cn(leading && "pl-9", className)}
        {...props}
      />
    </div>
  );
}

type SetupSelectProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string; flag?: string }[];
  /** setup：默认带 p-0.5；prompt：提示词阶段无 padding */
  shell?: SetupControlShell;
};

/** 目标地区 / 语言下拉（shadcn/ui Select） */
export function SetupSelect({ id, value, onChange, options, shell = "setup" }: SetupSelectProps) {
  const selected = options.find((o) => o.value === value);

  return (
    <div className={setupControlShell(shell)}>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger
          id={id}
          aria-label={selected?.label}
          className={cn(setupControlOpen, "h-9 pl-2 pr-3 py-1")}
        >
          <SelectValue placeholder="请选择">
            {selected ? (
              <span className="flex items-center gap-1.5">
                {selected.flag ? <span className="text-base leading-none">{selected.flag}</span> : null}
                <span className="truncate">{selected.label}</span>
              </span>
            ) : null}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              <span className="flex items-center gap-1.5">
                {o.flag ? <span className="text-base leading-none">{o.flag}</span> : null}
                <span>{o.label}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
