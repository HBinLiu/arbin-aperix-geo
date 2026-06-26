import type { VariantProps } from "class-variance-authority";

import { Button, buttonVariants } from "@/components/ui/button";
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
  confirmVariant?: VariantProps<typeof buttonVariants>["variant"];
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

function PromptConfirmDialogFooter({
  confirmLabel,
  confirmVariant = "default",
  submitting,
  onConfirm,
}: {
  confirmLabel: string;
  confirmVariant?: VariantProps<typeof buttonVariants>["variant"];
  submitting: boolean;
  onConfirm: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" variant={confirmVariant} disabled={submitting} onClick={onConfirm}>
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
  confirmVariant = "default",
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
          confirmVariant={confirmVariant}
          submitting={submitting}
          onConfirm={onConfirm}
        />
      </DialogContent>
    </Dialog>
  );
}
