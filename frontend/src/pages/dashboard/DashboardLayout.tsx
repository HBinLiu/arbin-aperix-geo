import { Outlet, useLocation } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { AnalysisDimensionTabs } from "@/components/analysis/common/AnalysisDimensionTabs";
import { PromptAnalysisHeader } from "@/components/analysis/prompt/PromptAnalysisHeader";
import { CitationDomainHeader } from "@/components/analysis/citation/CitationDomainHeader";
import { OpportunityBacklinkHeader } from "@/components/opportunity/OpportunityBacklinkHeader";
import { DiagnosisContentHeader } from "@/components/diagnosis/DiagnosisContentHeader";
import { OpportunityTabs } from "@/components/opportunity/OpportunityTabs";
import { BillingTabs } from "@/components/billing/BillingTabs";
import { DashboardSidebarFooter } from "@/components/dashboard/DashboardSidebarFooter";
import { SidebarSection } from "@/components/dashboard/SidebarSection";
import { SubjectSwitcher } from "@/components/dashboard/SubjectSwitcher";
import { AppShell } from "@/components/layouts/AppShell";
import { useDashboardSidebar } from "@/hooks/useDashboardSidebar";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useSamplingCompletionToast } from "@/hooks/useSamplingCompletionToast";
import { useQuotaWarningToast } from "@/hooks/useQuotaWarningToast";
import { SubjectPipelineProvider } from "@/hooks/SubjectPipelineProvider";
import { useSubjectPipeline } from "@/hooks/useSubjectPipeline";
import { AnalysisFiltersProvider } from "@/hooks/useAnalysisFiltersState";
import { analysisDimensionFromPathname, citationDomainFromPathname, promptIdFromPathname } from "@/lib/analysis";
import { opportunityTabFromPathname, backlinkOpportunityDomainFromPathname } from "@/lib/opportunity/nav";
import { billingTabFromPathname } from "@/lib/billing/nav";
import { diagnosisContentPromptIdFromPathname } from "@/lib/diagnosis/nav";
import {
  DASHBOARD_NAV_SECTIONS,
  dashboardNavIdFromPath,
  getDashboardNavItem,
} from "@/lib/dashboard";
import { cn } from "@/lib/utils";

/** 控制台布局：侧栏 + 子路由 Outlet。 */
export function DashboardLayout() {
  const { subject } = useDashboardContext();
  return (
    <SubjectPipelineProvider subjectId={subject.id}>
      <DashboardLayoutContent />
    </SubjectPipelineProvider>
  );
}

function DashboardLayoutContent() {
  const { pathname } = useLocation();
  const pipeline = useSubjectPipeline();
  useSamplingCompletionToast();
  useQuotaWarningToast();
  const { collapsed: sidebarCollapsed, toggle: toggleSidebar } = useDashboardSidebar();
  const activeNavId = dashboardNavIdFromPath(pathname);
  const activeNav = getDashboardNavItem(activeNavId);
  const SidebarToggleIcon = sidebarCollapsed ? PanelLeftOpen : PanelLeftClose;
  const isAnalysisPage = activeNav.id === "analysis";
  const isOpportunityPage = activeNav.id === "opportunity";
  const isBillingPage = activeNav.id === "billing";
  const isDiagnosisPage = activeNav.id === "diagnosis";
  const analysisDimension = analysisDimensionFromPathname(pathname);
  const citationDomain = citationDomainFromPathname(pathname);
  const promptDetailId = promptIdFromPathname(pathname);
  const opportunityTab = opportunityTabFromPathname(pathname);
  const billingTab = billingTabFromPathname(pathname);
  const diagnosisContentPromptId = diagnosisContentPromptIdFromPathname(pathname);
  const backlinkOpportunityDomain = backlinkOpportunityDomainFromPathname(pathname);

  return (
    <AppShell headerStart={<SubjectSwitcher />}>
      <div className="flex min-h-0 min-w-0 w-full flex-1">
        <aside
          className={cn(
            "bg-background flex shrink-0 flex-col pb-3 transition-[width] duration-200 ease-out",
            sidebarCollapsed ? "w-14 pr-2.5 pt-4" : "w-60 pr-2.5 pt-4",
          )}
        >
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overflow-x-hidden">
            {DASHBOARD_NAV_SECTIONS.map((section) => (
              <SidebarSection
                key={section.title}
                title={section.title}
                items={section.items}
                collapsed={sidebarCollapsed}
              />
            ))}
          </div>

          {!sidebarCollapsed ? <DashboardSidebarFooter pipeline={pipeline} /> : null}
        </aside>

        <main className="bg-muted-background border-border shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)] flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg border">
          <div className="border-border flex h-[48px] min-w-0 shrink-0 items-stretch border-b px-4">
            <div className="flex shrink-0 items-center pr-2">
              <button
                type="button"
                aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
                aria-expanded={!sidebarCollapsed}
                onClick={toggleSidebar}
                className="text-foreground hover:bg-background/80 -ml-1 flex size-7 items-center justify-center rounded-md transition-colors"
              >
                <SidebarToggleIcon className="size-4" aria-hidden />
              </button>
            </div>
            {isAnalysisPage && citationDomain ? (
              <CitationDomainHeader domain={citationDomain} />
            ) : isAnalysisPage && promptDetailId ? (
              <PromptAnalysisHeader promptId={promptDetailId} />
            ) : isAnalysisPage ? (
              <AnalysisDimensionTabs embedded value={analysisDimension} />
            ) : isOpportunityPage && backlinkOpportunityDomain ? (
              <OpportunityBacklinkHeader domain={backlinkOpportunityDomain} />
            ) : isOpportunityPage ? (
              <OpportunityTabs embedded value={opportunityTab} />
            ) : isBillingPage ? (
              <BillingTabs embedded value={billingTab} />
            ) : isDiagnosisPage && diagnosisContentPromptId ? (
              <DiagnosisContentHeader promptId={diagnosisContentPromptId} />
            ) : (
              <div className="flex min-w-0 flex-1 items-center">
                <h1 className="text-base font-semibold">{activeNav.label}</h1>
              </div>
            )}
          </div>
          <div className="flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-x-hidden overflow-y-auto">
            <AnalysisFiltersProvider>
              <Outlet />
            </AnalysisFiltersProvider>
          </div>
        </main>
      </div>
    </AppShell>
  );
}
