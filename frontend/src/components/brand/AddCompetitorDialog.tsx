import * as React from "react";
import { Building2, Globe, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SetupTextInput } from "@/components/setup/SetupField";
import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";

const DIALOG_EXIT_MS = 200;

type AddCompetitorDialogProps = {
  open: boolean;
  subjectType: string;
  existingValues: string[];
  onOpenChange: (open: boolean) => void;
  onSubmit: (value: string) => void;
  submitting?: boolean;
};

export function AddCompetitorDialog({
  open,
  subjectType,
  existingValues,
  onOpenChange,
  onSubmit,
  submitting = false,
}: AddCompetitorDialogProps) {
  const isDomain = subjectType === "domain";
  const [value, setValue] = React.useState("");
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
    if (!open) return;
    setValue("");
  }, [open]);

  React.useEffect(() => {
    if (!present || closing) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [present, closing, submitting, onOpenChange]);

  const handleSubmit = () => {
    const raw = value.trim();
    if (!raw) {
      toast.error(isDomain ? "请填写竞争对手域名。" : "请填写竞争对手品牌名称。");
      return;
    }

    if (isDomain) {
      const host = hostnameFromWebsiteInput(raw);
      const domain = registrableDomain(host || raw);
      if (!domain || domain.length < 3) {
        toast.error("请填写有效的网站域名。");
        return;
      }
      if (existingValues.includes(domain)) {
        toast.error("该竞品域名已存在。");
        return;
      }
      onSubmit(domain);
      return;
    }

    if (existingValues.includes(raw)) {
      toast.error("该竞品品牌已存在。");
      return;
    }

    onSubmit(raw);
  };

  if (!present) return null;

  const requestClose = () => {
    if (!submitting) onOpenChange(false);
  };

  const LeadingIcon = isDomain ? Globe : Building2;

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
        aria-labelledby="add-competitor-title"
        className={cn(
          "border-border relative z-10 w-full max-w-lg rounded-xl border bg-white shadow-lg",
          closing
            ? "animate-out fade-out-0 zoom-out-95 duration-200"
            : "animate-in fade-in-0 zoom-in-95 duration-200",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <h2 id="add-competitor-title" className="text-base font-semibold">
            添加竞争对手
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

        <div className="space-y-1.5 p-5">
          <label htmlFor="add-competitor-input" className="text-foreground text-sm font-medium px-1">
            {isDomain ? "竞争对手域名" : "竞争对手品牌"}
          </label>
          <SetupTextInput
            id="add-competitor-input"
            containerClassName="mt-1"
            leading={<LeadingIcon className="text-muted-foreground size-5" aria-hidden />}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSubmit();
              }
            }}
            disabled={submitting}
            placeholder={isDomain ? "example.com" : "例如：竞品品牌名"}
            autoFocus
          />
          <p className="text-muted-foreground text-xs leading-relaxed px-1">
            {isDomain
              ? "输入您要跟踪的竞争对手的网站域名。"
              : "输入您要跟踪的竞争对手品牌名称。"}
          </p>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4">
          <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
            取消
          </Button>
          <Button type="button" disabled={submitting} onClick={handleSubmit}>
            {submitting ? "添加中…" : "添加竞争对手"}
          </Button>
        </div>
      </div>
    </div>
  );
}
