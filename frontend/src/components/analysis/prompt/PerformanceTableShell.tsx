import { cn } from "@/lib/utils";

type PerformanceTableShellProps = {
  children: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
  loading?: boolean;
  /** 表格内容区最小宽度；超出父容器时在内部横向滚动，不撑宽页面 */
  scrollMinWidth?: number;
};

/**
 * 表现表外壳：卡片铺满父级宽度，横向溢出只在内部滚动。
 * minWidth 必须加在内层包裹 div 上，不能直接设在 table 上，否则会撑破 flex 布局。
 */
export function PerformanceTableShell({
  children,
  className,
  footer,
  loading = false,
  scrollMinWidth,
}: PerformanceTableShellProps) {
  return (
    <section
      className={cn(
        "border-border w-full max-w-full min-w-0 overflow-hidden rounded-lg border bg-white",
        className,
      )}
      aria-busy={loading}
    >
      <div className="w-full max-w-full min-w-0 overflow-x-auto">
        <div
          className="w-full"
          style={scrollMinWidth ? { minWidth: scrollMinWidth } : undefined}
        >
          {children}
        </div>
      </div>
      {footer}
    </section>
  );
}
