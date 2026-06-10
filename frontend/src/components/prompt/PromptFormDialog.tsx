import { SetupSelect, SetupTextInput } from "@/components/setup/SetupField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";

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

function PromptFormDialogFooter({
  submitLabel,
  submitting,
  onSubmit,
}: {
  submitLabel: string;
  submitting: boolean;
  onSubmit: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting} onClick={onSubmit}>
        {submitting ? "保存中…" : submitLabel}
      </Button>
    </DialogFooter>
  );
}

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
  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby="prompt-form-dialog-title">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <div>
            <DialogTitle id="prompt-form-dialog-title">{title}</DialogTitle>
            {description ? (
              <DialogDescription className="mt-1 text-xs">{description}</DialogDescription>
            ) : null}
          </div>
          <DialogClose />
        </div>

        <div className="space-y-4 p-5">{children}</div>

        <PromptFormDialogFooter
          submitLabel={submitLabel}
          submitting={submitting}
          onSubmit={onSubmit}
        />
      </DialogContent>
    </Dialog>
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
