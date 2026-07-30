import { Link } from "react-router-dom";
import { Clock3 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SAMPLING_BLOCKED_MESSAGE } from "@/lib/dashboard/nav-lock";

/** 采样未完成时拦截洞察 / 运营页面的提示。 */
export function SamplingBlockedNotice() {
  return (
    <div className="flex min-h-[20rem] flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <div className="bg-background flex size-12 items-center justify-center rounded-full">
        <Clock3 className="text-muted-foreground size-6" aria-hidden />
      </div>
      <div className="max-w-sm space-y-1">
        <p className="text-foreground text-sm font-medium">{SAMPLING_BLOCKED_MESSAGE}</p>
        <p className="text-muted-foreground text-xs">
          品牌分析任务完成后，即可查看具体内容。
        </p>
      </div>
      <Button variant="outline" size="sm" asChild>
        <Link to="/">返回概述</Link>
      </Button>
    </div>
  );
}
