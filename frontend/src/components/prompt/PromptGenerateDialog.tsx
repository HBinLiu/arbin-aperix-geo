import * as React from "react";
import { Sparkles } from "lucide-react";

import { PromptFunnelBadge } from "@/components/analysis/prompt/PromptFunnelBadge";
import { PromptIntentBadge } from "@/components/analysis/prompt/PromptIntentBadge";
import { SetupSelect } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { taxonomyOptionLabel, taxonomySelectOptions } from "@/lib/prompt/taxonomy";
import type { GeneratedPromptItem, PromptTaxonomy } from "@/types";
import { cn } from "@/lib/utils";

type CandidateRow = GeneratedPromptItem & {
  id: string;
  selected: boolean;
};

type PromptGenerateDialogProps = {
  open: boolean;
  taxonomy: PromptTaxonomy;
  topicId: string;
  onTopicIdChange: (value: string) => void;
  topicOptions: { value: string; label: string }[];
  funnelStage: string;
  onFunnelStageChange: (value: string) => void;
  searchIntent: string;
  onSearchIntentChange: (value: string) => void;
  decisionType: string;
  onDecisionTypeChange: (value: string) => void;
  count: number;
  onCountChange: (value: number) => void;
  remaining: number;
  previewLoading?: boolean;
  confirmLoading?: boolean;
  onOpenChange: (open: boolean) => void;
  onPreview: (input: {
    topicId: string;
    count: number;
    funnelStage: string;
    searchIntent: string;
    decisionType: string;
  }) => Promise<GeneratedPromptItem[]>;
  onConfirm: (input: {
    topicId: string;
    items: GeneratedPromptItem[];
  }) => Promise<void>;
};

const promptCheckboxClass =
  "size-[18px] shrink-0 rounded-[4px] data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground [&_svg]:size-3";

const selectListGrid = cn(
  "grid w-full items-start gap-x-3 gap-y-2",
  "grid-cols-[auto_minmax(0,1fr)_5rem_4rem_6rem]",
);

const funnelIntentCellClass = "flex min-h-9 items-center justify-center";

/** 提示词管理 · 生成提示词对话框（左侧配置，右侧预览多选） */
export function PromptGenerateDialog({
  open,
  taxonomy,
  topicId,
  onTopicIdChange,
  topicOptions,
  funnelStage,
  onFunnelStageChange,
  searchIntent,
  onSearchIntentChange,
  decisionType,
  onDecisionTypeChange,
  count,
  onCountChange,
  remaining,
  previewLoading = false,
  confirmLoading = false,
  onOpenChange,
  onPreview,
  onConfirm,
}: PromptGenerateDialogProps) {
  const [candidates, setCandidates] = React.useState<CandidateRow[]>([]);

  React.useEffect(() => {
    if (!open) {
      setCandidates([]);
    }
  }, [open]);

  const taxonomyReady =
    taxonomy.funnel_stages.length > 0 &&
    taxonomy.search_intents.length > 0 &&
    taxonomy.decision_types.length > 0;
  const canPreview = Boolean(
    taxonomyReady &&
      topicId &&
      count > 0 &&
      remaining > 0 &&
      funnelStage &&
      searchIntent &&
      decisionType,
  );
  const hasCandidates = candidates.length > 0;
  const selectedCount = candidates.filter((row) => row.selected).length;
  const allSelected = hasCandidates && candidates.every((row) => row.selected);
  const busy = previewLoading || confirmLoading;

  const handlePreview = async () => {
    if (!canPreview) return;
    try {
      const items = await onPreview({
        topicId,
        count,
        funnelStage,
        searchIntent,
        decisionType,
      });
      setCandidates(
        items.map((item) => ({
          ...item,
          id: crypto.randomUUID(),
          selected: true,
        })),
      );
    } catch {
      // handled by API
    }
  };

  const handleConfirm = async () => {
    const selected = candidates.filter((row) => row.selected);
    if (selected.length === 0) return;
    try {
      await onConfirm({ topicId, items: selected });
    } catch {
      // handled by API
    }
  };

  const toggleAll = (checked: boolean) => {
    setCandidates((rows) => rows.map((row) => ({ ...row, selected: checked })));
  };

  const toggleRow = (id: string, checked: boolean) => {
    setCandidates((rows) =>
      rows.map((row) => (row.id === id ? { ...row, selected: checked } : row)),
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={busy}>
      <DialogContent
        className="flex h-[min(72vh,38rem)] max-h-[80vh] max-w-4xl flex-col overflow-hidden"
        aria-labelledby="prompt-generate-dialog-title"
      >
        <div className="border-border flex shrink-0 items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="text-primary size-4" aria-hidden />
            <DialogTitle id="prompt-generate-dialog-title">配置提示词生成</DialogTitle>
          </div>
          <DialogClose />
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-5 py-5">
          <div className="flex min-h-0 flex-1 gap-6 md:flex-row md:items-stretch md:gap-8">
            <div className="md:w-[260px] md:shrink-0">
              <div className="space-y-4">
                <Field label="主题" required>
                  <SetupSelect
                    id="generate-topic"
                    value={topicId}
                    onChange={onTopicIdChange}
                    options={topicOptions}
                  />
                </Field>

                <Field label="搜索意图" required>
                  <SetupSelect
                    id="generate-intent"
                    value={searchIntent}
                    onChange={onSearchIntentChange}
                    options={taxonomySelectOptions(taxonomy.search_intents)}
                  />
                </Field>

                <Field label="营销漏斗" required>
                  <SetupSelect
                    id="generate-funnel"
                    value={funnelStage}
                    onChange={onFunnelStageChange}
                    options={taxonomySelectOptions(taxonomy.funnel_stages)}
                  />
                </Field>

                <Field label="决策场景" required>
                  <SetupSelect
                    id="generate-decision"
                    value={decisionType}
                    onChange={onDecisionTypeChange}
                    options={taxonomySelectOptions(taxonomy.decision_types)}
                  />
                </Field>

                <Field label="要生成的提示词数量" required>
                  <div className="relative">
                    <Input
                      id="generate-count"
                      type="number"
                      min={1}
                      max={Math.max(remaining, 1)}
                      value={count}
                      disabled={busy || remaining <= 0}
                      onChange={(event) => {
                        const next = Number.parseInt(event.target.value, 10);
                        if (Number.isNaN(next)) return;
                        onCountChange(Math.min(Math.max(next, 1), remaining));
                      }}
                      controlSize="sm"
                      className="border-border h-9 rounded-lg pr-28"
                    />
                    <span className="text-muted-foreground pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs whitespace-nowrap">
                      剩余{remaining}个额度
                    </span>
                  </div>
                </Field>

                <Button
                  type="button"
                  variant="default"
                  className="w-full"
                  disabled={busy || !canPreview}
                  onClick={() => void handlePreview()}
                >
                  {previewLoading ? "生成中…" : hasCandidates ? "重新生成" : "生成"}
                </Button>
              </div>
            </div>

            <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
              <div className="shrink-0">
                <p className="text-sm font-semibold">配置提示词生成</p>
                <p className="text-muted-foreground mt-2 text-xs leading-relaxed">
                  第一步：点击左侧「生成」预览候选提示词；第二步：勾选后点击底部「添加」写入。
                </p>
              </div>

              <div className="border-border flex min-h-0 flex-1 flex-col rounded-lg border">
                {hasCandidates ? (
                  <div className="flex min-h-0 flex-1 flex-col p-3">
                    <div className={cn(selectListGrid, "shrink-0")}>
                      <div className="col-span-full grid grid-cols-subgrid items-center px-1">
                        <div className="flex h-9 items-center">
                          <Checkbox
                            checked={allSelected}
                            onCheckedChange={(value) => toggleAll(value === true)}
                            aria-label="全选提示词"
                            className={promptCheckboxClass}
                          />
                        </div>
                        <span className="text-foreground text-sm font-semibold">
                          提示词
                        </span>
                        <span className={cn(funnelIntentCellClass, "text-foreground text-sm font-semibold")}>
                          漏斗
                        </span>
                        <span className={cn(funnelIntentCellClass, "text-foreground text-sm font-semibold")}>
                          意图
                        </span>
                        <span className={cn(funnelIntentCellClass, "text-foreground text-sm font-semibold")}>
                          决策
                        </span>
                      </div>
                    </div>

                    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 py-1">
                      <div className={selectListGrid}>
                        {candidates.map((row) => (
                          <div
                            key={row.id}
                            className="col-span-full grid grid-cols-subgrid items-start"
                          >
                            <div className="flex min-h-9 items-start pt-1.5">
                              <Checkbox
                                checked={row.selected}
                                onCheckedChange={(value) => toggleRow(row.id, value === true)}
                                aria-label={`选择 ${row.text}`}
                                className={promptCheckboxClass}
                              />
                            </div>
                            <p className="text-foreground min-h-9 py-1.5 text-sm leading-relaxed">
                              {row.text}
                            </p>
                            <div className={cn(funnelIntentCellClass, "pl-2")}>
                              <PromptFunnelBadge stage={row.funnel_stage} />
                            </div>
                            <div className={cn(funnelIntentCellClass, "pl-1")}>
                              <PromptIntentBadge intent={row.search_intent} />
                            </div>
                            <div className={cn(funnelIntentCellClass, "justify-start px-1")}>
                              <span className="text-foreground line-clamp-2 text-center text-xs leading-snug">
                                {taxonomyOptionLabel(taxonomy.decision_types, row.decision_type)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-muted-foreground flex flex-1 items-center justify-center px-4 py-8 text-center text-sm">
                    点击左侧「生成」后，预览结果将显示在此处。
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <PromptGenerateDialogFooter
          busy={busy}
          hasCandidates={hasCandidates}
          selectedCount={selectedCount}
          confirmLoading={confirmLoading}
          onConfirm={() => void handleConfirm()}
        />
      </DialogContent>
    </Dialog>
  );
}

function PromptGenerateDialogFooter({
  busy,
  hasCandidates,
  selectedCount,
  confirmLoading,
  onConfirm,
}: {
  busy: boolean;
  hasCandidates: boolean;
  selectedCount: number;
  confirmLoading: boolean;
  onConfirm: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <div className="border-border flex shrink-0 justify-end gap-2 border-t px-5 py-4">
      <Button type="button" variant="outline" disabled={busy} onClick={requestClose}>
        取消
      </Button>
      <Button
        type="button"
        disabled={busy || !hasCandidates || selectedCount <= 0}
        onClick={onConfirm}
      >
        {confirmLoading ? "添加中…" : `添加选中（${selectedCount}）`}
      </Button>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-foreground px-1 text-sm font-medium">
        {label}
        {required ? <span className="text-error"> *</span> : null}
      </label>
      {children}
    </div>
  );
}
