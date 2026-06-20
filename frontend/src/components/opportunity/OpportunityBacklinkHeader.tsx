import { ChevronRight, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { FaviconImage } from "@/components/common/FaviconImage";
import { faviconUrlFromHost } from "@/lib/favicon";
import { opportunityTabPath } from "@/lib/opportunity/nav";

type OpportunityBacklinkHeaderProps = {
  host: string;
};

/** 反向链接机会详情 · 顶栏：返回 + 域名 */
export function OpportunityBacklinkHeader({ host }: OpportunityBacklinkHeaderProps) {
  const externalUrl = host.startsWith("http") ? host : `https://${host}`;

  return (
    <div className="flex h-[48px] min-w-0 flex-1 items-center gap-1.5 overflow-hidden text-sm">
      <Link
        to={opportunityTabPath("backlink")}
        className="text-muted-foreground hover:text-foreground shrink-0 font-medium transition-colors"
      >
        返回
      </Link>
      <ChevronRight className="text-muted-foreground size-4 shrink-0" aria-hidden />
      <FaviconImage url={faviconUrlFromHost(host)} size={20} className="size-5 shrink-0 rounded-sm" />
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
