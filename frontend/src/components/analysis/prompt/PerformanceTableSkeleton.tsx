import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

import {
  performanceTableClasses,
  PROMPT_TABLE_COLUMNS,
  promptTableColumnCellStyle,
  TOPIC_TABLE_COLUMNS,
} from "@/components/analysis/prompt/performanceTableLayout";

type SkeletonRowsProps = {
  count?: number;
};

/** 主题表骨架行：列宽由外层 table colgroup（TOPIC_TABLE_COLUMNS）决定 */
export function TopicPerformanceSkeletonRows({ count = 4 }: SkeletonRowsProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          {TOPIC_TABLE_COLUMNS.map((column, columnIndex) => (
            <td key={column.id} className={cn(columnIndex === 0 && "pl-5")}>
              <Skeleton className="h-4 w-4/5" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/** 提示词表骨架行：列宽由 colgroup + promptTableColumnCellStyle 决定 */
export function PromptPerformanceSkeletonRows({ count = 8 }: SkeletonRowsProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          {PROMPT_TABLE_COLUMNS.map((column, columnIndex) => (
            <td
              key={column.id}
              className={cn(columnIndex === 0 && "max-w-0 overflow-hidden pl-5")}
              style={promptTableColumnCellStyle(column)}
            >
              <Skeleton className={cn("h-4", column.flex ? "w-4/5" : "w-3/5")} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
