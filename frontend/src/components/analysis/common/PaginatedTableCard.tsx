import { TableScrollOverlay } from "@/components/analysis/common/TableScrollOverlay";
import { cn } from "@/lib/utils";

type PaginatedTableCardProps = {
  children: React.ReactNode;
  loading?: boolean;
  fetching?: boolean;
  footer?: React.ReactNode;
  className?: string;
};

/** 分页表格卡片：边框 + 内容区 loading 遮罩 + 可选底部分页 */
export function PaginatedTableCard({
  children,
  loading = false,
  fetching = false,
  footer,
  className,
}: PaginatedTableCardProps) {
  return (
    <div
      className={cn("border-border overflow-hidden rounded-lg border bg-muted-background", className)}
      aria-busy={loading || fetching}
    >
      <TableScrollOverlay fetching={fetching}>{children}</TableScrollOverlay>
      {footer}
    </div>
  );
}
