import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { InsightOpsGate } from "@/components/dashboard/InsightOpsGate";
import { LoginPage } from "@/pages/auth/LoginPage";
import { DashboardLayout } from "@/pages/dashboard/DashboardLayout";
import { DashboardRoot } from "@/pages/dashboard/DashboardRoot";
import {
  AgentRoute,
  KnowledgeRoute,
  AnalysisCitationRoute,
  AnalysisCitationDomainRoute,
  AnalysisPlatformRoute,
  AnalysisPromptRoute,
  AnalysisPromptDetailRoute,
  AnalysisFanoutRoute,
  AnalysisRoute,
  AnalysisSentimentRoute,
  AnalysisVisibilityRoute,
  BrandRoute,
  DiagnosisRoute,
  DiagnosisContentDetailRoute,
  OpportunityRoute,
  OpportunityBacklinkDetailRoute,
  OverviewRoute,
  PromptRoute,
  RankRoute,
  ProfileRoute,
  BillingRoute,
} from "@/routes/dashboard";
import { SetupRoute } from "@/routes/setup";
import { DASHBOARD_APP_BASE } from "@/lib/dashboard";

/**
 * 应用路由表
 *
 * 公开：/auth/*（官网 /、/about 由 Astro website/ 提供）
 * 控制台：/app/*（RequireAuth → setup / 控制台子路由）
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/auth/login" replace />} />
      <Route
        path={`${DASHBOARD_APP_BASE}/*`}
        element={
          <RequireAuth>
            <Outlet />
          </RequireAuth>
        }
      >
        <Route path="setup" element={<SetupRoute />} />
        <Route element={<DashboardRoot />}>
          <Route element={<DashboardLayout />}>
            <Route index element={<OverviewRoute />} />
            <Route element={<InsightOpsGate />}>
              <Route path="analysis" element={<AnalysisRoute />}>
                <Route index element={<Navigate to="visibility" replace />} />
                <Route path="visibility" element={<AnalysisVisibilityRoute />} />
                <Route path="prompt/:promptId" element={<AnalysisPromptDetailRoute />} />
                <Route path="prompt" element={<AnalysisPromptRoute />} />
                <Route path="fanout" element={<AnalysisFanoutRoute />} />
                <Route path="platform" element={<AnalysisPlatformRoute />} />
                <Route path="sentiment" element={<AnalysisSentimentRoute />} />
                <Route path="citation" element={<AnalysisCitationRoute />} />
                <Route path="citation/:domain" element={<AnalysisCitationDomainRoute />} />
                <Route path="*" element={<Navigate to="visibility" replace />} />
              </Route>
              <Route path="rank" element={<RankRoute />} />
              <Route path="diagnosis">
                <Route index element={<DiagnosisRoute />} />
                <Route path=":promptId" element={<DiagnosisContentDetailRoute />} />
              </Route>
              <Route path="opportunity">
                <Route index element={<Navigate to="backlink" replace />} />
                <Route path="backlink/:domain" element={<OpportunityBacklinkDetailRoute />} />
                <Route path=":tab" element={<OpportunityRoute />} />
              </Route>
              <Route path="knowledge" element={<KnowledgeRoute />} />
              <Route path="agent" element={<AgentRoute />} />
            </Route>
            <Route path="prompt" element={<PromptRoute />} />
            <Route path="brand" element={<BrandRoute />} />
            <Route path="profile">
              <Route index element={<Navigate to="account" replace />} />
              <Route path=":tab" element={<ProfileRoute />} />
            </Route>
            <Route path="billing">
              <Route index element={<Navigate to="plan" replace />} />
              <Route path=":tab" element={<BillingRoute />} />
            </Route>
            <Route path="*" element={<Navigate to={DASHBOARD_APP_BASE} replace />} />
          </Route>
        </Route>
      </Route>
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<Navigate to="/auth/login" replace />} />
      <Route path="/auth/forgot-password" element={<Navigate to="/auth/login" replace />} />
    </Routes>
  );
}
