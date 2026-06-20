import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { faviconUrlFromHost } from "@/lib/favicon";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ContentOpportunityDetailRow } from "@/types";
import { cn } from "@/lib/utils";

type CompetitorSourceUrlsDialogProps = {
  row: ContentOpportunityDetailRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function CopyUrlButton({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      className="text-muted-foreground hover:text-foreground shrink-0 rounded-md p-1 transition-colors"
      aria-label="复制链接"
      onClick={() => void onCopy()}
    >
      {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
    </button>
  );
}

export function CompetitorSourceUrlsDialog({
  row,
  open,
  onOpenChange,
}: CompetitorSourceUrlsDialogProps) {
  if (!row) return null;

  const host = (row.domain ?? row.label).trim().toLowerCase();
  const urls = row.citation_urls ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-w-xl flex-col" aria-labelledby="competitor-source-urls-title">
        <div className="flex items-start justify-between px-6 pt-5 pb-4">
          <DialogTitle id="competitor-source-urls-title" className="text-lg font-semibold">
            来源 URL
          </DialogTitle>
          <DialogClose />
        </div>

        <DialogBody className="flex flex-col gap-4 px-6 pb-6 pt-0">
          <div className="flex min-w-0 items-center gap-2.5">
            <FaviconImage
              url={faviconUrlFromHost(host)}
              size={20}
              className="size-5 shrink-0 rounded-sm"
            />
            <span className="truncate text-sm font-medium text-foreground">{host}</span>
          </div>

          <div className="h-[360px] overflow-y-auto">
            {urls.length === 0 ? (
              <p className="text-muted-foreground flex h-full items-center justify-center text-sm">
                暂无引用链接
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {urls.map((url) => (
                  <li
                    key={url}
                    className="bg-muted flex min-w-0 items-center gap-2 rounded-lg px-3 py-2.5"
                  >
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className={cn(
                        "text-foreground min-w-0 flex-1 truncate text-sm transition-colors",
                        "hover:text-primary hover:underline hover:underline-offset-2",
                      )}
                    >
                      {url}
                    </a>
                    <CopyUrlButton url={url} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
