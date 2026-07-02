import { SetupSelect, SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { taxonomySelectOptions } from "@/lib/prompt/taxonomy";
import type { PromptTaxonomy } from "@/types";

type PromptFormMode = "create" | "edit";

type PromptCreateDialogProps = {
  open: boolean;
  mode?: PromptFormMode;
  taxonomy: PromptTaxonomy;
  topicId: string;
  onTopicIdChange: (value: string) => void;
  topicOptions: { value: string; label: string }[];
  text: string;
  onTextChange: (value: string) => void;
  funnelStage: string;
  onFunnelStageChange: (value: string) => void;
  searchIntent: string;
  onSearchIntentChange: (value: string) => void;
  decisionType: string;
  onDecisionTypeChange: (value: string) => void;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: () => void;
};

function PromptCreateDialogFooter({
  mode,
  submitting,
  canSubmit,
  onSubmit,
}: {
  mode: PromptFormMode;
  submitting: boolean;
  canSubmit: boolean;
  onSubmit: () => void;
}) {
  const { requestClose } = useDialog();
  const isEdit = mode === "edit";

  return (
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting || !canSubmit} onClick={onSubmit}>
        {submitting ? (isEdit ? "保存中…" : "创建中…") : isEdit ? "保存" : "创建"}
      </Button>
    </DialogFooter>
  );
}

/** 提示词管理 · 创建 / 编辑提示词对话框 */
export function PromptCreateDialog({
  open,
  mode = "create",
  taxonomy,
  topicId,
  onTopicIdChange,
  topicOptions,
  text,
  onTextChange,
  funnelStage,
  onFunnelStageChange,
  searchIntent,
  onSearchIntentChange,
  decisionType,
  onDecisionTypeChange,
  submitting = false,
  onOpenChange,
  onSubmit,
}: PromptCreateDialogProps) {
  const isEdit = mode === "edit";
  const taxonomyReady =
    taxonomy.funnel_stages.length > 0 &&
    taxonomy.search_intents.length > 0 &&
    taxonomy.decision_types.length > 0;
  const canSubmit = Boolean(
    taxonomyReady &&
      topicId &&
      text.trim() &&
      funnelStage &&
      searchIntent &&
      decisionType,
  );
  const titleId = isEdit ? "prompt-edit-dialog-title" : "prompt-create-dialog-title";

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby={titleId}>
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id={titleId}>{isEdit ? "编辑提示词" : "创建提示词"}</DialogTitle>
          <DialogClose />
        </div>

        <div className="space-y-4 p-5">
          <Field label="主题" required>
            <SetupSelect
              id={isEdit ? "edit-prompt-topic" : "create-prompt-topic"}
              value={topicId}
              onChange={onTopicIdChange}
              options={topicOptions}
            />
          </Field>

          <Field label="提示词" required>
            <SetupTextInput
              id={isEdit ? "edit-prompt-text" : "create-prompt-text"}
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder="请输入提示词"
              disabled={submitting}
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="营销漏斗" required>
              <SetupSelect
                id={isEdit ? "edit-prompt-funnel" : "create-prompt-funnel"}
                value={funnelStage}
                onChange={onFunnelStageChange}
                options={taxonomySelectOptions(taxonomy.funnel_stages)}
              />
            </Field>
            
            <Field label="搜索意图" required>
              <SetupSelect
                id={isEdit ? "edit-prompt-intent" : "create-prompt-intent"}
                value={searchIntent}
                onChange={onSearchIntentChange}
                options={taxonomySelectOptions(taxonomy.search_intents)}
              />
            </Field>

            <Field label="决策场景" required>
              <SetupSelect
                id={isEdit ? "edit-prompt-decision" : "create-prompt-decision"}
                value={decisionType}
                onChange={onDecisionTypeChange}
                options={taxonomySelectOptions(taxonomy.decision_types)}
              />
            </Field>
          </div>
        </div>

        <PromptCreateDialogFooter
          mode={mode}
          submitting={submitting}
          canSubmit={canSubmit}
          onSubmit={onSubmit}
        />
      </DialogContent>
    </Dialog>
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
