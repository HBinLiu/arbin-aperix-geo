import { Sparkles } from "lucide-react";

import { SetupSelect } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type PromptGenerateDialogProps = {
  open: boolean;
  topicId: string;
  onTopicIdChange: (value: string) => void;
  topicOptions: { value: string; label: string }[];
  count: number;
  onCountChange: (value: number) => void;
  remaining: number;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: () => void;
};

function PromptGenerateDialogFooter({
  submitting,
  canSubmit,
  onSubmit,
}: {
  submitting: boolean;
  canSubmit: boolean;
  onSubmit: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <div className="border-border flex shrink-0 items-center justify-between gap-3 border-t px-5 py-4">
      <p className="text-muted-foreground text-xs">选择一个主题以生成用于 AI 监控的提示词。</p>
      <div className="flex shrink-0 gap-2">
        <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
          取消
        </Button>
        <Button type="button" disabled={submitting || !canSubmit} onClick={onSubmit}>
          {submitting ? "生成中…" : "生成提示词"}
        </Button>
      </div>
    </div>
  );
}

/** 提示词管理 · 生成提示词对话框 */
export function PromptGenerateDialog({
  open,
  topicId,
  onTopicIdChange,
  topicOptions,
  count,
  onCountChange,
  remaining,
  submitting = false,
  onOpenChange,
  onSubmit,
}: PromptGenerateDialogProps) {
  const canSubmit = Boolean(topicId && count > 0 && remaining > 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent
        className="flex max-h-[90vh] max-w-3xl flex-col overflow-hidden"
        aria-labelledby="prompt-generate-dialog-title"
      >
        <div className="border-border flex shrink-0 items-center justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="text-primary size-4" aria-hidden />
            <DialogTitle id="prompt-generate-dialog-title">配置提示词生成</DialogTitle>
          </div>
          <DialogClose />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div className="flex flex-col gap-6 md:flex-row md:gap-8">
            <div className="md:w-[220px] md:shrink-0">
              <p className="text-sm font-semibold">配置提示词生成</p>
              <p className="text-muted-foreground mt-2 text-xs leading-relaxed">
                选择主题后由 AI 生成监测提示词。地区与语言取自主体监测范围。每个主题最多可创建
                20 个提示词。
              </p>
            </div>

            <div className="min-w-0 flex-1 space-y-4">
              <Field label="主题" required>
                <SetupSelect
                  id="generate-topic"
                  value={topicId}
                  onChange={onTopicIdChange}
                  options={topicOptions}
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
                    disabled={submitting || remaining <= 0}
                    onChange={(event) => {
                      const next = Number.parseInt(event.target.value, 10);
                      if (Number.isNaN(next)) return;
                      onCountChange(Math.min(Math.max(next, 1), remaining));
                    }}
                    controlSize="sm"
                    className="border-border h-9 rounded-lg pr-28 shadow-none"
                  />
                  <span className="text-muted-foreground pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs whitespace-nowrap">
                    仅剩{remaining}个提示词
                  </span>
                </div>
              </Field>
            </div>
          </div>
        </div>

        <PromptGenerateDialogFooter
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
        {required ? <span className="text-destructive"> *</span> : null}
      </label>
      {children}
    </div>
  );
}
