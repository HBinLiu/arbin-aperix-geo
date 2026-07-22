import { FileText, Globe, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatKnowledgeDateTime,
  knowledgeExtractStatusLabel,
  knowledgeIndexDisplayLabel,
  knowledgeNeedsReindex,
  knowledgeStatusLabel,
} from "@/lib/knowledge/display";
import type { SubjectKnowledge } from "@/types";

type KnowledgeStatusBarProps = {
  knowledge: SubjectKnowledge;
  chunkCount: number;
  reindexing?: boolean;
  onReindex?: () => void;
};

export function KnowledgeStatusBar({
  knowledge,
  chunkCount,
  reindexing,
  onReindex,
}: KnowledgeStatusBarProps) {
  const needsReindex = knowledgeNeedsReindex(knowledge);
  const indexing = knowledge.index_status === "indexing";
  const pendingIndex = knowledge.index_status === "pending" || needsReindex;
  const failed = knowledge.index_status === "failed";
  const extractStatus = knowledge.extract_status ?? "pending";
  const extracting = extractStatus === "pending";
  const extractFailed = extractStatus === "failed";
  const showReindex = Boolean(onReindex) && (needsReindex || failed) && !indexing;

  return (
    <div className="border-border rounded-lg border bg-muted-background p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <TextBadge variant={knowledge.status === "verified" ? "success" : "warning"}>
            {knowledgeStatusLabel(knowledge.status)}
          </TextBadge>
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
          <TextBadge variant={extractFailed ? "error" : extracting ? "info" : "success"}>
            {extracting ? (
              <span className="inline-flex items-center gap-1.5">
                <Loader2 className="size-3 animate-spin" aria-hidden />
                {knowledgeExtractStatusLabel(extractStatus)}
              </span>
            ) : (
              knowledgeExtractStatusLabel(extractStatus)
            )}
          </TextBadge>
          <TextBadge variant="gray">v{knowledge.version}</TextBadge>
          <span className="text-muted-foreground text-xs">
            当前版本已索引 {chunkCount} 块
            {typeof knowledge.node_count === "number" ? ` · ${knowledge.node_count} 实体` : ""}
            {" · "}
            更新于 {formatKnowledgeDateTime(knowledge.updated_at)}
          </span>
        </div>
        {showReindex ? (
          <Button type="button" variant="outline" size="sm" onClick={onReindex} disabled={reindexing}>
            <RefreshCw className="size-3.5" aria-hidden />
            重新索引
          </Button>
        ) : null}
      </div>
      {needsReindex && !indexing ? (
        <p className="text-warning mt-2 text-xs">
          内容已变更（v{knowledge.version}），当前索引停在 v{knowledge.indexed_version}
          。可点击「重新索引」修复。
        </p>
      ) : null}
      {failed && knowledge.index_error ? (
        <p className="text-destructive mt-2 text-xs">{knowledge.index_error}</p>
      ) : null}
      {extractFailed && knowledge.extract_error ? (
        <p className="text-destructive mt-2 text-xs">{knowledge.extract_error}</p>
      ) : null}
    </div>
  );
}

export function KnowledgeStatusBarSkeleton() {
  return (
    <div className="border-border rounded-lg border bg-muted-background p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Skeleton className="h-5 w-14 rounded-full" />
        <Skeleton className="h-5 w-8 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-4 w-52" />
      </div>
    </div>
  );
}

export function KnowledgeSourceKindIcon({ kind }: { kind: string }) {
  if (kind === "homepage") return <Globe className="text-muted-foreground size-4 shrink-0" aria-hidden />;
  if (kind === "upload") return <FileText className="text-muted-foreground size-4 shrink-0" aria-hidden />;
  return <FileText className="text-muted-foreground size-4 shrink-0" aria-hidden />;
}
