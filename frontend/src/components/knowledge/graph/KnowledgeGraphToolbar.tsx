import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { knowledgeNodeTypeLabel } from "@/lib/knowledge/display";
import { KNOWLEDGE_GRAPH_NODE_TYPES, knowledgeGraphNodeStyle } from "@/lib/knowledge/graphStyle";

type KnowledgeGraphToolbarProps = {
  countsByType: Record<string, number>;
  enabledTypes: ReadonlySet<string>;
  search: string;
  onSearchChange: (value: string) => void;
  onToggleType: (type: string) => void;
};

export function KnowledgeGraphToolbar({
  countsByType,
  enabledTypes,
  search,
  onSearchChange,
  onToggleType,
}: KnowledgeGraphToolbarProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {KNOWLEDGE_GRAPH_NODE_TYPES.map((type) => {
            const pinned = type === "brand";
            const count = countsByType[type] ?? 0;
            const on = count > 0 && (pinned || enabledTypes.has(type));
            const color = knowledgeGraphNodeStyle(type).color;
            return (
              <button
                key={type}
                type="button"
                disabled={pinned || count === 0}
                onClick={() => onToggleType(type)}
                title={pinned ? "品牌节点始终显示" : undefined}
                className={[
                  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
                  on
                    ? "border-primary/40 bg-primary/10 text-foreground"
                    : "border-border bg-background text-muted-foreground",
                  pinned ? "cursor-default" : count > 0 ? "hover:bg-muted" : "",
                ].join(" ")}
              >
                <span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                <span>{knowledgeNodeTypeLabel(type)}</span>
                <span className="text-muted-foreground">{count}</span>
              </button>
            );
          })}
        </div>
        <div className="relative w-48 shrink-0">
          <span className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">
            <Search className="text-muted-foreground size-4" aria-hidden />
          </span>
          <Input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="搜索实体…"
            controlSize="sm"
            className="pl-9"
            aria-label="搜索实体"
          />
        </div>
      </div>
    </div>
  );
}
