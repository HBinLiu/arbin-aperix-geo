import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { DashboardLayout } from "@/pages/dashboard/DashboardLayout";
import { DashboardRoot } from "@/pages/dashboard/DashboardRoot";
import {
  AgentRoute,
  AnalysisCitationRoute,
  AnalysisCitationDomainRoute,
  AnalysisPlatformRoute,
  AnalysisPromptRoute,
  AnalysisPromptDetailRoute,
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
} from "@/routes/dashboard";
import { SetupRoute } from "@/routes/setup";
import { AboutPage } from "@/pages/website/AboutPage";
import { HomePage } from "@/pages/website/HomePage";
import { DASHBOARD_APP_BASE } from "@/lib/dashboard";

/**
 * 应用路由表
 *
 * 公开：/、/about、/auth/*
 * 控制台：/app/*（RequireAuth → setup / 控制台子路由）
 */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
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
            <Route path="analysis" element={<AnalysisRoute />}>
              <Route index element={<Navigate to="visibility" replace />} />
              <Route path="visibility" element={<AnalysisVisibilityRoute />} />
              <Route path="prompt/:promptId" element={<AnalysisPromptDetailRoute />} />
              <Route path="prompt" element={<AnalysisPromptRoute />} />
              <Route path="platform" element={<AnalysisPlatformRoute />} />
              <Route path="sentiment" element={<AnalysisSentimentRoute />} />
              <Route path="citation" element={<AnalysisCitationRoute />} />
              <Route path="citation/:host" element={<AnalysisCitationDomainRoute />} />
              <Route path="*" element={<Navigate to="visibility" replace />} />
            </Route>
            <Route path="rank" element={<RankRoute />} />
            <Route path="opportunity">
              <Route index element={<Navigate to="backlink" replace />} />
              <Route path="backlink/:host" element={<OpportunityBacklinkDetailRoute />} />
              <Route path=":tab" element={<OpportunityRoute />} />
            </Route>
            <Route path="agent" element={<AgentRoute />} />
            <Route path="diagnosis">
              <Route index element={<DiagnosisRoute />} />
              <Route path=":promptId" element={<DiagnosisContentDetailRoute />} />
            </Route>
            <Route path="prompt" element={<PromptRoute />} />
            <Route path="brand" element={<BrandRoute />} />
            <Route path="*" element={<Navigate to={DASHBOARD_APP_BASE} replace />} />
          </Route>
        </Route>
      </Route>
      <Route path="/about" element={<AboutPage />} />
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<RegisterPage />} />
    </Routes>
  );
}
