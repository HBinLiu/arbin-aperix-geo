import * as React from "react";
import { Globe } from "lucide-react";

import { faviconCandidateUrls } from "@/lib/favicon";
import { cn } from "@/lib/utils";

type FaviconImageProps = {
  domain: string;
  size?: number;
  className?: string;
  iconClassName?: string;
};

/**
 * 站点图标：domain 可为 URL / www / 子域名 / 主域名（内部 normalize 为 eTLD+1）。
 */
export function FaviconImage({
  domain,
  size = 20,
  className,
  iconClassName,
}: FaviconImageProps) {
  const candidates = React.useMemo(() => faviconCandidateUrls(domain), [domain]);
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    setIndex(0);
  }, [domain, candidates.join("|")]);

  if (candidates.length === 0 || index >= candidates.length) {
    return (
      <Globe
        className={cn("text-muted-foreground shrink-0", iconClassName ?? "size-5")}
        style={size ? { width: size, height: size } : undefined}
        aria-hidden
      />
    );
  }

  return (
    <img
      src={candidates[index]}
      alt=""
      width={size}
      height={size}
      className={cn("shrink-0 rounded-sm object-contain", className)}
      style={{ width: size, height: size }}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setIndex((i) => i + 1)}
    />
  );
}
