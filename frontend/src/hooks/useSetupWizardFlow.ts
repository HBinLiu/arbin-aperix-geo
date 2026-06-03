import * as React from "react";

import {
  discoverCompetitors,
  discoverProfile,
  finalizeSetup,
  generateSetupPrompts,
} from "@/api/setup";
import { hostnameFromWebsiteInput } from "@/lib/domain";
import { setPendingJobId } from "@/lib/sampling";
import {
  clearSetupCache,
  defaultSetupCache,
  loadSetupCache,
  rowsToPersist,
  saveSetupCache,
  selectedPromptRows,
  selectedTopicNames,
  selectedTopicRows,
  setupStepHeader,
} from "@/lib/setup";
import { toast } from "@/lib/toast";
import type { CompetitorRow, PromptRow, SubjectMode, TopicRow } from "@/types";

type UseSetupWizardFlowOptions = {
  onCompleted: (subjectId: string) => void;
};

export function useSetupWizardFlow({ onCompleted }: UseSetupWizardFlowOptions) {
  const initial = React.useMemo(() => loadSetupCache() ?? defaultSetupCache(), []);

  const [step, setStep] = React.useState(initial.step);
  const [mode, setMode] = React.useState<SubjectMode>(initial.mode);
  const [websiteUrl, setWebsiteUrl] = React.useState(initial.websiteUrl);
  const [brandName, setBrandName] = React.useState(initial.brandName);
  const [region, setRegion] = React.useState(initial.region);
  const [language, setLanguage] = React.useState(initial.language);
  const [sessionId, setSessionId] = React.useState(initial.sessionId);
  const [competitorRows, setCompetitorRows] = React.useState<CompetitorRow[]>(initial.competitorRows);
  const [topicRows, setTopicRows] = React.useState<TopicRow[]>(initial.topicRows ?? []);
  const [promptRows, setPromptRows] = React.useState<PromptRow[]>(initial.promptRows ?? []);
  const [submitting, setSubmitting] = React.useState(false);
  const [analyzingProfile, setAnalyzingProfile] = React.useState(false);
  const [discoveringCompetitors, setDiscoveringCompetitors] = React.useState(false);
  const [generatingPrompts, setGeneratingPrompts] = React.useState(false);

  const setupLabel = mode === "domain" ? "网站设置" : "品牌设置";
  const stepLabels = [setupLabel, "审查主题", "选择竞品", "确认提示词"];
  const busy = analyzingProfile || discoveringCompetitors || generatingPrompts;

  const hostPreview = hostnameFromWebsiteInput(websiteUrl);
  const faviconHost = hostPreview && hostPreview.includes(".") ? hostPreview : null;
  const activeTopics = React.useMemo(() => selectedTopicRows(topicRows), [topicRows]);

  React.useEffect(() => {
    saveSetupCache({
      sessionId,
      mode,
      websiteUrl,
      brandName,
      region,
      language,
      topicRows,
      competitorRows,
      promptRows,
      step,
    });
  }, [sessionId, mode, websiteUrl, brandName, region, language, topicRows, competitorRows, promptRows, step]);

  const resetDownstream = (fromStep: number) => {
    if (fromStep <= 0) {
      setSessionId("");
      setTopicRows([]);
      setCompetitorRows([]);
      setPromptRows([]);
      return;
    }
    if (fromStep <= 1) {
      setCompetitorRows([]);
      setPromptRows([]);
      return;
    }
    if (fromStep <= 2) {
      setPromptRows([]);
    }
  };

  const validateStep0 = (): boolean => {
    if (mode === "domain") {
      if (!hostPreview || hostPreview.length < 3) {
        toast.error("请填写有效的网站URL。");
        return false;
      }
    } else if (!brandName.trim()) {
      toast.error("请填写品牌名称。");
      return false;
    }
    return true;
  };

  const validateStep1 = (): boolean => {
    const names = selectedTopicNames(topicRows);
    if (names.length < 1) {
      toast.error("请至少选择一个主题。");
      return false;
    }
    if (names.length !== new Set(names).size) {
      toast.error("主题名称不能重复。");
      return false;
    }
    if (!sessionId) {
      toast.error("会话已失效，请返回上一步重新分析。");
      return false;
    }
    return true;
  };

  const validateStep2 = (): boolean => {
    const { competitors, brand_names } = rowsToPersist(mode, competitorRows);
    if (mode === "domain" && competitors.length < 1) {
      toast.error("请至少选择一个竞品域名。");
      return false;
    }
    if (mode === "brand" && brand_names.length < 1) {
      toast.error("按品牌监测时，请至少选择一个竞品品牌。");
      return false;
    }
    return true;
  };

  const validateStep3 = (): boolean => {
    if (selectedPromptRows(promptRows).length < 1) {
      toast.error("请至少选择一条提示词。");
      return false;
    }
    return true;
  };

  const runDiscoverProfile = async () => {
    setAnalyzingProfile(true);
    setStep(1);
    resetDownstream(0);
    try {
      const result = await discoverProfile({
        mode,
        domain: mode === "domain" ? (hostPreview ?? "") : "",
        brand: mode === "brand" ? brandName.trim() : "",
        region,
        language,
      });
      setSessionId(result.sessionId);
      setTopicRows(result.topicRows);
    } catch {
      setStep(0);
    } finally {
      setAnalyzingProfile(false);
    }
  };

  const runDiscoverCompetitors = async () => {
    if (!sessionId) return;
    setDiscoveringCompetitors(true);
    setStep(2);
    resetDownstream(1);
    try {
      const result = await discoverCompetitors({
        mode,
        sessionId,
        microKeywords: selectedTopicNames(topicRows),
      });
      setCompetitorRows(result.competitorRows);
      if (result.topicRows) {
        setTopicRows(result.topicRows);
      }
      if (result.competitorRows.length === 0) {
        toast.info(
          mode === "domain"
            ? "未发现符合条件的竞品，请手动添加域名。"
            : "未发现符合条件的竞品品牌，请手动添加。",
        );
      }
    } catch {
      setStep(1);
    } finally {
      setDiscoveringCompetitors(false);
    }
  };

  const runGeneratePrompts = async () => {
    if (!sessionId) return;
    setGeneratingPrompts(true);
    setStep(3);
    resetDownstream(2);
    const { competitors, brand_names } = rowsToPersist(mode, competitorRows);
    const competitorLabels = mode === "domain" ? competitors.map((c) => c.domain) : brand_names;
    try {
      const rows = await generateSetupPrompts({
        sessionId,
        topics: activeTopics,
        competitorLabels,
      });
      setPromptRows(rows);
    } catch {
      setStep(2);
    } finally {
      setGeneratingPrompts(false);
    }
  };

  const runFinalize = async () => {
    setSubmitting(true);
    try {
      const { subject, samplingJobId } = await finalizeSetup({
        mode,
        sessionId,
        domain: mode === "domain" ? (hostPreview ?? "") : "",
        brand: mode === "brand" ? brandName.trim() : "",
        region,
        language,
        topicRows,
        competitorRows,
        promptRows,
      });
      clearSetupCache();
      setPendingJobId(subject.id, samplingJobId);
      onCompleted(subject.id);
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinue = () => {
    if (step === 0) {
      if (!validateStep0()) return;
      void runDiscoverProfile();
      return;
    }
    if (step === 1) {
      if (!validateStep1()) return;
      void runDiscoverCompetitors();
      return;
    }
    if (step === 2) {
      if (!validateStep2()) return;
      void runGeneratePrompts();
      return;
    }
    if (step === 3) {
      if (!validateStep3()) return;
      void runFinalize();
    }
  };

  const handleBack = () => {
    if (busy) return;
    if (step === 0) return;
    if (step === 1) {
      setSessionId("");
      setTopicRows([]);
    }
    if (step === 2) {
      setCompetitorRows([]);
    }
    setStep((s) => Math.max(0, s - 1));
  };

  const shellHeader = setupStepHeader(step, {
    analyzingProfile,
    discoveringCompetitors,
    generatingPrompts,
  });

  return {
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
    analyzingProfile,
    discoveringCompetitors,
    generatingPrompts,
    setupLabel,
    stepLabels,
    busy,
    faviconHost,
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
  };
}
