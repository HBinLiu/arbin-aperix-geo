import { TableFetchOverlay } from "@/components/analysis/common/TableFetchOverlay";
import { cn } from "@/lib/utils";

type TableScrollOverlayProps = {
  children: React.ReactNode;
  fetching?: boolean;
  className?: string;
};

/** 表格横向滚动容器，fetching 时在内容区显示半透明 loading 遮罩 */
export function TableScrollOverlay({
  children,
  fetching = false,
  className,
}: TableScrollOverlayProps) {
  return (
    <div className={cn("relative overflow-x-auto", className)}>
      {children}
      {fetching ? <TableFetchOverlay /> : null}
    </div>
  );
}
