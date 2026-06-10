import * as React from "react";
import { Globe } from "lucide-react";

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

function FaviconPlaceholder({
  size,
  className,
  iconClassName,
}: Pick<FaviconImageProps, "size" | "className" | "iconClassName">) {
  return (
    <Globe
      className={cn("text-muted-foreground shrink-0", iconClassName ?? "size-5")}
      style={size ? { width: size, height: size } : undefined}
      aria-hidden
    />
  );
}

/**
 * 站点图标：domain 可为 URL / www / 子域名 / 主域名（内部 normalize 为 eTLD+1）。
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
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    setIndex(0);
  }, [cacheKey, candidates.join("|")]);

  if (!host || getFaviconClientStatus(domain, pageUrl) === "miss") {
    return <FaviconPlaceholder size={size} className={className} iconClassName={iconClassName} />;
  }

  if (candidates.length === 0 || index >= candidates.length) {
    return <FaviconPlaceholder size={size} className={className} iconClassName={iconClassName} />;
  }

  return (
    <img
      src={candidates[index]}
      alt=""
      width={size}
      height={size}
      className={cn("shrink-0 rounded-sm object-contain", className)}
      style={{ width: size, height: size }}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onLoad={() => markFaviconClientOk(domain, pageUrl)}
      onError={() => {
        const next = index + 1;
        if (next >= candidates.length) {
          markFaviconClientMiss(domain, pageUrl);
        }
        setIndex(next);
      }}
    />
  );
}
