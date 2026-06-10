import { ChevronRight, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { FaviconImage } from "@/components/common/FaviconImage";
import { analysisDimensionPath } from "@/lib/analysis";

type CitationDomainHeaderProps = {
  host: string;
};

export function CitationDomainHeader({ host }: CitationDomainHeaderProps) {
  const externalUrl = host.startsWith("http") ? host : `https://${host}`;

  return (
    <div className="flex h-[48px] min-w-0 flex-1 items-center gap-1.5 text-sm">
      <Link
        to={analysisDimensionPath("citation")}
        className="text-muted-foreground hover:text-foreground shrink-0 font-medium transition-colors"
      >
        返回
      </Link>
      <ChevronRight className="text-muted-foreground size-4 shrink-0" aria-hidden />
      <FaviconImage domain={host} size={20} className="size-5 shrink-0 rounded-sm" />
      <span className="truncate font-semibold" title={host}>
        {host}
      </span>
      <a
        href={externalUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-muted-foreground hover:text-foreground ml-0.5 inline-flex shrink-0 items-center rounded-sm transition-colors"
        aria-label={`在新窗口打开 ${host}`}
      >
        <ExternalLink className="size-3" aria-hidden />
      </a>
    </div>
  );
}
