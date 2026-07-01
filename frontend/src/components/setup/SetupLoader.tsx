import { cn } from "@/lib/utils";

/** 设置向导：加载态（居中圆环 + 提示文案） */
export function SetupLoader() {
  return (
    <div
      className="flex w-full min-h-[min(24rem,calc(100vh-14rem))] flex-col items-center justify-center gap-3"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div
        className={cn(
          "size-10 shrink-0 animate-spin rounded-full border-[3px]",
          "border-background border-t-primary",
        )}
        aria-hidden
      />
      <p className="text-muted-foreground text-sm">大概需要1~2分钟，请耐心等待...</p>
    </div>
  );
}
