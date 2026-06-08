import * as React from "react";
import { X } from "lucide-react";

import { SetupSelect, SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DIALOG_EXIT_MS = 200;

type PromptFormDialogProps = {
  open: boolean;
  title: string;
  description?: string;
  submitLabel: string;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: () => void;
  children: React.ReactNode;
};

/** 提示词管理通用表单对话框 */
export function PromptFormDialog({
  open,
  title,
  description,
  submitLabel,
  submitting = false,
  onOpenChange,
  onSubmit,
  children,
}: PromptFormDialogProps) {
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
        aria-labelledby="prompt-form-dialog-title"
        className={cn(
          "border-border relative z-10 w-full max-w-lg rounded-xl border bg-white shadow-lg",
          closing
            ? "animate-out fade-out-0 zoom-out-95 duration-200"
            : "animate-in fade-in-0 zoom-in-95 duration-200",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <div>
            <h2 id="prompt-form-dialog-title" className="text-base font-semibold">
              {title}
            </h2>
            {description ? (
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{description}</p>
            ) : null}
          </div>
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

        <div className="space-y-4 p-5">{children}</div>

        <div className="flex justify-end gap-2 px-5 py-4">
          <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
            取消
          </Button>
          <Button type="button" disabled={submitting} onClick={onSubmit}>
            {submitting ? "保存中…" : submitLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

type PromptTextFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  multiline?: boolean;
  disabled?: boolean;
};

export function PromptTextField({
  id,
  label,
  value,
  onChange,
  placeholder,
  multiline = false,
  disabled = false,
}: PromptTextFieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-foreground px-1 text-sm font-medium">
        {label}
      </label>
      {multiline ? (
        <textarea
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          rows={4}
          className="border-input bg-background ring-offset-background placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[96px] w-full rounded-md border px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        />
      ) : (
        <SetupTextInput
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
        />
      )}
    </div>
  );
}

type PromptTopicFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
};

export function PromptTopicField({
  id,
  label,
  value,
  onChange,
  options,
}: PromptTopicFieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-foreground px-1 text-sm font-medium">
        {label}
      </label>
      <SetupSelect id={id} value={value} onChange={onChange} options={options} />
    </div>
  );
}

type PromptEnabledFieldProps = {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  disabled?: boolean;
};

export function PromptEnabledField({ enabled, onChange, disabled = false }: PromptEnabledFieldProps) {
  return (
    <div className="flex items-center gap-2 px-1">
      <input
        id="prompt-enabled"
        type="checkbox"
        checked={enabled}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="accent-primary size-4 rounded border"
      />
      <label htmlFor="prompt-enabled" className="text-sm">
        启用该提示词
      </label>
    </div>
  );
}
