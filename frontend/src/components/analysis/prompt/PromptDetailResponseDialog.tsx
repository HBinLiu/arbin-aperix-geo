import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Copy, UserRound } from "lucide-react";

import { fetchLlmResponse } from "@/api/responses";
import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { FaviconImage } from "@/components/common/FaviconImage";
import {
  Dialog,
  DialogClose,
  DialogContent,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { HighlightedReplyContent } from "@/components/analysis/prompt/HighlightedReplyContent";
import {
  responseMentionedBrandTerms,
  responseMentionBrands,
  responseSources,
} from "@/lib/analysis/responseDetail";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { LlmResponseDialogRow, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type PromptDetailResponseDialogProps = {
  row: LlmResponseDialogRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promptText: string;
  platformsMeta: SamplingPlatform[];
};

function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("已复制到剪贴板");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("复制失败");
    }
  };

  return (
    <button
      type="button"
      onClick={() => void onCopy()}
      className={cn(
        "border-border text-foreground inline-flex shrink-0 items-center gap-1 rounded-md border bg-white px-2.5 py-1.5 text-xs leading-none transition-colors",
        className,
      )}
    >
      {copied ? <Check className="size-3.5" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
      复制
    </button>
  );
}

function UserPromptAvatar() {
  return (
    <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-foreground">
      <UserRound className="size-5" strokeWidth={2} aria-hidden />
    </span>
  );
}

function UserPromptMessage({ text }: { text: string }) {
  return (
    <div className="flex w-full items-start justify-end gap-2.5">
      <p className="bg-muted max-w-[85%] rounded-lg px-3 py-2 text-left text-sm leading-6 whitespace-pre-wrap">
        {text.trim() || "—"}
      </p>
      <UserPromptAvatar />
    </div>
  );
}

function ChatMessageRow({
  avatar,
  children,
}: {
  avatar: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex w-full items-start justify-start gap-2.5 text-left">
      <div className="shrink-0 pt-0.5">{avatar}</div>
      <div className="min-w-0 flex-1 text-left">{children}</div>
    </div>
  );
}

const SCROLL_FADE_SIZE = "h-5";
const SCROLL_FADE_THRESHOLD = 2;

function SidebarSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showTopFade, setShowTopFade] = useState(false);
  const [showBottomFade, setShowBottomFade] = useState(false);

  const updateScrollFades = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;

    const { scrollTop, scrollHeight, clientHeight } = el;
    const canScroll = scrollHeight - clientHeight > SCROLL_FADE_THRESHOLD;

    setShowTopFade(scrollTop > SCROLL_FADE_THRESHOLD);
    setShowBottomFade(canScroll && scrollTop + clientHeight < scrollHeight - SCROLL_FADE_THRESHOLD);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    updateScrollFades();
    el.addEventListener("scroll", updateScrollFades, { passive: true });

    const observer = new ResizeObserver(updateScrollFades);
    observer.observe(el);

    return () => {
      el.removeEventListener("scroll", updateScrollFades);
      observer.disconnect();
    };
  }, [updateScrollFades, children]);

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-2">
      <h3 className="shrink-0 text-xs font-semibold">{title}</h3>
      <div className="relative min-h-0 flex-1">
        <div
          ref={scrollRef}
          className="h-full overflow-y-auto overscroll-contain pr-1"
        >
          {children}
        </div>
        <div
          className={cn(
            "pointer-events-none absolute inset-x-0 top-0 bg-gradient-to-b from-white from-40% via-white/70 to-transparent backdrop-blur-[1px] transition-opacity duration-200",
            SCROLL_FADE_SIZE,
            showTopFade ? "opacity-100" : "opacity-0",
          )}
          aria-hidden
        />
        <div
          className={cn(
            "pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-white from-40% via-white/70 to-transparent backdrop-blur-[1px] transition-opacity duration-200",
            SCROLL_FADE_SIZE,
            showBottomFade ? "opacity-100" : "opacity-0",
          )}
          aria-hidden
        />
      </div>
    </section>
  );
}

export function PromptDetailResponseDialog({
  row,
  open,
  onOpenChange,
  promptText,
  platformsMeta,
}: PromptDetailResponseDialogProps) {
  const responseId = row?.response_id ?? "";

  const detailQuery = useQuery({
    queryKey: queryKeys.llmResponse(responseId),
    queryFn: () => fetchLlmResponse(responseId),
    enabled: open && !!responseId,
  });

  const platformMeta = resolvePlatformMeta(row?.platform ?? "", platformsMeta);
  const parsed = detailQuery.data?.parsed ?? null;
  const rawText = detailQuery.data?.raw_text ?? row?.reply_preview ?? "";

  const mentionBrands = useMemo(() => responseMentionBrands(parsed), [parsed]);
  const sources = useMemo(() => responseSources(parsed), [parsed]);
  const mentionTerms = useMemo(() => responseMentionedBrandTerms(parsed), [parsed]);

  if (!row) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[82vh] max-w-5xl flex-col overflow-hidden rounded-xl p-0 [--tw-enter-scale:1] [--tw-exit-scale:1]"
        aria-labelledby="prompt-detail-response-dialog-title"
      >
        <div className="border-border flex shrink-0 items-center justify-between gap-3 border-b px-5 py-4">
          <div className="flex h-8 min-w-0 flex-1 items-center gap-2.5">
            <PlatformLogo
              provider={row.platform}
              label={platformMeta.label}
              className="block size-8 shrink-0 rounded-md"
            />
            <p
              id="prompt-detail-response-dialog-title"
              className="min-w-0 truncate text-sm leading-none font-semibold"
            >
              {platformMeta.label}
            </p>
            <CopyButton text={rawText} />
          </div>

          <DialogClose className="shrink-0" />
        </div>

        <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,7fr)_minmax(240px,3fr)]">
          <div className="min-h-0 overflow-y-auto px-5 py-4">
            {detailQuery.isLoading ? (
              <div className="space-y-6 text-left">
                <div className="flex items-start justify-end gap-2.5">
                  <Skeleton className="h-10 w-4/5 max-w-sm rounded-lg" />
                  <Skeleton className="size-10 shrink-0 rounded-full" />
                </div>
                <div className="flex gap-2.5">
                  <Skeleton className="size-7 shrink-0 rounded-md" />
                  <div className="flex-1 space-y-2">
                    {Array.from({ length: 6 }).map((_, index) => (
                      <Skeleton key={index} className="h-4 w-full" />
                    ))}
                  </div>
                </div>
              </div>
            ) : detailQuery.isError ? (
              <p className="text-muted-foreground text-sm">加载回复详情失败，请稍后重试。</p>
            ) : (
              <div className="space-y-6 text-left">
                <UserPromptMessage text={promptText} />

                <ChatMessageRow
                  avatar={
                    <PlatformLogo
                      provider={row.platform}
                      label={platformMeta.label}
                      className="size-7 rounded-md"
                    />
                  }
                >
                  {rawText.trim() ? (
                    <HighlightedReplyContent text={rawText} parsed={parsed} mentionTerms={mentionTerms} />
                  ) : (
                    <p className="text-muted-foreground text-sm">暂无回复正文</p>
                  )}
                </ChatMessageRow>
              </div>
            )}
          </div>

          <aside className="border-border flex min-h-0 flex-col gap-4 border-t px-4 py-4 lg:border-t-0 lg:border-l">
            <SidebarSection title="提及品牌">
              {detailQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-8 w-full" />
                  ))}
                </div>
              ) : mentionBrands.length === 0 ? (
                <p className="text-muted-foreground text-sm">暂无提及品牌</p>
              ) : (
                <ul className="space-y-2">
                  {mentionBrands.map((item) => (
                    <li key={item.label} className="flex items-center gap-2 rounded-md py-1">
                      <BrandRankIcon label={item.iconLabel} size="sm" />
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.label}</span>
                      <span className="inline-flex items-center gap-1.5 text-sm font-semibold tabular-nums">
                        <span className="bg-orange-500 size-2 shrink-0 rounded-full" aria-hidden />
                        {item.scoreLabel}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </SidebarSection>

            <SidebarSection title="来源">
              {detailQuery.isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <Skeleton key={index} className="h-10 w-full" />
                  ))}
                </div>
              ) : sources.length === 0 ? (
                <p className="text-muted-foreground text-sm">暂无来源</p>
              ) : (
                <ol className="space-y-3">
                  {sources.map((source, index) => (
                    <li key={source.url} className="flex gap-2">
                      <span className="text-muted-foreground mt-0.5 w-4 shrink-0 text-xs tabular-nums">
                        {index + 1}
                      </span>
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <FaviconImage
                            domain={source.host}
                            pageUrl={source.url}
                            size={16}
                            className="size-4 shrink-0 rounded-sm"
                          />
                          <span className="truncate text-sm font-medium">{source.host}</span>
                        </div>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-muted-foreground mt-0.5 block truncate text-xs underline underline-offset-2"
                        >
                          {source.url}
                        </a>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </SidebarSection>

            <SidebarSection title="查询扩展">
              <p className="text-muted-foreground text-sm">未找到查询扩展</p>
            </SidebarSection>
          </aside>
        </div>
      </DialogContent>
    </Dialog>
  );
}
