import { useEffect, useMemo, useState } from "react";
import { Loader2, Network, RefreshCw } from "lucide-react";

import { KnowledgeForceGraph } from "@/components/knowledge/graph/KnowledgeForceGraph";
import { KnowledgeGraphToolbar } from "@/components/knowledge/graph/KnowledgeGraphToolbar";
import { Button } from "@/components/ui/button";
import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { knowledgeExtractStatusLabel } from "@/lib/knowledge/display";
import { KNOWLEDGE_GRAPH_NODE_TYPES } from "@/lib/knowledge/graphStyle";
import {
  countNodesByType,
  filterGraphViewData,
  matchNodeIds,
  neighborIdsForNode,
  toGraphViewData,
} from "@/lib/knowledge/graphView";
import { cn } from "@/lib/utils";
import type { KnowledgeGraph, SubjectKnowledge } from "@/types";

type KnowledgeGraphSectionProps = {
  loading?: boolean;
  knowledge: SubjectKnowledge | null;
  graph: KnowledgeGraph | null | undefined;
  extracting?: boolean;
  onRetryExtract?: () => void;
  className?: string;
};

const DEFAULT_ENABLED = new Set<string>(KNOWLEDGE_GRAPH_NODE_TYPES);

export function KnowledgeGraphSection({
  loading,
  knowledge,
  graph,
  extracting,
  onRetryExtract,
  className,
}: KnowledgeGraphSectionProps) {
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(() => new Set(DEFAULT_ENABLED));
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const baseView = useMemo(() => toGraphViewData(graph), [graph]);
  const filteredView = useMemo(
    () => filterGraphViewData(baseView, { enabledTypes }),
    [baseView, enabledTypes],
  );
  const countsByType = useMemo(() => countNodesByType(baseView.nodes), [baseView.nodes]);
  const searchMatchIds = useMemo(
    () => matchNodeIds(filteredView.nodes, search),
    [filteredView.nodes, search],
  );
  const activeId = hoveredId || selectedId;
  const highlightIds = useMemo(
    () => neighborIdsForNode(filteredView, activeId),
    [filteredView, activeId],
  );

  useEffect(() => {
    if (selectedId && !filteredView.nodes.some((node) => node.id === selectedId)) {
      setSelectedId(null);
    }
  }, [filteredView.nodes, selectedId]);

  if (loading) {
    return (
      <div
        className={cn(
          "border-border flex h-full min-h-[320px] flex-col rounded-lg border bg-muted-background p-4",
          className,
        )}
      >
        <Skeleton className="mb-3 h-5 w-28 shrink-0" />
        <Skeleton className="min-h-0 w-full flex-1 rounded-md" />
      </div>
    );
  }

  if (!knowledge) return null;

  const extractStatus = graph?.extract_status ?? knowledge.extract_status ?? "pending";
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const pending = extractStatus === "pending" || extracting;
  const failed = extractStatus === "failed";

  function toggleType(type: string) {
    if (type === "brand") return;
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  return (
    <section
      className={cn(
        "border-border flex h-full min-h-0 flex-col rounded-lg border bg-muted-background p-4",
        className,
      )}
    >
      <div className="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Network className="text-muted-foreground size-4" aria-hidden />
          <h2 className="text-foreground text-sm font-medium">知识图谱</h2>
          <TextBadge variant={failed ? "error" : pending ? "info" : "success"}>
            {pending ? (
              <span className="inline-flex items-center gap-1.5">
                <Loader2 className="size-3 animate-spin" aria-hidden />
                {knowledgeExtractStatusLabel(extractStatus)}
              </span>
            ) : (
              knowledgeExtractStatusLabel(extractStatus)
            )}
          </TextBadge>
          {nodes.length > 0 ? (
            <span className="text-muted-foreground text-xs">
              {baseView.nodes.length} 实体 · {baseView.links.length} 关系
            </span>
          ) : null}
        </div>
        {failed && onRetryExtract ? (
          <Button type="button" variant="outline" size="sm" onClick={onRetryExtract} disabled={extracting}>
            <RefreshCw className="size-3.5" aria-hidden />
            重新抽取
          </Button>
        ) : null}
      </div>

      {failed && (graph?.extract_error || knowledge.extract_error) ? (
        <p className="text-destructive mb-3 shrink-0 text-xs">{graph?.extract_error || knowledge.extract_error}</p>
      ) : null}

      {pending && nodes.length === 0 ? (
        <p className="text-muted-foreground text-sm">正在从资料中识别实体与关系…</p>
      ) : null}

      {!pending && nodes.length === 0 ? (
        <p className="text-muted-foreground text-sm">暂无图谱。上传或补充品牌资料后将自动抽取。</p>
      ) : null}

      {nodes.length > 0 ? (
        <div className="flex min-h-0 flex-1 flex-col gap-3">
          <div className="shrink-0">
            <KnowledgeGraphToolbar
              countsByType={countsByType}
              enabledTypes={enabledTypes}
              search={search}
              onSearchChange={setSearch}
              onToggleType={toggleType}
            />
          </div>
          <div className="min-h-0 flex-1">
            <KnowledgeForceGraph
              data={filteredView}
              selectedId={selectedId}
              hoveredId={hoveredId}
              highlightIds={highlightIds}
              searchMatchIds={searchMatchIds}
              onHover={setHoveredId}
              onSelect={setSelectedId}
            />
          </div>
          {edges.length > 0 && filteredView.links.length === 0 ? (
            <p className="text-muted-foreground shrink-0 text-xs">当前类型筛选下没有可见关系。</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
