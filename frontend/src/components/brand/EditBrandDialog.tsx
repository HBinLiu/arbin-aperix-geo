import * as React from "react";
import { X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input, inputControlClass } from "@/components/ui/input";
import { formatApiError } from "@/api/client";
import { patchSubject } from "@/api/subject";
import { clearAnalysisCatalog, clearQueries, queryKeys } from "@/lib/queries";
import { subjectEditAliases, subjectWebsiteUrl } from "@/lib/subject";
import { toast } from "@/lib/toast";
import type { Subject } from "@/types";
import { cn } from "@/lib/utils";

type EditBrandDialogProps = {
  subject: Subject;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="text-foreground text-sm font-medium">
      {children}
      {required ? <span className="text-destructive ml-0.5">*</span> : null}
    </label>
  );
}

function AliasTagsInput({
  aliases,
  onChange,
}: {
  aliases: string[];
  onChange: (next: string[]) => void;
}) {
  const [draft, setDraft] = React.useState("");

  const addAlias = (raw: string) => {
    const value = raw.trim();
    if (!value || aliases.includes(value)) return;
    onChange([...aliases, value]);
    setDraft("");
  };

  const removeAlias = (index: number) => {
    onChange(aliases.filter((_, i) => i !== index));
  };

  return (
    <div
      className={cn(
        inputControlClass,
        "flex min-h-10 flex-wrap items-center gap-1.5 px-2 py-1.5",
      )}
    >
      {aliases.map((alias, index) => (
        <span
          key={`${alias}-${index}`}
          className="border-border bg-muted/60 inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-sm"
        >
          {alias}
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground rounded-sm p-0.5"
            aria-label={`移除别名 ${alias}`}
            onClick={() => removeAlias(index)}
          >
            <X className="size-3" aria-hidden />
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addAlias(draft);
          } else if (e.key === "Backspace" && !draft && aliases.length > 0) {
            removeAlias(aliases.length - 1);
          }
        }}
        onBlur={() => {
          if (draft.trim()) addAlias(draft);
        }}
        placeholder={aliases.length === 0 ? "按 Enter 添加别名" : ""}
        className="placeholder:text-muted-foreground min-w-[8rem] flex-1 border-0 bg-transparent text-sm outline-none"
      />
    </div>
  );
}

export function EditBrandDialog({ subject, open, onOpenChange }: EditBrandDialogProps) {
  const queryClient = useQueryClient();
  const websiteUrl = subjectWebsiteUrl(subject);

  const [brand, setBrand] = React.useState("");
  const [aliases, setAliases] = React.useState<string[]>([]);
  const [summary, setSummary] = React.useState("");
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    setBrand(subject.brand?.trim() ?? "");
    setAliases(subjectEditAliases(subject));
    setSummary(subject.profile_summary.trim());
  }, [open, subject]);

  const onSave = async () => {
    const trimmedBrand = brand.trim();
    if (!trimmedBrand) {
      toast.error("请填写品牌名称。");
      return;
    }

    setSaving(true);
    try {
      await patchSubject(subject.id, {
        brand: trimmedBrand,
        aliases,
        profile_summary: summary.trim(),
      });
      await clearQueries(queryClient, { queryKey: queryKeys.subjects });
      clearAnalysisCatalog(queryClient, subject.id);
      onOpenChange(false);
    } catch (e: unknown) {
      toast.error(formatApiError(e, "保存失败，请重试。"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={saving}>
      <DialogContent
        className="flex max-h-[min(90vh,720px)] max-w-5xl flex-col"
        aria-labelledby="edit-brand-title"
      >
        <div className="border-border flex shrink-0 items-center justify-between border-b px-5 py-4">
          <DialogTitle id="edit-brand-title">编辑品牌详情</DialogTitle>
          <DialogClose />
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <div className="space-y-1.5">
            <FieldLabel>网站</FieldLabel>
            <p className="text-muted-foreground text-sm break-all">
              {websiteUrl ?? "—"}
            </p>
          </div>

          <div className="space-y-1.5">
            <FieldLabel required>品牌</FieldLabel>
            <Input
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder="品牌名称"
              disabled={saving}
            />
          </div>

          <div className="space-y-1.5">
            <FieldLabel>别名</FieldLabel>
            <AliasTagsInput aliases={aliases} onChange={setAliases} />
          </div>

          <div className="space-y-1.5">
            <FieldLabel>摘要</FieldLabel>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              disabled={saving}
              rows={12}
              placeholder="品牌 Markdown 摘要"
              className={cn(inputControlClass, "min-h-[220px] resize-y px-3 py-2 leading-relaxed")}
            />
          </div>
        </div>

        <div className="border-border flex shrink-0 justify-end gap-2 px-5 pb-4">
          <Button type="button" variant="outline" disabled={saving} onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="button" disabled={saving} onClick={() => void onSave()}>
            {saving ? "保存中…" : "保存更改"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
