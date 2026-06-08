import * as React from "react";
import { X } from "lucide-react";

import { SetupSelect, SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DIALOG_EXIT_MS = 200;

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

  const canSubmit = Boolean(topicId && text.trim());

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
        aria-labelledby="prompt-create-dialog-title"
        className={cn(
          "border-border relative z-10 w-full max-w-lg rounded-xl border bg-white shadow-lg",
          closing
            ? "animate-out fade-out-0 zoom-out-95 duration-200"
            : "animate-in fade-in-0 zoom-in-95 duration-200",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <h2 id="prompt-create-dialog-title" className="text-base font-semibold">
            创建提示词
          </h2>
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground rounded-md p-1"
            aria-label="关闭"
            disabled={submitting}
            onClick={requestClose}
          >
            <X className="size-5" aria-hidden />
          </button>
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

        <div className="flex justify-end gap-2 px-5 py-4">
          <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
            取消
          </Button>
          <Button type="button" disabled={submitting || !canSubmit} onClick={onSubmit}>
            {submitting ? "创建中…" : "创建"}
          </Button>
        </div>
      </div>
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
        {required ? <span className="text-destructive"> *</span> : null}
      </label>
      {children}
    </div>
  );
}
