import * as React from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DIALOG_EXIT_MS = 200;

type PromptConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

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
  const [present, setPresent] = React.useState(open);
  const [closing, setClosing] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setPresent(true);
      setClosing(false);
      return;
    }
    if (!present) return;
    setClosing(true);
    const timer = window.setTimeout(() => {
      setPresent(false);
      setClosing(false);
    }, DIALOG_EXIT_MS);
    return () => window.clearTimeout(timer);
  }, [open, present]);

  React.useEffect(() => {
    if (!present || closing) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !submitting) onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [present, closing, submitting, onOpenChange]);

  if (!present) return null;

  const requestClose = () => {
    if (!submitting) onOpenChange(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className={cn(
          "absolute inset-0 bg-black/80",
          closing ? "animate-out fade-out-0 duration-200" : "animate-in fade-in-0 duration-200",
        )}
        aria-label="关闭对话框"
        onClick={requestClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="prompt-confirm-dialog-title"
        className={cn(
          "border-border relative z-10 w-full max-w-md rounded-xl border bg-white shadow-lg",
          closing
            ? "animate-out fade-out-0 zoom-out-95 duration-200"
            : "animate-in fade-in-0 zoom-in-95 duration-200",
        )}
      >
        <div className="flex items-start justify-between px-5 pt-5 pb-2">
          <div>
            <h2 id="prompt-confirm-dialog-title" className="text-base font-semibold">
              {title}
            </h2>
            <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{description}</p>
          </div>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground -mr-1 rounded-md p-1"
            aria-label="关闭"
            disabled={submitting}
            onClick={requestClose}
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4">
          <Button
            type="button"
            variant="primaryOutline"
            disabled={submitting}
            onClick={requestClose}
          >
            取消
          </Button>
          <Button type="button" disabled={submitting} onClick={onConfirm}>
            {submitting ? "处理中…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
