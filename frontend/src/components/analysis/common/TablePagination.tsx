import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export const DEFAULT_TABLE_PAGE_SIZE = 10;

export const TABLE_PAGE_SIZE_OPTIONS = [10, 30, 50] as const;

type TablePaginationProps = {
  total: number;
  page: number;
  pageSize?: number;
  pageSizeOptions?: readonly number[];
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  className?: string;
};

function getPageItems(current: number, totalPages: number): (number | "ellipsis")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items: (number | "ellipsis")[] = [1];

  if (current > 3) items.push("ellipsis");

  const start = Math.max(2, current - 1);
  const end = Math.min(totalPages - 1, current + 1);
  for (let page = start; page <= end; page += 1) {
    items.push(page);
  }

  if (current < totalPages - 2) items.push("ellipsis");

  items.push(totalPages);
  return items;
}

/** 表格底部分页（基于 shadcn Pagination） */
export function TablePagination({
  total,
  page,
  pageSize = DEFAULT_TABLE_PAGE_SIZE,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
  className,
}: TablePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const pageItems = getPageItems(safePage, totalPages);

  if (total === 0) return null;

  const rangeStart = (safePage - 1) * pageSize + 1;
  const rangeEnd = Math.min(safePage * pageSize, total);
  const showPageNav = totalPages > 1;

  return (
    <div
      className={cn(
        "border-border flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-muted-foreground text-sm tabular-nums">
          第 {rangeStart}–{rangeEnd} 条，共 {total} 条
        </p>

        {onPageSizeChange && pageSizeOptions && pageSizeOptions.length > 0 ? (
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-sm">每页</span>
            <Select
              value={String(pageSize)}
              onValueChange={(value) => onPageSizeChange(Number(value))}
            >
              <SelectTrigger
                className="border-border h-8 w-[4.5rem] rounded-lg bg-white px-2 text-xs shadow-none"
                aria-label="每页条数"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {pageSizeOptions.map((option) => (
                  <SelectItem key={option} value={String(option)}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-muted-foreground text-sm">条</span>
          </div>
        ) : null}
      </div>

      {showPageNav ? (
        <Pagination className="mx-0 w-auto justify-end">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                disabled={safePage <= 1}
                onClick={() => onPageChange(safePage - 1)}
              />
            </PaginationItem>

            {pageItems.map((item, index) =>
              item === "ellipsis" ? (
                <PaginationItem key={`ellipsis-${index}`}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={item}>
                  <PaginationLink
                    isActive={item === safePage}
                    onClick={() => onPageChange(item)}
                  >
                    {item}
                  </PaginationLink>
                </PaginationItem>
              ),
            )}

            <PaginationItem>
              <PaginationNext
                disabled={safePage >= totalPages}
                onClick={() => onPageChange(safePage + 1)}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const start = (safePage - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}
