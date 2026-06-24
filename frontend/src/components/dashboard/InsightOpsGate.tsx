import { Outlet } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { SamplingBlockedNotice } from "@/components/dashboard/SamplingBlockedNotice";
import { useSubjectPipeline } from "@/hooks/useSubjectPipeline";
import { isInsightOpsLocked } from "@/lib/dashboard/nav-lock";

/** 采样进行中拦截洞察 / 运营子路由。 */
export function InsightOpsGate() {
  const pipeline = useSubjectPipeline();

  if (pipeline.isLoading) {
    return (
      <div className="flex min-h-[16rem] flex-1 items-center justify-center">
        <Loader2 className="text-muted-foreground size-5 animate-spin" aria-label="加载中" />
      </div>
    );
  }

  if (isInsightOpsLocked(pipeline)) {
    return <SamplingBlockedNotice />;
  }

  return <Outlet />;
}
