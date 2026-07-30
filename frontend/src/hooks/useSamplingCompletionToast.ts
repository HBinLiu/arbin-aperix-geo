import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useSubjectPipeline } from "@/hooks/useSubjectPipeline";
import { dashboardNavToPath } from "@/lib/dashboard";
import { toast } from "@/lib/toast";

/** 首份采样完成后站内通知，并引导回概述页。 */
export function useSamplingCompletionToast() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { isComplete, isRunning } = useSubjectPipeline();
  const initializedRef = useRef(false);
  const sawRunningRef = useRef(false);
  const wasCompleteRef = useRef(false);

  useEffect(() => {
    if (isRunning) {
      sawRunningRef.current = true;
    }
  }, [isRunning]);

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      wasCompleteRef.current = isComplete;
      return;
    }

    if (sawRunningRef.current && !wasCompleteRef.current && isComplete) {
      toast.success("品牌分析已完成，概述数据已就绪。");
      wasCompleteRef.current = true;

      const onOverview = pathname === "/" || pathname === "";
      if (!onOverview) {
        navigate(dashboardNavToPath("overview"), { replace: true });
      }
      return;
    }

    wasCompleteRef.current = isComplete;
  }, [isComplete, navigate, pathname]);
}
