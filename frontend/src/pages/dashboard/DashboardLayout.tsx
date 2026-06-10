import { Outlet, useLocation } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { AnalysisDimensionTabs } from "@/components/analysis/common/AnalysisDimensionTabs";
import { PromptAnalysisHeader } from "@/components/analysis/prompt/PromptAnalysisHeader";
import { CitationDomainHeader } from "@/components/analysis/citation/CitationDomainHeader";
import { OpportunityTabs } from "@/components/opportunity/OpportunityTabs";
import { SidebarSection } from "@/components/dashboard/SidebarSection";
import { SubjectSwitcher } from "@/components/dashboard/SubjectSwitcher";
import { AppShell } from "@/components/layouts/AppShell";
import { useDashboardSidebar } from "@/hooks/useDashboardSidebar";
import { analysisDimensionFromPathname, citationDomainFromPathname, promptIdFromPathname } from "@/lib/analysis";
import { opportunityTabFromPathname } from "@/lib/opportunity/nav";
import {
  DASHBOARD_NAV_SECTIONS,
  dashboardNavIdFromPath,
  getDashboardNavItem,
} from "@/lib/dashboard";
import { cn } from "@/lib/utils";

/** 控制台布局：侧栏 + 子路由 Outlet。 */
export function DashboardLayout() {
  const { pathname } = useLocation();
  const { collapsed: sidebarCollapsed, toggle: toggleSidebar } = useDashboardSidebar();
  const activeNavId = dashboardNavIdFromPath(pathname);
  const activeNav = getDashboardNavItem(activeNavId);
  const SidebarToggleIcon = sidebarCollapsed ? PanelLeftOpen : PanelLeftClose;
  const isAnalysisPage = activeNav.id === "analysis";
  const isOpportunityPage = activeNav.id === "opportunity";
  const analysisDimension = analysisDimensionFromPathname(pathname);
  const citationDomain = citationDomainFromPathname(pathname);
  const promptDetailId = promptIdFromPathname(pathname);
  const opportunityTab = opportunityTabFromPathname(pathname);

  return (
    <AppShell headerStart={<SubjectSwitcher />}>
      <div className="flex min-h-0 min-w-0 w-full flex-1">
        <aside
          className={cn(
            "bg-app-sidebar flex shrink-0 flex-col pb-3 transition-[width] duration-200 ease-out",
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

          {!sidebarCollapsed ? (
            <div className="border-border/80 mt-3 shrink-0 rounded-lg border bg-white p-3 shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)]">
              <p className="text-foreground text-sm font-medium">正在生成报告…</p>
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                基于您的初始数据生成首份监测报告，完成后将通知您。
              </p>
            </div>
          ) : null}
        </aside>

        <main className="bg-white border-border shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)] flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-lg border">
          <div className="border-border flex h-[48px] min-w-0 shrink-0 items-stretch border-b px-4">
            <div className="flex shrink-0 items-center pr-2">
              <button
                type="button"
                aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
                aria-expanded={!sidebarCollapsed}
                onClick={toggleSidebar}
                className="text-foreground hover:bg-muted/80 -ml-1 flex size-7 items-center justify-center rounded-md transition-colors"
              >
                <SidebarToggleIcon className="size-4" aria-hidden />
              </button>
            </div>
            {isAnalysisPage && citationDomain ? (
              <CitationDomainHeader host={citationDomain} />
            ) : isAnalysisPage && promptDetailId ? (
              <PromptAnalysisHeader promptId={promptDetailId} />
            ) : isAnalysisPage ? (
              <AnalysisDimensionTabs embedded value={analysisDimension} />
            ) : isOpportunityPage ? (
              <OpportunityTabs embedded value={opportunityTab} />
            ) : (
              <div className="flex min-w-0 flex-1 items-center">
                <h1 className="text-base font-semibold">{activeNav.label}</h1>
              </div>
            )}
          </div>
          <div className="flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-x-hidden overflow-y-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </AppShell>
  );
}
