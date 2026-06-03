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
          "border-muted border-t-primary",
        )}
        aria-hidden
      />
      <p className="text-muted-foreground text-sm">这可能需要一些时间...</p>
    </div>
  );
}
