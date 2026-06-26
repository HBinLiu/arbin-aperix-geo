import {
  ColumnHelp,
  SentimentMetricCell,
  VisibilityMetricCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { TopicPerformanceSkeletonRows } from "@/components/analysis/prompt/PerformanceTableSkeleton";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import {
  performanceTableClasses,
  TOPIC_TABLE_COLUMNS,
  TOPIC_TABLE_MIN_WIDTH,
} from "@/components/analysis/prompt/performanceTableLayout";
import type { TopicPerformanceRow } from "@/lib/analysis/prompt";
import { cn } from "@/lib/utils";

type TopicPerformanceTableProps = {
  rows: TopicPerformanceRow[];
  selectedTopicId?: string | null;
  onTopicSelect?: (topicId: string | null) => void;
  loading?: boolean;
  className?: string;
};

/** 主题表现汇总表：列宽自适应（百分比），table 始终铺满容器 */
export function TopicPerformanceTable({
  rows,
  selectedTopicId = null,
  onTopicSelect,
  loading = false,
  className,
}: TopicPerformanceTableProps) {
  const selectable = Boolean(onTopicSelect);
  const columnCount = TOPIC_TABLE_COLUMNS.length;

  return (
    <PerformanceTableShell className={className} loading={loading} scrollMinWidth={TOPIC_TABLE_MIN_WIDTH}>
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {TOPIC_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">主题</th>
            <th>
              <span className="inline-flex items-center gap-1">
                可见度
                <ColumnHelp
                  label="可见度"
                  description="在所选时间窗内，至少提及一次自有品牌的 AI 回复占全部成功回复的比例。"
                />
              </span>
            </th>
            <th>
              <span className="inline-flex items-center gap-1">
                情感倾向分数
                <ColumnHelp
                  label="情感倾向分数"
                  description="AI 在提及自有品牌时的平均情感得分，0–100 越高越正向。"
                />
              </span>
            </th>
            <th>平均排名</th>
            <th>
              <span className="inline-flex items-center gap-1">
                引用率
                <ColumnHelp
                  label="引用率"
                  description="在含指向自有域名来源链接的回复中，来源页正文提及品牌的占比。"
                />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <TopicPerformanceSkeletonRows />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columnCount} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无主题表现数据
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const selected = selectable && selectedTopicId === row.id;

              return (
                <tr
                  key={row.id}
                  className={cn(
                    performanceTableClasses.row,
                    selectable && "cursor-pointer",
                    selected && "bg-primary/10 hover:bg-primary/10",
                  )}
                  aria-selected={selected || undefined}
                  onClick={
                    selectable
                      ? () => onTopicSelect?.(selected ? null : row.id)
                      : undefined
                  }
                >
                  <td className="text-foreground pl-5 font-medium">{row.topicName}</td>
                  <td className="font-medium">
                    <VisibilityMetricCell value={row.visibility} delta={row.visibilityDelta} />
                  </td>
                  <td className="font-medium">
                    <SentimentMetricCell
                      value={row.sentiment}
                      label={row.sentimentLabel}
                    />
                  </td>
                  <td className="font-medium">{row.averageRank}</td>
                  <td className="font-medium">{row.citationRate}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
