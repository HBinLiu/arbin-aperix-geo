import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { DashboardLayout } from "@/pages/dashboard/DashboardLayout";
import { DashboardRoot } from "@/pages/dashboard/DashboardRoot";
import {
  AgentRoute,
  AnalysisRoute,
  BrandRoute,
  CitationAnalysisRoute,
  PlatformAnalysisRoute,
  PromptAnalysisRoute,
  RankRoute,
  OpportunitiesRoute,
  OverviewRoute,
  SentimentAnalysisRoute,
  VisibilityAnalysisRoute,
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
              <Route path="visibility" element={<VisibilityAnalysisRoute />} />
              <Route path="prompt" element={<PromptAnalysisRoute />} />
              <Route path="platform" element={<PlatformAnalysisRoute />} />
              <Route path="sentiment" element={<SentimentAnalysisRoute />} />
              <Route path="citation" element={<CitationAnalysisRoute />} />
              <Route path="*" element={<Navigate to="visibility" replace />} />
            </Route>
            <Route path="rank" element={<RankRoute />} />
            <Route path="opportunities" element={<OpportunitiesRoute />} />
            <Route path="agent" element={<AgentRoute />} />
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
