import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";

type PromptConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

function PromptConfirmDialogFooter({
  confirmLabel,
  submitting,
  onConfirm,
}: {
  confirmLabel: string;
  submitting: boolean;
  onConfirm: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <DialogFooter>
      <Button type="button" variant="primaryOutline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting} onClick={onConfirm}>
        {submitting ? "处理中…" : confirmLabel}
      </Button>
    </DialogFooter>
  );
}

/** 提示词管理 · 确认对话框 */
export function PromptConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "确认",
  submitting = false,
  onOpenChange,
  onConfirm,
}: PromptConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-md" aria-labelledby="prompt-confirm-dialog-title">
        <div className="flex items-start justify-between px-5 pt-5 pb-2">
          <DialogHeader className="block">
            <DialogTitle id="prompt-confirm-dialog-title">{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>
          <DialogClose />
        </div>
        <PromptConfirmDialogFooter
          confirmLabel={confirmLabel}
          submitting={submitting}
          onConfirm={onConfirm}
        />
      </DialogContent>
    </Dialog>
  );
}
