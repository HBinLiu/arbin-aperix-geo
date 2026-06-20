import { Plus, Search, Sparkles, Trash2, Upload } from "lucide-react";

import { ActionTooltip } from "@/components/common/ActionTooltip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PROMPT_TOOLBAR_MIN_WIDTH, type PromptEnabledFilter } from "@/lib/prompt";

const ENABLED_FILTER_TABS: { id: PromptEnabledFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "enabled", label: "启用" },
  { id: "disabled", label: "停用" },
];

type PromptToolbarProps = {
  enabledFilter: PromptEnabledFilter;
  onEnabledFilterChange: (value: PromptEnabledFilter) => void;
  search: string;
  onSearchChange: (value: string) => void;
  selectedCount: number;
  onBatchDelete: () => void;
  onUpload: () => void;
  onGenerate: () => void;
  onAddPrompt: () => void;
  disabled?: boolean;
};

/** 提示词管理 · 工具栏 */
export function PromptToolbar({
  enabledFilter,
  onEnabledFilterChange,
  search,
  onSearchChange,
  selectedCount,
  onBatchDelete,
  onUpload,
  onGenerate,
  onAddPrompt,
  disabled = false,
}: PromptToolbarProps) {
  return (
    <div className="border-border min-w-0 overflow-x-auto border-b">
      <div
        className="flex w-full flex-nowrap items-center gap-2 px-4 py-3"
        style={{ minWidth: PROMPT_TOOLBAR_MIN_WIDTH }}
      >
        <div className="flex shrink-0 flex-nowrap items-center gap-2">
          <Tabs
            value={enabledFilter}
            onValueChange={(value) => onEnabledFilterChange(value as PromptEnabledFilter)}
            className="shrink-0"
          >
            <TabsList className="h-9">
              {ENABLED_FILTER_TABS.map((tab) => (
                <TabsTrigger key={tab.id} value={tab.id} className="px-3 text-xs">
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="relative w-[200px] shrink-0">
            <Search
              className="text-muted-foreground pointer-events-none absolute top-1/2 left-4 size-3.5 -translate-y-1/2"
              aria-hidden
            />
            <Input
              type="search"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="搜索提示词..."
              controlSize="sm"
              className="border-border h-9 w-full rounded-lg bg-white pr-3 pl-8 text-xs shadow-none"
              aria-label="搜索提示词"
              disabled={disabled}
            />
          </div>
        </div>

        <div className="ml-auto flex shrink-0 flex-nowrap items-center gap-2">
          <ActionTooltip label="批量删除">
            <Button
              type="button"
              variant={selectedCount > 0 ? "brandout" : "outline"}
              size="icon"
              className="size-9 rounded-lg"
              disabled={disabled || selectedCount === 0}
              aria-label="批量删除"
              onClick={onBatchDelete}
            >
              <Trash2 className="size-4" aria-hidden />
            </Button>
          </ActionTooltip>
          <Button
            type="button"
            variant="brandout"
            className="h-9 gap-1.5 rounded-lg px-3"
            disabled={disabled}
            onClick={onUpload}
          >
            <Upload className="size-3.5" aria-hidden />
            上传提示词
          </Button>
          <Button
            type="button"
            variant="brandout"
            className="h-9 gap-1.5 rounded-lg px-3"
            disabled={disabled}
            onClick={onGenerate}
          >
            <Sparkles className="size-3.5" aria-hidden />
            生成提示词
          </Button>
          <Button
            type="button"
            className="h-9 gap-1.5 rounded-lg px-3 text-xs"
            disabled={disabled}
            onClick={onAddPrompt}
          >
            <Plus className="size-3.5" aria-hidden />
            添加提示词
          </Button>
        </div>
      </div>
    </div>
  );
}
