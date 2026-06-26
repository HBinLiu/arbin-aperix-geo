import * as React from "react";
import { Globe, X } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogTitle,
  useDialog,
} from "@/components/ui/dialog";
import { Input, InputGroup, inputControlClass } from "@/components/ui/input";
import type { CompetitorItem } from "@/types";
import { hostnameFromWebsiteInput, registrableDomain, websiteUrlFromInput } from "@/lib/domain";
import { faviconUrlFromWebsite } from "@/lib/favicon";
import { cn } from "@/lib/utils";
import { toast } from "@/lib/toast";

type EditCompetitorDialogProps = {
  open: boolean;
  subjectType: string;
  competitor: CompetitorItem | null;
  existingValues: string[];
  onOpenChange: (open: boolean) => void;
  onSubmit: (item: Omit<CompetitorItem, "id">) => void;
  submitting?: boolean;
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
  disabled,
}: {
  aliases: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
}) {
  const [draft, setDraft] = React.useState("");

  const addAlias = (raw: string) => {
    const value = raw.trim();
    if (!value || aliases.includes(value)) return;
    onChange([...aliases, value]);
    setDraft("");
  };

  return (
    <div
      className={cn(
        inputControlClass,
        "flex min-h-10 flex-wrap items-center gap-1.5 px-2 py-1.5",
        disabled && "opacity-60",
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
            disabled={disabled}
            onClick={() => onChange(aliases.filter((_, i) => i !== index))}
          >
            <X className="size-3" aria-hidden />
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        disabled={disabled}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addAlias(draft);
          } else if (e.key === "Backspace" && !draft && aliases.length > 0) {
            onChange(aliases.slice(0, -1));
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

function EditCompetitorDialogFooter({
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
        {submitting ? "保存中…" : "保存更改"}
      </Button>
    </DialogFooter>
  );
}

export function EditCompetitorDialog({
  open,
  subjectType,
  competitor,
  existingValues,
  onOpenChange,
  onSubmit,
  submitting = false,
}: EditCompetitorDialogProps) {
  const isDomain = subjectType === "domain";
  const [domainInput, setDomainInput] = React.useState("");
  const [brand, setBrand] = React.useState("");
  const [aliases, setAliases] = React.useState<string[]>([]);
  const [summary, setSummary] = React.useState("");

  const domainFaviconUrl = React.useMemo(() => {
    const raw = domainInput.trim();
    if (!raw) return null;
    const domain = registrableDomain(hostnameFromWebsiteInput(raw) || raw);
    if (!domain) return null;
    const websiteUrl = websiteUrlFromInput(raw) || `https://${domain}/`;
    return faviconUrlFromWebsite(websiteUrl, domain);
  }, [domainInput]);

  React.useEffect(() => {
    if (!open || !competitor) return;
    setDomainInput(competitor.domain.trim() || competitor.website_url.trim());
    setBrand(competitor.brand.trim());
    setAliases([...(competitor.aliases ?? [])]);
    setSummary(competitor.summary.trim());
  }, [open, competitor]);

  const handleSubmit = () => {
    if (!competitor) return;

    const trimmedBrand = brand.trim();
    if (!trimmedBrand) {
      toast.error(isDomain ? "请填写品牌名称。" : "请填写竞品品牌。");
      return;
    }

    if (isDomain) {
      const raw = domainInput.trim();
      if (!raw) {
        toast.error("请填写竞争对手域名。");
        return;
      }
      const domain = registrableDomain(hostnameFromWebsiteInput(raw) || raw);
      if (!domain || domain.length < 3) {
        toast.error("请填写有效的网站域名。");
        return;
      }
      const currentDomain = competitor.domain.trim();
      if (domain !== currentDomain && existingValues.includes(domain)) {
        toast.error("该竞品域名已存在。");
        return;
      }
      const website_url =
        domain === currentDomain
          ? competitor.website_url
          : websiteUrlFromInput(raw) || `https://${domain}/`;

      onSubmit({
        domain,
        website_url,
        brand: trimmedBrand,
        aliases,
        summary: summary.trim(),
      });
      return;
    }

    const currentBrand = competitor.brand.trim();
    if (
      trimmedBrand !== currentBrand &&
      existingValues.some((value) => value.toLowerCase() === trimmedBrand.toLowerCase())
    ) {
      toast.error("该竞品品牌已存在。");
      return;
    }

    onSubmit({
      domain: "",
      website_url: "",
      brand: trimmedBrand,
      aliases,
      summary: summary.trim(),
    });
  };

  if (!competitor) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-lg" aria-labelledby="edit-competitor-title">
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <DialogTitle id="edit-competitor-title">编辑竞争对手</DialogTitle>
          <DialogClose />
        </div>

        <div className="space-y-4 p-5">
          {isDomain ? (
            <div className="space-y-1.5">
              <FieldLabel required>竞品网站</FieldLabel>
              <InputGroup className="h-9">
                <div className="relative min-w-0 flex-1">
                  <div className="pointer-events-none absolute top-1/2 left-2.5 z-10 flex -translate-y-1/2 items-center">
                    {domainFaviconUrl ? (
                      <FaviconImage url={domainFaviconUrl} size={20} iconClassName="size-5" />
                    ) : (
                      <Globe className="text-muted-foreground size-5 shrink-0" aria-hidden />
                    )}
                  </div>
                  <Input
                    variant="merged"
                    controlSize="sm"
                    value={domainInput}
                    onChange={(e) => setDomainInput(e.target.value)}
                    disabled={submitting}
                    placeholder="example.com"
                    className="w-full pl-10"
                    autoFocus
                  />
                </div>
              </InputGroup>
            </div>
          ) : null}

          <div className="space-y-1.5">
            <FieldLabel required>{isDomain ? "品牌名称" : "竞品品牌"}</FieldLabel>
            <Input
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              disabled={submitting}
              placeholder={isDomain ? "展示用品牌名" : "竞品品牌名"}
              autoFocus={!isDomain}
            />
          </div>

          <div className="space-y-1.5">
            <FieldLabel>别名</FieldLabel>
            <AliasTagsInput aliases={aliases} onChange={setAliases} disabled={submitting} />
          </div>

          <div className="space-y-1.5">
            <FieldLabel>摘要</FieldLabel>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              disabled={submitting}
              rows={4}
              placeholder="可选：竞品简介或备注"
              className={cn(inputControlClass, "min-h-[96px] resize-y px-3 py-2 leading-relaxed")}
            />
          </div>
        </div>

        <EditCompetitorDialogFooter submitting={submitting} onSubmit={handleSubmit} />
      </DialogContent>
    </Dialog>
  );
}
