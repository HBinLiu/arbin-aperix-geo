import { useMemo, useState } from "react";
import { CirclePlus, Search, SquarePen, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { filterTopicsBySearch, PROMPT_TOPIC_ALL, topicPromptCounts } from "@/lib/prompt";
import type { SubjectPrompt, SubjectTopic } from "@/types";
import { cn } from "@/lib/utils";

type PromptTopicSidebarProps = {
  topics: SubjectTopic[];
  prompts: SubjectPrompt[];
  selectedTopicId: string;
  onSelectTopic: (topicId: string) => void;
  onAddTopic: () => void;
  onEditTopic: (topic: SubjectTopic) => void;
  onDeleteTopic: (topic: SubjectTopic) => void;
  loading?: boolean;
  actionsDisabled?: boolean;
};

/** 提示词管理 · 主题侧栏 */
export function PromptTopicSidebar({
  topics,
  prompts,
  selectedTopicId,
  onSelectTopic,
  onAddTopic,
  onEditTopic,
  onDeleteTopic,
  loading = false,
  actionsDisabled = false,
}: PromptTopicSidebarProps) {
  const [search, setSearch] = useState("");
  const counts = useMemo(() => topicPromptCounts(topics, prompts), [topics, prompts]);
  const filteredTopics = useMemo(
    () => filterTopicsBySearch(topics, search),
    [topics, search],
  );

  return (
    <aside className="border-border flex min-h-0 w-[240px] shrink-0 flex-col self-stretch border-r bg-muted-background">
      <div className="border-border border-b p-3">
        <div className="relative">
          <span className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">
            <Search className="text-muted-foreground size-3.5" aria-hidden />
          </span>
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索主题..."
            controlSize="sm"
            className="border-border h-9 rounded-lg bg-muted-background pl-9 text-xs"
            aria-label="搜索主题"
          />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto p-2" aria-label="主题列表" aria-busy={loading}>
        <TopicNavItem
          label="所有主题"
          count={prompts.length}
          active={selectedTopicId === PROMPT_TOPIC_ALL}
          onClick={() => onSelectTopic(PROMPT_TOPIC_ALL)}
        />
        {filteredTopics.map((topic) => (
          <TopicNavItem
            key={topic.id}
            label={topic.name}
            count={counts.get(topic.id) ?? 0}
            active={selectedTopicId === topic.id}
            onClick={() => onSelectTopic(topic.id)}
            onEdit={
              actionsDisabled
                ? undefined
                : () => {
                    onEditTopic(topic);
                  }
            }
            onDelete={
              actionsDisabled
                ? undefined
                : () => {
                    onDeleteTopic(topic);
                  }
            }
          />
        ))}
      </nav>

      <div className="border-border border-t p-3">
        <Button
          type="button"
          variant="brandout"
          className="h-8 w-full justify-center gap-1.5 rounded-lg"
          disabled={actionsDisabled}
          onClick={onAddTopic}
        >
          <CirclePlus className="size-3.5" aria-hidden />
          添加主题
        </Button>
      </div>
    </aside>
  );
}

function TopicNavItem({
  label,
  count,
  active,
  onClick,
  onEdit,
  onDelete,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const showActions = Boolean(onEdit || onDelete);

  return (
    <div
      className={cn(
        "group relative rounded-md transition-colors",
        active ? "bg-background" : "hover:bg-background/60",
      )}
    >
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
          active ? "text-foreground font-medium" : "text-foreground",
        )}
      >
        <span className="truncate">{label}</span>
        <span
          className={cn(
            "text-muted-foreground shrink-0 tabular-nums",
            showActions && "group-hover:hidden group-focus-within:hidden",
          )}
        >
          {count}
        </span>
      </button>

      {showActions ? (
        <div className="absolute top-1/2 right-1 z-10 hidden -translate-y-1/2 items-center gap-0.5 group-hover:flex group-focus-within:flex">
          {onEdit ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-foreground size-7"
              aria-label={`编辑主题 ${label}`}
              onClick={(event) => {
                event.stopPropagation();
                onEdit();
              }}
            >
              <SquarePen className="size-3.5" aria-hidden />
            </Button>
          ) : null}
          {onDelete ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-destructive size-7"
              aria-label={`删除主题 ${label}`}
              onClick={(event) => {
                event.stopPropagation();
                onDelete();
              }}
            >
              <Trash2 className="size-3.5" aria-hidden />
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
