import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { SetupSelect, SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { Input, InputGroup } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  maxPromptCount,
  newPromptRow,
} from "@/lib/setup";
import type { PromptRow, TopicRow } from "@/types";
import { cn } from "@/lib/utils";

/** 三列轨道：提示词（宽）| 主题（窄）| Checkbox+删除 */
const PROMPT_COLS = "grid-cols-[minmax(0,1fr)_minmax(0,12rem)_auto]" as const;

const promptTableGrid = cn("grid w-full items-center gap-x-4 gap-y-1", PROMPT_COLS);

const promptHeaderGridClass = cn("col-span-full grid gap-x-4 gap-y-1 pl-2", PROMPT_COLS);

/** 与竞品 5 行列表等高：5 × h-9 + 4 × gap-y-2 */
const promptListBodyClass = cn(
  "col-span-full grid min-h-[13.25rem] max-h-[13.25rem] gap-x-4 gap-y-2 overflow-y-auto overscroll-contain pl-2 py-1",
  PROMPT_COLS,
);

const promptCheckboxClass =
  "size-[18px] shrink-0 rounded-[4px] border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground [&_svg]:size-3";

const promptMergedSelectClass =
  "border-input min-w-0 border-l bg-muted-background [&_button]:h-9 [&_button]:rounded-none [&_button]:rounded-r-md [&_button]:border-0 [&_button]:bg-muted-background [&_button]:px-2 [&_button]:shadow-none [&_button]:focus:ring-0";

const promptRowActionsClass = "flex h-9 items-center gap-0";

const promptActionCellClass =
  "flex h-9 w-9 shrink-0 items-center justify-center justify-self-center self-center";

type SetupStepPromptProps = {
  rows: PromptRow[];
  topics: TopicRow[];
  onChange: (rows: PromptRow[]) => void;
};

export function SetupStepPrompt({ rows, topics, onChange }: SetupStepPromptProps) {
  const [draftText, setDraftText] = React.useState("");
  const maxCount = maxPromptCount(topics.length);
  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected = rows.length > 0 && rows.every((r) => r.selected);
  const atMax = rows.length >= maxCount;
  const defaultTopicId = topics[0]?.id ?? "";

  const topicOptions = topics.map((t) => ({ value: t.id, label: t.name }));

  const updateRow = (id: string, patch: Partial<PromptRow>) => {
    onChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: string) => {
    onChange(rows.filter((r) => r.id !== id));
  };

  const toggleAll = (checked: boolean) => {
    onChange(rows.map((r) => ({ ...r, selected: checked })));
  };

  const addFromDraft = () => {
    const text = draftText.trim();
    if (!text || atMax || !defaultTopicId) return;
    onChange([...rows, newPromptRow({ text, topicId: defaultTopicId, selected: true })]);
    setDraftText("");
  };

  return (
    <div className="flex w-full max-w-3xl flex-col gap-4">
      <div className={promptTableGrid}>
        <div className={promptHeaderGridClass}>
          <span className="text-foreground min-h-9 self-center text-sm font-semibold">
            提示词（{rows.length}/{maxCount}）
          </span>
          <span className="text-foreground min-h-9 self-center text-sm font-semibold">主题</span>
          <div className={cn(promptRowActionsClass, "col-start-3")}>
            <div className={promptActionCellClass}>
              <Checkbox
                checked={allSelected}
                onCheckedChange={(v) => toggleAll(v === true)}
                aria-label="全选提示词"
                className={promptCheckboxClass}
              />
            </div>
            <span aria-hidden className={cn(promptActionCellClass, "pointer-events-none")} />
          </div>
        </div>

        <div className={promptListBodyClass}>
          {rows.map((row) => (
            <React.Fragment key={row.id}>
              <InputGroup className="col-span-2 grid h-9 grid-cols-subgrid">
                <Input
                  variant="merged"
                  controlSize="sm"
                  value={row.text}
                  onChange={(e) => updateRow(row.id, { text: e.target.value })}
                  placeholder="输入提示词"
                  aria-label={`提示词 ${row.text || "未命名"}`}
                />
                <div className={promptMergedSelectClass}>
                  <SetupSelect
                    id={`prompt-topic-${row.id}`}
                    value={row.topicId || defaultTopicId}
                    onChange={(topicId) => updateRow(row.id, { topicId })}
                    options={topicOptions}
                    shell="prompt"
                  />
                </div>
              </InputGroup>
              <div className={cn(promptRowActionsClass, "col-start-3")}>
                <div className={promptActionCellClass}>
                  <Checkbox
                    checked={row.selected}
                    onCheckedChange={(v) => updateRow(row.id, { selected: v === true })}
                    aria-label={`选择 ${row.text || "提示词"}`}
                    className={promptCheckboxClass}
                  />
                </div>
                <div className={promptActionCellClass}>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground size-9"
                    onClick={() => removeRow(row.id)}
                    aria-label="删除"
                  >
                    <Trash2 className="size-4 stroke-[1.5]" />
                  </Button>
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>

        {!atMax && defaultTopicId ? (
          <div className="col-span-full flex w-full items-center gap-x-4 px-1.5 pt-2">
            <SetupTextInput
              shell="prompt"
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              placeholder="输入要添加的提示词"
              containerClassName="min-w-0 flex-1 basis-0"
              className="w-full"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addFromDraft();
                }
              }}
            />
            <Button
              type="button"
              variant="outline"
              className="text-muted-foreground h-9 shrink-0 gap-1.5 whitespace-nowrap rounded-md bg-muted-background px-4 text-sm font-normal"
              onClick={addFromDraft}
            >
              <Plus className="size-4 shrink-0" />
              添加提示词
            </Button>
          </div>
        ) : null}
      </div>

      <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
        <span>已选择 {selectedCount} 项</span>
        <span>最多可添加 {maxCount} 个提示词。</span>
      </div>
    </div>
  );
}
