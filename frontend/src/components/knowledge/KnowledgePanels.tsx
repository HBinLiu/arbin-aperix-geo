import { FileText, Globe, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatKnowledgeDateTime,
  knowledgeIndexDisplayLabel,
  knowledgeNeedsReindex,
} from "@/lib/knowledge/display";
import type { SubjectKnowledge } from "@/types";

type KnowledgeStatusProps = {
  knowledge: SubjectKnowledge;
  chunkCount: number;
  reindexing?: boolean;
  onReindex?: () => void;
};

/** 卡片标题旁的状态徽章。 */
export function KnowledgeStatusBadges({ knowledge }: { knowledge: SubjectKnowledge }) {
  const needsReindex = knowledgeNeedsReindex(knowledge);
  const indexing = knowledge.index_status === "indexing";
  const pendingIndex = knowledge.index_status === "pending" || needsReindex;
  const failed = knowledge.index_status === "failed";

  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <TextBadge variant={failed ? "error" : indexing || pendingIndex ? "info" : "success"}>
        {indexing || (pendingIndex && knowledge.index_status === "pending") ? (
          <span className="inline-flex items-center gap-1.5">
            <Loader2 className="size-3 animate-spin" aria-hidden />
            {knowledgeIndexDisplayLabel(knowledge)}
          </span>
        ) : (
          knowledgeIndexDisplayLabel(knowledge)
        )}
      </TextBadge>
      <TextBadge variant="gray">v{knowledge.version}</TextBadge>
    </span>
  );
}

export function KnowledgeStatusBadgesSkeleton() {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <Skeleton className="h-5 w-16 rounded-full" />
      <Skeleton className="h-5 w-8 rounded-full" />
    </span>
  );
}

/** 卡片标题区副文案：索引摘要与告警。 */
export function KnowledgeStatusDescription({
  knowledge,
  chunkCount,
}: {
  knowledge: SubjectKnowledge;
  chunkCount: number;
}) {
  const needsReindex = knowledgeNeedsReindex(knowledge);
  const indexing = knowledge.index_status === "indexing";
  const failed = knowledge.index_status === "failed";

  return (
    <div className="space-y-1.5">
      <p>
        当前版本已索引 {chunkCount} 块
        {" · "}
        更新于 {formatKnowledgeDateTime(knowledge.updated_at)}
      </p>
      {needsReindex && !indexing ? (
        <p className="text-warning text-xs">
          内容已变更（v{knowledge.version}），当前索引停在 v{knowledge.indexed_version}
          。可点击「重新索引」修复。
        </p>
      ) : null}
      {failed && knowledge.index_error ? (
        <p className="text-destructive text-xs">{knowledge.index_error}</p>
      ) : null}
    </div>
  );
}

/** 需要时展示在卡片操作区的「重新索引」按钮。 */
export function KnowledgeReindexButton({
  knowledge,
  reindexing,
  onReindex,
}: Pick<KnowledgeStatusProps, "knowledge" | "reindexing" | "onReindex">) {
  if (!onReindex) return null;
  const needsReindex = knowledgeNeedsReindex(knowledge);
  const indexing = knowledge.index_status === "indexing";
  const failed = knowledge.index_status === "failed";
  if ((!needsReindex && !failed) || indexing) return null;

  return (
    <Button type="button" variant="outline" size="sm" onClick={onReindex} disabled={reindexing}>
      <RefreshCw className="size-3.5" aria-hidden />
      重新索引
    </Button>
  );
}

export function KnowledgeSourceKindIcon({ kind }: { kind: string }) {
  if (kind === "homepage") return <Globe className="text-muted-foreground size-4 shrink-0" aria-hidden />;
  if (kind === "upload") return <FileText className="text-muted-foreground size-4 shrink-0" aria-hidden />;
  return <FileText className="text-muted-foreground size-4 shrink-0" aria-hidden />;
}
