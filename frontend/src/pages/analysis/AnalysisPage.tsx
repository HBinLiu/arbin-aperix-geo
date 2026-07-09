import { Outlet } from "react-router-dom";

import { useDashboardContext } from "@/hooks/useDashboardContext";
import type { AnalysisOutletContext } from "@/types";

/** 分析模块布局：仅提供 subjectId，各子页自行拉数与空态。 */
export function AnalysisPage() {
  const { subject } = useDashboardContext();

  const outletContext: AnalysisOutletContext = {
    subjectId: subject.id,
  };

  return <Outlet context={outletContext} />;
}
