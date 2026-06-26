import type { FormEvent } from "react";

import { AppShell } from "@/components/layouts/AppShell";
import { SetupStepFooter } from "@/components/setup/SetupStepFooter";
import { SetupStepVertical } from "@/components/setup/SetupStepVertical";
import { SetupStepContent } from "@/components/setup/SetupStepContent";
import { useSetupWizardFlow } from "@/hooks/useSetupWizardFlow";
import { SETUP_LANGUAGES, SETUP_REGIONS } from "@/lib/setup";

type SetupWizardProps = {
  onCompleted: (subjectId: string) => void;
};

type SetupWizardHeaderProps = {
  title?: string;
  subtitle?: string;
};

function SetupWizardHeader({ title, subtitle }: SetupWizardHeaderProps) {
  return (
    <div className="shrink-0 space-y-2 text-left">
      <h1 className="text-[24px] font-semibold leading-tight text-foreground">{title ?? "欢迎！让我们开始吧"}</h1>
      <p className="text-muted-foreground text-sm">{subtitle ?? "告诉我们您的新计划以开始使用"}</p>
    </div>
  );
}

/** 设置 → 选择竞品 → 审查主题 → 确认提示词；后端 4 个 API。 */
export function SetupWizard({ onCompleted }: SetupWizardProps) {
  const {
    step,
    mode,
    websiteUrl,
    brandName,
    region,
    language,
    topicRows,
    competitorRows,
    promptRows,
    submitting,
    discovering,
    loadingTopics,
    generatingPrompts,
    stepLabels,
    verticalStep,
    busy,
    activeTopics,
    shellHeader,
    setMode,
    setWebsiteUrl,
    setBrandName,
    setRegion,
    setLanguage,
    setTopicRows,
    setCompetitorRows,
    setPromptRows,
    handleContinue,
    handleBack,
  } = useSetupWizardFlow({ onCompleted });

  const regionOptions = SETUP_REGIONS.map((r) => ({ value: r.value, label: r.label, flag: r.flag }));
  const languageOptions = SETUP_LANGUAGES.map((l) => ({ value: l.value, label: l.label, flag: l.flag }));
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    handleContinue();
  };
  const stepContentView = {
    step,
    mode,
    websiteUrl,
    brandName,
    region,
    language,
    topicRows,
    competitorRows,
    promptRows,
    activeTopics,
    regionOptions,
    languageOptions,
    analyzingProfile: discovering,
    discoveringCompetitors: discovering || loadingTopics,
    generatingPrompts,
  };
  const stepContentActions = {
    onModeChange: setMode,
    onWebsiteUrlChange: setWebsiteUrl,
    onBrandNameChange: setBrandName,
    onRegionChange: setRegion,
    onLanguageChange: setLanguage,
    onTopicRowsChange: setTopicRows,
    onCompetitorRowsChange: setCompetitorRows,
    onPromptRowsChange: setPromptRows,
  };

  return (
    <AppShell>
      <section className="bg-muted-background border-border shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)] flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border">
        <div className="mx-auto flex h-full min-h-0 w-full max-w-[calc(40px+60rem)] flex-1 flex-col overflow-auto px-6 pb-10 pt-6">
          <div className="my-auto grid w-full min-h-[min(669px,calc(100vh-8rem))] grid-cols-1 rounded-lg border shadow-[10px_12px_28px_-14px_rgba(15,23,42,0.22)] md:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="flex min-h-0 flex-col p-6 md:p-8 lg:p-10">
              <form className="flex h-full min-h-0 w-full flex-col" onSubmit={handleSubmit}>
                <SetupWizardHeader title={shellHeader?.title} subtitle={shellHeader?.subtitle} />

                <div className="mt-10 min-h-0 flex-1 space-y-4 overflow-y-auto px-0.5">
                  <SetupStepContent view={stepContentView} actions={stepContentActions} />
                </div>

                <SetupStepFooter
                  step={step}
                  busy={busy}
                  submitting={submitting}
                  onBack={handleBack}
                />
              </form>
            </div>

            <aside
              className="setup-panel-bg relative m-2 hidden min-h-[260px] min-w-0 overflow-hidden rounded-md md:flex md:self-stretch"
              aria-label="设置流程"
            >
              <div className="relative z-10 flex h-full w-full items-center p-10">
                <SetupStepVertical steps={stepLabels} currentStep={verticalStep} />
              </div>
            </aside>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
