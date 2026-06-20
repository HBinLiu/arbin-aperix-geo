import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { Skeleton } from "@/components/ui/skeleton";
import { usePromptDetailMeta } from "@/hooks/usePromptDetailAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { opportunityTabPath } from "@/lib/opportunity/nav";

type OpportunityContentHeaderProps = {
  promptId: string;
};

/** 内容机会详情 · 顶栏：返回 + 提示词 */
export function OpportunityContentHeader({ promptId }: OpportunityContentHeaderProps) {
  const { subject } = useDashboardContext();
  const { isLoading, promptText } = usePromptDetailMeta(subject.id, promptId);

  return (
    <div className="flex h-[48px] min-w-0 flex-1 items-center gap-1.5 overflow-hidden text-sm">
      <Link
        to={opportunityTabPath("content")}
        className="text-muted-foreground hover:text-foreground shrink-0 font-medium transition-colors"
      >
        返回
      </Link>
      <ChevronRight className="text-muted-foreground size-4 shrink-0" aria-hidden />
      {isLoading ? (
        <Skeleton className="h-4 w-48 max-w-full" />
      ) : (
        <span className="truncate font-semibold" title={promptText}>
          {promptText || "内容机会详情"}
        </span>
      )}
    </div>
  );
}
