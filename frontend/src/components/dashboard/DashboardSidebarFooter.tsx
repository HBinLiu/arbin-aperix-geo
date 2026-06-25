// import { BrandReportSidebarCard } from "@/components/dashboard/BrandReportSidebarCard";
// import { SamplingProgressSidebar } from "@/components/dashboard/SamplingProgressSidebar";
import type { SubjectPipelineState } from "@/hooks/useSubjectPipeline";

type DashboardSidebarFooterProps = {
  pipeline: SubjectPipelineState;
};

/** 侧栏底部：报告入口与采样进度（暂时隐藏）。 */
export function DashboardSidebarFooter({ pipeline: _pipeline }: DashboardSidebarFooterProps) {
  return null;

  // return (
  //   <div className="mt-3 shrink-0 space-y-3">
  //     <SamplingProgressSidebar pipeline={pipeline} />
  //     <BrandReportSidebarCard pipeline={pipeline} />
  //   </div>
  // );
}
