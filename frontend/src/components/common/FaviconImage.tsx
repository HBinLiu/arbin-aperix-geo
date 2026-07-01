import * as React from "react";
import { Globe, Loader2 } from "lucide-react";

import {
  faviconCacheKey,
  faviconCandidateUrls,
  getFaviconClientStatus,
  markFaviconClientMiss,
  markFaviconClientOk,
  resolveFaviconInput,
} from "@/lib/favicon";
import { cn } from "@/lib/utils";

type FaviconImageProps = {
  /** 网站 URL 或可解析为 URL 的输入（不用裸传 domain）。 */
  url: string;
  size?: number;
  className?: string;
  iconClassName?: string;
  /** 加载中是否显示转圈（筛选项等紧凑场景建议关闭，避免路由切换闪烁） */
  showLoadingSpinner?: boolean;
  /** 输入框等场景立即加载，避免 lazy + opacity-0 导致不发起请求 */
  eager?: boolean;
};

type DisplayState = "loading" | "loaded" | "fallback";

function resolveInitialState(url: string, candidates: string[]): DisplayState {
  if (!resolveFaviconInput(url) || candidates.length === 0) return "fallback";
  const status = getFaviconClientStatus(url);
  if (status === "miss") return "fallback";
  if (status === "ok") return "loaded";
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
 * 站点图标：按输入 URL 请求 favicon API（``?url=``）。
 * 加载中显示转圈；成功显示 favicon；API 204/失败时回退 Globe。
 */
export function FaviconImage({
  url,
  size = 20,
  className,
  iconClassName,
  showLoadingSpinner = true,
  eager = false,
}: FaviconImageProps) {
  const cacheKey = React.useMemo(() => faviconCacheKey(url), [url]);
  const candidates = React.useMemo(() => faviconCandidateUrls(url), [url]);
  const candidatesKey = candidates.join("|");

  const [index, setIndex] = React.useState(0);
  const [display, setDisplay] = React.useState<DisplayState>(() =>
    resolveInitialState(url, candidates),
  );

  React.useEffect(() => {
    setIndex(0);
    setDisplay(resolveInitialState(url, candidates));
  }, [cacheKey, candidatesKey, url, candidates]);

  const src = candidates[index] ?? null;

  const handleError = React.useCallback(() => {
    setIndex((current) => {
      const next = current + 1;
      if (next >= candidates.length) {
        markFaviconClientMiss(url);
        setDisplay("fallback");
        return current;
      }
      return next;
    });
  }, [candidates.length, url]);

  const handleLoad = React.useCallback(() => {
    markFaviconClientOk(url);
    setDisplay("loaded");
  }, [url]);

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
      {display === "loading" && showLoadingSpinner ? (
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
        loading={eager ? "eager" : "lazy"}
        decoding="async"
        referrerPolicy="no-referrer"
        onLoad={handleLoad}
        onError={handleError}
      />
    </IconShell>
  );
}
