import * as React from "react";
import { Globe, Loader2 } from "lucide-react";

import {
  faviconCacheKey,
  faviconCandidateUrls,
  getFaviconClientStatus,
  markFaviconClientMiss,
  markFaviconClientOk,
  normalizeFaviconDomain,
} from "@/lib/favicon";
import { cn } from "@/lib/utils";

type FaviconImageProps = {
  domain: string;
  pageUrl?: string | null;
  size?: number;
  className?: string;
  iconClassName?: string;
};

type DisplayState = "loading" | "loaded" | "fallback";

function resolveInitialState(
  domain: string,
  pageUrl: string | null | undefined,
  host: string,
  candidates: string[],
): DisplayState {
  if (!host || candidates.length === 0) return "fallback";
  if (getFaviconClientStatus(domain, pageUrl) === "miss") return "fallback";
  return "loading";
}

function IconShell({
  size,
  className,
  children,
}: {
  size: number;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn("relative inline-flex shrink-0 items-center justify-center", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {children}
    </span>
  );
}

function FaviconFallback({
  size,
  iconClassName,
}: Pick<FaviconImageProps, "size" | "iconClassName">) {
  return (
    <Globe
      className={cn("text-muted-foreground shrink-0", iconClassName ?? "size-5")}
      style={size ? { width: size, height: size } : undefined}
      aria-hidden
    />
  );
}

function FaviconSpinner({
  size,
  iconClassName,
}: Pick<FaviconImageProps, "size" | "iconClassName">) {
  return (
    <Loader2
      className={cn("text-muted-foreground shrink-0 animate-spin", iconClassName ?? "size-5")}
      style={size ? { width: size, height: size } : undefined}
      aria-hidden
    />
  );
}

/**
 * 站点图标：domain 可为 URL / www / 子域名 / 主域名（内部 normalize 为 eTLD+1）。
 * 加载中显示转圈；成功显示 favicon；API 204/失败时 onError 回退 Globe（超时由后端 resolve 控制）。
 */
export function FaviconImage({
  domain,
  pageUrl,
  size = 20,
  className,
  iconClassName,
}: FaviconImageProps) {
  const host = React.useMemo(() => normalizeFaviconDomain(domain), [domain]);
  const cacheKey = React.useMemo(() => faviconCacheKey(domain, pageUrl), [domain, pageUrl]);
  const candidates = React.useMemo(
    () => faviconCandidateUrls(domain, pageUrl),
    [domain, pageUrl],
  );
  const candidatesKey = candidates.join("|");

  const [index, setIndex] = React.useState(0);
  const [display, setDisplay] = React.useState<DisplayState>(() =>
    resolveInitialState(domain, pageUrl, host, candidates),
  );

  React.useEffect(() => {
    setIndex(0);
    setDisplay(resolveInitialState(domain, pageUrl, host, candidates));
  }, [cacheKey, candidatesKey, domain, pageUrl, host]);

  const src = candidates[index] ?? null;

  const handleError = React.useCallback(() => {
    setIndex((current) => {
      const next = current + 1;
      if (next >= candidates.length) {
        markFaviconClientMiss(domain, pageUrl);
        setDisplay("fallback");
        return current;
      }
      return next;
    });
  }, [candidates.length, domain, pageUrl]);

  const handleLoad = React.useCallback(() => {
    markFaviconClientOk(domain, pageUrl);
    setDisplay("loaded");
  }, [domain, pageUrl]);

  if (display === "fallback") {
    return (
      <IconShell size={size} className={className}>
        <FaviconFallback size={size} iconClassName={iconClassName} />
      </IconShell>
    );
  }

  if (!src) {
    return (
      <IconShell size={size} className={className}>
        <FaviconFallback size={size} iconClassName={iconClassName} />
      </IconShell>
    );
  }

  return (
    <IconShell size={size} className={className}>
      {display === "loading" ? (
        <FaviconSpinner size={size} iconClassName={iconClassName} />
      ) : null}
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        className={cn(
          "rounded-sm object-contain",
          display === "loading" && "pointer-events-none absolute opacity-0",
        )}
        style={{ width: size, height: size }}
        loading="lazy"
        decoding="async"
        referrerPolicy="no-referrer"
        onLoad={handleLoad}
        onError={handleError}
      />
    </IconShell>
  );
}
