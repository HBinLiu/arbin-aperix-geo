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

type PromptCreateDialogProps = {
  open: boolean;
  topicId: string;
  onTopicIdChange: (value: string) => void;
  topicOptions: { value: string; label: string }[];
  text: string;
  onTextChange: (value: string) => void;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: () => void;
};

function PromptCreateDialogFooter({
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
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting || !canSubmit} onClick={onSubmit}>
        {submitting ? "创建中…" : "创建"}
      </Button>
    </DialogFooter>
  );
}

/** 提示词管理 · 创建提示词对话框 */
export function PromptCreateDialog({
  open,
  topicId,
  onTopicIdChange,
  topicOptions,
  text,
  onTextChange,
  submitting = false,
  onOpenChange,
  onSubmit,
}: PromptCreateDialogProps) {
  const canSubmit = Boolean(topicId && text.trim());

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby="prompt-create-dialog-title">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id="prompt-create-dialog-title">创建提示词</DialogTitle>
          <DialogClose />
        </div>

        <div className="space-y-4 p-5">
          <Field label="主题" required>
            <SetupSelect
              id="create-prompt-topic"
              value={topicId}
              onChange={onTopicIdChange}
              options={topicOptions}
            />
          </Field>

          <Field label="提示词" required>
            <SetupTextInput
              id="create-prompt-text"
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder="请输入提示词"
              disabled={submitting}
            />
          </Field>
        </div>

        <PromptCreateDialogFooter
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
