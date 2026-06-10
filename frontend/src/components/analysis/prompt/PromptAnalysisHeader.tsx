import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PromptIntentBadge } from "@/components/analysis/prompt/PromptIntentBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { usePromptDetailMeta } from "@/hooks/usePromptDetailAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { analysisDimensionPath } from "@/lib/analysis";

type PromptAnalysisHeaderProps = {
  promptId: string;
};

/** 提示词详情页 · 顶栏：返回 + 提示词 + 主题 + 意图 */
export function PromptAnalysisHeader({ promptId }: PromptAnalysisHeaderProps) {
  const { subject } = useDashboardContext();
  const { isLoading, promptText, topicName, intent } = usePromptDetailMeta(subject.id, promptId);

  return (
    <div className="flex h-[48px] min-w-0 flex-1 items-center gap-1.5 overflow-hidden text-sm">
      <Link
        to={analysisDimensionPath("prompt")}
        className="text-muted-foreground hover:text-foreground shrink-0 font-medium transition-colors"
      >
        返回
      </Link>
      <ChevronRight className="text-muted-foreground size-4 shrink-0" aria-hidden />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-0 overflow-hidden">
        <div className="flex min-w-0 items-center gap-1.5 leading-4">
          {isLoading ? (
            <Skeleton className="h-3.5 w-48 max-w-full" />
          ) : (
            <>
              <span className="truncate text-sm font-semibold" title={promptText}>
                {promptText || "提示词详情"}
              </span>
              {intent ? <PromptIntentBadge intent={intent} /> : null}
            </>
          )}
        </div>
        {!isLoading && topicName ? (
          <p className="text-muted-foreground truncate text-[11px] leading-4">主题：{topicName}</p>
        ) : null}
      </div>
    </div>
  );
}
