import { FileText, Globe, Loader2 } from "lucide-react";

import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatKnowledgeDateTime,
  knowledgeIndexStatusLabel,
  knowledgeNeedsReindex,
  knowledgeStatusLabel,
} from "@/lib/knowledge/display";
import type { SubjectKnowledge } from "@/types";

type KnowledgeStatusBarProps = {
  knowledge: SubjectKnowledge;
  chunkCount: number;
};

export function KnowledgeStatusBar({ knowledge, chunkCount }: KnowledgeStatusBarProps) {
  const needsReindex = knowledgeNeedsReindex(knowledge);
  const indexing = knowledge.index_status === "indexing";
  const failed = knowledge.index_status === "failed";

  return (
    <div className="border-border rounded-lg border bg-muted-background p-4">
      <div className="flex flex-wrap items-center gap-2">
        <TextBadge variant={knowledge.status === "verified" ? "success" : "warning"}>
          {knowledgeStatusLabel(knowledge.status)}
        </TextBadge>
        <TextBadge variant="gray">v{knowledge.version}</TextBadge>
        <TextBadge variant={failed ? "error" : indexing ? "info" : needsReindex ? "warning" : "success"}>
          {indexing ? (
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="size-3 animate-spin" aria-hidden />
              {knowledgeIndexStatusLabel(knowledge.index_status)}
            </span>
          ) : (
            knowledgeIndexStatusLabel(knowledge.index_status)
          )}
        </TextBadge>
        <span className="text-muted-foreground text-xs">
          已索引 {chunkCount} 块 · 更新于 {formatKnowledgeDateTime(knowledge.updated_at)}
        </span>
      </div>
      {needsReindex && !indexing ? (
        <p className="text-warning mt-2 text-xs">内容已变更，尚未完成重新索引。</p>
      ) : null}
      {failed && knowledge.index_error ? (
        <p className="text-destructive mt-2 text-xs">{knowledge.index_error}</p>
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
