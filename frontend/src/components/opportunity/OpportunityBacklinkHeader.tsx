import { ChevronRight, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { FaviconImage } from "@/components/common/FaviconImage";
import { faviconUrlFromHost } from "@/lib/favicon";
import { opportunityTabPath } from "@/lib/opportunity/nav";

type OpportunityBacklinkHeaderProps = {
  domain: string;
};

export function OpportunityBacklinkHeader({ domain }: OpportunityBacklinkHeaderProps) {
  const externalUrl = domain.startsWith("http") ? domain : `https://${domain}`;

  return (
    <div className="flex h-[48px] min-w-0 flex-1 items-center gap-1.5 text-sm">
      <Link
        to={opportunityTabPath("backlink")}
        className="text-muted-foreground hover:text-foreground shrink-0 font-medium transition-colors"
      >
        返回
      </Link>
      <ChevronRight className="text-muted-foreground size-4 shrink-0" aria-hidden />
      <FaviconImage url={faviconUrlFromHost(domain)} size={20} className="size-5 shrink-0 rounded-sm" />
      <span className="truncate font-semibold" title={domain}>
        {domain}
      </span>
      <a
        href={externalUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-muted-foreground hover:text-foreground ml-0.5 inline-flex shrink-0 items-center rounded-sm transition-colors"
        aria-label={`在新窗口打开 ${domain}`}
      >
        <ExternalLink className="size-3" aria-hidden />
      </a>
    </div>
  );
}
