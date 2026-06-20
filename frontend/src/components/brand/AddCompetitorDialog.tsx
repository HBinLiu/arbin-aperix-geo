import * as React from "react";
import { Building2, Globe } from "lucide-react";

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
import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import { toast } from "@/lib/toast";

type AddCompetitorDialogProps = {
  open: boolean;
  subjectType: string;
  existingValues: string[];
  onOpenChange: (open: boolean) => void;
  onSubmit: (value: string) => void;
  submitting?: boolean;
};

function AddCompetitorDialogFooter({
  submitting,
  onSubmit,
}: {
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
        {submitting ? "添加中…" : "添加竞争对手"}
      </Button>
    </DialogFooter>
  );
}

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

  React.useEffect(() => {
    if (!open) return;
    setValue("");
  }, [open]);

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
      onSubmit(raw);
      return;
    }

    if (existingValues.includes(raw)) {
      toast.error("该竞品品牌已存在。");
      return;
    }

    onSubmit(raw);
  };

  const LeadingIcon = isDomain ? Globe : Building2;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby="add-competitor-title">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id="add-competitor-title">添加竞争对手</DialogTitle>
          <DialogClose />
        </div>

        <div className="space-y-1.5 p-5">
          <label htmlFor="add-competitor-input" className="text-foreground px-1 text-sm font-medium">
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
          <p className="text-muted-foreground px-1 text-xs leading-relaxed">
            {isDomain
              ? "输入您要跟踪的竞争对手的网站域名。"
              : "输入您要跟踪的竞争对手品牌名称。"}
          </p>
        </div>

        <AddCompetitorDialogFooter submitting={submitting} onSubmit={handleSubmit} />
      </DialogContent>
    </Dialog>
  );
}
