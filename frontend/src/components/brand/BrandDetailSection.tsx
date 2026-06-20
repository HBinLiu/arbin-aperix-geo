import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Copy, ExternalLink, Pencil, Plus, Tag } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import { EditBrandDialog } from "@/components/brand/EditBrandDialog";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Button } from "@/components/ui/button";
import { DASHBOARD_SETUP_PATH } from "@/lib/dashboard";
import { clearSetupCache } from "@/lib/setup";
import {
  subjectDisplayLabel,
  subjectEditAliases,
  subjectFaviconUrl,
  subjectWebsiteUrl,
} from "@/lib/subject";
import type { Subject } from "@/types";
import { cn } from "@/lib/utils";

type BrandDetailSectionProps = {
  subject: Subject;
};

function BrandSummary({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="text-muted-foreground space-y-2 text-sm leading-relaxed">
      {lines.map((line, index) => {
        const trimmed = line.trimEnd();
        if (trimmed.startsWith("# ")) {
          return (
            <h3 key={index} className="text-foreground pt-1 text-base font-semibold">
              {trimmed.slice(2)}
            </h3>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h4 key={index} className="text-foreground pt-1 text-sm font-semibold">
              {trimmed.slice(3)}
            </h4>
          );
        }
        if (trimmed.startsWith("* ") || trimmed.startsWith("- ")) {
          return (
            <p key={index} className="pl-1">
              {trimmed.replace(/^[*-]\s+/, "• ")}
            </p>
          );
        }
        if (!trimmed.trim()) {
          return <div key={index} className="h-1" aria-hidden />;
        }
        return <p key={index}>{trimmed}</p>;
      })}
    </div>
  );
}

function CopyIdButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <button
      type="button"
      onClick={() => void onCopy()}
      className="text-muted-foreground hover:text-foreground rounded p-0.5 transition-colors"
      aria-label={copied ? "已复制" : "复制 ID"}
    >
      {copied ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
    </button>
  );
}

function DetailField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="border-border min-w-0 space-y-1 rounded-lg border bg-white px-3 py-2.5">
      <p className="text-muted-foreground text-xs font-medium">{label}</p>
      <div className="text-muted-foreground text-sm font-medium">{children}</div>
    </div>
  );
}

export function BrandDetailSection({ subject }: BrandDetailSectionProps) {
  const navigate = useNavigate();
  const [editOpen, setEditOpen] = useState(false);
  const displayName = subjectDisplayLabel(subject);
  const faviconUrl = subjectFaviconUrl(subject);
  const brandName = subject.brand.trim();
  const aliases = subjectEditAliases(subject);
  const websiteUrl = subjectWebsiteUrl(subject);
  const summary = subject.profile_summary?.trim() ?? "";

  return (
    <>
      <BrandSectionCard
        title="品牌详情"
        description="定义您的品牌以跟踪相关性能指标。"
        actionLabel="创建新项目"
        actionIcon={<Plus className="size-4" aria-hidden />}
        actionVariant="default"
        onAction={() => {
          clearSetupCache();
          navigate(DASHBOARD_SETUP_PATH);
        }}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className="border-border flex size-11 shrink-0 items-center justify-center rounded-md border bg-white p-1.5">
              {faviconUrl ? (
                <FaviconImage
                  url={faviconUrl}
                  size={32}
                  className="size-8"
                  iconClassName="size-4"
                />
              ) : (
                <span className="text-muted-foreground text-base font-semibold">
                  {displayName.slice(0, 1).toUpperCase()}
                </span>
              )}
            </div>
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold tracking-tight sm:text-xl">{displayName}</p>
              <div className="text-muted-foreground mt-0.5 flex min-w-0 items-center gap-1 text-xs">
                <span className="truncate font-mono">{subject.id}</span>
                <CopyIdButton value={subject.id} />
              </div>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            className="shrink-0 gap-1.5"
            onClick={() => setEditOpen(true)}
          >
            <Pencil className="size-4" aria-hidden />
            编辑
          </Button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <DetailField label="品牌">{brandName || "—"}</DetailField>
          <DetailField label="别名">
            {aliases.length > 0 ? (
              <span className="inline-flex min-w-0 flex-wrap items-center gap-1.5">
                {aliases.map((item) => (
                  <span
                    key={item}
                    className="bg-muted text-muted-foreground inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm"
                  >
                    <Tag className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
                    <span>{item}</span>
                  </span>
                ))}
              </span>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </DetailField>
          <DetailField label="网站">
            {websiteUrl ? (
              <a
                href={websiteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground inline-flex min-w-0 max-w-full items-center gap-1 hover:text-primary hover:underline"
              >
                <span className="truncate">{websiteUrl}</span>
                <ExternalLink className="size-3.5 shrink-0" aria-hidden />
              </a>
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </DetailField>
        </div>

        <div className="border-border mt-4 space-y-1 rounded-lg border bg-white px-3 py-2.5">
          <p className="text-muted-foreground text-xs font-medium">摘要</p>
          <div className="h-40 overflow-y-auto pr-1 sm:h-44">
            {summary ? (
              <BrandSummary text={summary} />
            ) : (
              <p className={cn("text-muted-foreground text-sm leading-relaxed")}>
                暂无品牌摘要。完成设置向导或编辑品牌信息后可在此展示说明文案。
              </p>
            )}
          </div>
        </div>
      </BrandSectionCard>

      <EditBrandDialog subject={subject} open={editOpen} onOpenChange={setEditOpen} />
    </>
  );
}
