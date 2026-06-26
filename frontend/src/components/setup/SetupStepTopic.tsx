import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { MAX_TOPICS, newTopicRow } from "@/lib/setup";
import type { TopicRow } from "@/types";
import { cn } from "@/lib/utils";

const TOPIC_COLS = "grid-cols-[minmax(0,1fr)_2.25rem_2.25rem]" as const;

const topicTableGrid = cn("grid w-full items-center gap-x-4 gap-y-3", TOPIC_COLS);

const topicCheckboxClass =
  "size-[18px] shrink-0 rounded-[4px] border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground [&_svg]:size-3";

const topicActionCellClass =
  "flex h-9 w-9 shrink-0 items-center justify-center justify-self-center self-center";

type SetupStepTopicProps = {
  rows: TopicRow[];
  onChange: (rows: TopicRow[]) => void;
  title?: string;
  description?: string;
  placeholder?: string;
  addLabel?: string;
};

export function SetupStepTopic({
  rows,
  onChange,
  title = "主题",
  description,
  placeholder = "主题名称",
  addLabel = "添加主题",
}: SetupStepTopicProps) {
  const [draftTopic, setDraftTopic] = React.useState("");
  const selectedCount = rows.filter((r) => r.selected).length;
  const allSelected = rows.length > 0 && rows.every((r) => r.selected);
  const atMax = rows.length >= MAX_TOPICS;

  const updateRow = (id: string, patch: Partial<TopicRow>) => {
    onChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: string) => {
    onChange(rows.filter((r) => r.id !== id));
  };

  const toggleAll = (checked: boolean) => {
    onChange(rows.map((r) => ({ ...r, selected: checked })));
  };

  const addFromDraft = () => {
    const name = draftTopic.trim();
    if (!name || atMax) return;
    if (rows.some((r) => r.name.trim() === name)) {
      setDraftTopic("");
      return;
    }
    onChange([...rows, newTopicRow({ name, selected: true })]);
    setDraftTopic("");
  };

  return (
    <div className="flex w-full max-w-3xl flex-col gap-4">
      {description ? <p className="text-muted-foreground text-xs">{description}</p> : null}
      <div className={topicTableGrid}>
        <span className="text-foreground flex h-9 items-center px-0.5 text-sm font-semibold">
          {title}（{rows.length}/{MAX_TOPICS}）
        </span>
        <div className={cn(topicActionCellClass, "col-start-2")}>
          <Checkbox
            checked={allSelected}
            onCheckedChange={(v) => toggleAll(v === true)}
            aria-label="全选主题"
            className={topicCheckboxClass}
          />
        </div>
        <span aria-hidden className={cn(topicActionCellClass, "col-start-3")} />

        {rows.map((row) => (
          <React.Fragment key={row.id}>
            <Input
              controlSize="sm"
              value={row.name}
              onChange={(e) => updateRow(row.id, { name: e.target.value })}
              placeholder={placeholder}
              aria-label={`${title} ${row.name || "未命名"}`}
            />
            <div className={cn(topicActionCellClass, "col-start-2")}>
              <Checkbox
                checked={row.selected}
                onCheckedChange={(v) => updateRow(row.id, { selected: v === true })}
                aria-label={`选择 ${row.name || "主题"}`}
                className={topicCheckboxClass}
              />
            </div>
            <div className={cn(topicActionCellClass, "col-start-3")}>
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
          </React.Fragment>
        ))}

        {!atMax ? (
          <div className="col-span-full flex w-full items-center gap-x-4 pt-1">
            <SetupTextInput
              value={draftTopic}
              onChange={(e) => setDraftTopic(e.target.value)}
              placeholder={placeholder}
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
              {addLabel}
            </Button>
          </div>
        ) : null}
      </div>

      <div className="text-muted-foreground flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
        <span>已选择 {selectedCount} 项</span>
        <span>最多可添加 {MAX_TOPICS} 个{title}。</span>
      </div>
    </div>
  );
}
