import { SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";

type PromptAddTopicDialogProps = {
  open: boolean;
  mode?: "create" | "edit";
  name: string;
  onNameChange: (value: string) => void;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: () => void;
};

function PromptAddTopicDialogFooter({
  mode,
  submitting,
  canSubmit,
  onSubmit,
}: {
  mode: "create" | "edit";
  submitting: boolean;
  canSubmit: boolean;
  onSubmit: () => void;
}) {
  const { requestClose } = useDialog();
  const submitLabel =
    mode === "edit" ? (submitting ? "保存中…" : "保存") : submitting ? "添加中…" : "添加主题";

  return (
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting || !canSubmit} onClick={onSubmit}>
        {submitLabel}
      </Button>
    </DialogFooter>
  );
}

/** 提示词管理 · 添加 / 编辑主题对话框 */
export function PromptAddTopicDialog({
  open,
  mode = "create",
  name,
  onNameChange,
  submitting = false,
  onOpenChange,
  onSubmit,
}: PromptAddTopicDialogProps) {
  const canSubmit = Boolean(name.trim());
  const title = mode === "edit" ? "编辑主题" : "添加主题";

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby="prompt-add-topic-dialog-title">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id="prompt-add-topic-dialog-title">{title}</DialogTitle>
          <DialogClose />
        </div>

        <div className="space-y-4 p-5">
          <div className="space-y-1.5">
            <label htmlFor="topic-name" className="text-foreground px-1 text-sm font-medium">
              主题名称
              <span className="text-error"> *</span>
            </label>
            <SetupTextInput
              id="topic-name"
              value={name}
              onChange={(event) => onNameChange(event.target.value)}
              placeholder="请输入主题名称"
              disabled={submitting}
            />
          </div>
        </div>

        <PromptAddTopicDialogFooter
          mode={mode}
          submitting={submitting}
          canSubmit={canSubmit}
          onSubmit={onSubmit}
        />
      </DialogContent>
    </Dialog>
  );
}
