import { BrandPage } from "@/pages/dashboard/BrandPage";
import { DashboardPlaceholder } from "@/components/dashboard/DashboardPlaceholder";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { RankContent } from "@/pages/dashboard/RankPage";
import { OverviewContent } from "@/pages/dashboard/OverviewPage";
import { AnalysisPage } from "@/pages/dashboard/AnalysisPage";
import { CitationPage } from "@/pages/analysis/CitationPage";
import { PlatformPage } from "@/pages/analysis/PlatformPage";
import { PromptPage } from "@/pages/analysis/PromptPage";
import { SentimentPage } from "@/pages/analysis/SentimentPage";
import { VisibilityPage } from "@/pages/analysis/VisibilityPage";

export function OverviewRoute() {
  const { subject } = useDashboardContext();
  return <OverviewContent subjectId={subject.id} />;
}

export function BrandRoute() {
  const { subject } = useDashboardContext();
  return <BrandPage subject={subject} />;
}

export function AnalysisRoute() {
  return <AnalysisPage />;
}

export function VisibilityAnalysisRoute() {
  return <VisibilityPage />;
}

export function PromptAnalysisRoute() {
  return <PromptPage />;
}

export function PlatformAnalysisRoute() {
  return <PlatformPage />;
}

export function SentimentAnalysisRoute() {
  return <SentimentPage />;
}

export function CitationAnalysisRoute() {
  return <CitationPage />;
}

export function RankRoute() {
  const { subject } = useDashboardContext();
  return <RankContent subjectId={subject.id} />;
}

export function OpportunitiesRoute() {
  return <DashboardPlaceholder title="机会" />;
}

export function AgentRoute() {
  return <DashboardPlaceholder title="智能体" />;
}
