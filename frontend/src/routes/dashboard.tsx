import { DashboardPlaceholder } from "@/components/dashboard/DashboardPlaceholder";
import { DiagnosisContent } from "@/pages/dashboard/DiagnosisPage";
import { PromptContent } from "@/pages/dashboard/PromptPage";
import { BrandPage } from "@/pages/dashboard/BrandPage";
import { OpportunityContent } from "@/pages/dashboard/OpportunityPage";
import { ContentDetailPage } from "@/pages/diagnosis/ContentDetailPage";
import { BacklinkDetailPage } from "@/pages/opportunity/BacklinkDetailPage";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { RankContent } from "@/pages/dashboard/RankPage";
import { OverviewContent } from "@/pages/dashboard/OverviewPage";
import { AnalysisPage } from "@/pages/dashboard/AnalysisPage";
import { CitationPage } from "@/pages/analysis/CitationPage";
import { CitationDomainPage } from "@/pages/analysis/CitationDomainPage";
import { PlatformPage } from "@/pages/analysis/PlatformPage";
import { PromptPage } from "@/pages/analysis/PromptPage";
import { PromptDetailPage } from "@/pages/analysis/PromptDetailPage";
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

export function AnalysisVisibilityRoute() {
  return <VisibilityPage />;
}

export function AnalysisPromptRoute() {
  return <PromptPage />;
}

export function AnalysisPromptDetailRoute() {
  return <PromptDetailPage />;
}

export function AnalysisPlatformRoute() {
  return <PlatformPage />;
}

export function AnalysisSentimentRoute() {
  return <SentimentPage />;
}

export function AnalysisCitationRoute() {
  return <CitationPage />;
}

export function AnalysisCitationDomainRoute() {
  return <CitationDomainPage />;
}

export function RankRoute() {
  const { subject } = useDashboardContext();
  return <RankContent subjectId={subject.id} />;
}

export function DiagnosisContentDetailRoute() {
  const { subject } = useDashboardContext();
  return <ContentDetailPage subjectId={subject.id} />;
}

export function OpportunityBacklinkDetailRoute() {
  const { subject } = useDashboardContext();
  return <BacklinkDetailPage subjectId={subject.id} />;
}

export function OpportunityRoute() {
  const { subject } = useDashboardContext();
  return <OpportunityContent subjectId={subject.id} />;
}

export function AgentRoute() {
  return <DashboardPlaceholder title="智能体" />;
}

export function DiagnosisRoute() {
  const { subject } = useDashboardContext();
  return <DiagnosisContent subjectId={subject.id} />;
}

export function PromptRoute() {
  return <PromptContent />;
}
