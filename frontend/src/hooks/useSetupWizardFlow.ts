import * as React from "react";

import { discoverSetup, finalizeSetup, generateSetupPrompts, generateSetupTopics } from "@/api/setup";
import { hostnameFromWebsiteInput } from "@/lib/domain";
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
  setupVerticalStep,
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
  const [topicRows, setTopicRows] = React.useState<TopicRow[]>(initial.topicRows);
  const [competitorRows, setCompetitorRows] = React.useState<CompetitorRow[]>(initial.competitorRows);
  const [promptRows, setPromptRows] = React.useState<PromptRow[]>(initial.promptRows);
  const [submitting, setSubmitting] = React.useState(false);
  const [discovering, setDiscovering] = React.useState(false);
  const [loadingTopics, setLoadingTopics] = React.useState(false);
  const [generatingPrompts, setGeneratingPrompts] = React.useState(false);

  const setupLabel = mode === "domain" ? "网站设置" : "品牌设置";
  const stepLabels = [setupLabel, "选择竞品", "审查主题", "确认提示词"];
  const busy = discovering || loadingTopics || generatingPrompts || submitting;

  const hostPreview = hostnameFromWebsiteInput(websiteUrl);
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
  }, [
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
  ]);

  const resetDownstream = (fromStep: number) => {
    if (fromStep <= 0) {
      setTopicRows([]);
      setCompetitorRows([]);
      setPromptRows([]);
      return;
    }
    if (fromStep <= 1) {
      setTopicRows([]);
      setPromptRows([]);
      return;
    }
    if (fromStep <= 2) {
      setPromptRows([]);
    }
  };

  const clearSession = () => {
    setSessionId("");
    resetDownstream(0);
  };

  const setModeAndReset = (nextMode: SubjectMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);
    clearSession();
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
    const { competitors } = rowsToPersist(mode, competitorRows);
    if (mode === "domain" && competitors.filter((c) => c.domain).length < 1) {
      toast.error("请至少选择一个竞品域名。");
      return false;
    }
    if (mode === "brand" && competitors.filter((c) => c.brand && !c.domain).length < 1) {
      toast.error("按品牌监测时，请至少选择一个竞品品牌。");
      return false;
    }
    return true;
  };

  const validateStep2 = (): boolean => {
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

  const validateStep3 = (): boolean => {
    if (selectedPromptRows(promptRows).length < 1) {
      toast.error("请至少选择一条提示词。");
      return false;
    }
    return true;
  };

  const runDiscover = async () => {
    setDiscovering(true);
    setStep(1);
    resetDownstream(0);
    try {
      const result = await discoverSetup({
        mode,
        domain: mode === "domain" ? websiteUrl.trim() : "",
        brand: mode === "brand" ? brandName.trim() : "",
        region,
        language,
        sessionId: sessionId || undefined,
      });
      setSessionId(result.sessionId);
      setCompetitorRows(result.competitorRows);
      if (result.competitorRows.length === 0) {
        toast.info(
          mode === "domain"
            ? "未发现符合条件的竞品，请手动添加域名。"
            : "未发现符合条件的竞品品牌，请手动添加。",
        );
      }
    } catch {
      setStep(0);
    } finally {
      setDiscovering(false);
    }
  };

  const runLoadTopics = async () => {
    if (!sessionId) return;
    setLoadingTopics(true);
    resetDownstream(2);
    try {
      const { topicRows: rows } = await generateSetupTopics({
        sessionId,
        mode,
        competitorRows,
      });
      setTopicRows(rows);
      setStep(2);
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setLoadingTopics(false);
    }
  };

  const runGeneratePrompts = async () => {
    if (!sessionId) return;
    setGeneratingPrompts(true);
    const excludePrompts = selectedPromptRows(promptRows).map((row) => row.text);
    resetDownstream(2);
    try {
      const rows = await generateSetupPrompts({
        sessionId,
        topics: activeTopics,
        excludePrompts,
      });
      setPromptRows(rows);
      setStep(3);
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setGeneratingPrompts(false);
    }
  };

  const runFinalize = async () => {
    setSubmitting(true);
    try {
      const { subjectId } = await finalizeSetup({
        sessionId,
        topicRows,
        promptRows,
      });
      clearSetupCache();
      onCompleted(subjectId);
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinue = () => {
    if (step === 0) {
      if (!validateStep0()) return;
      void runDiscover();
      return;
    }
    if (step === 1) {
      if (!validateStep1()) return;
      void runLoadTopics();
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
      setCompetitorRows([]);
      setTopicRows([]);
      setPromptRows([]);
    }
    setStep((s) => Math.max(0, s - 1));
  };

  const handleRegionChange = (value: string) => {
    if (value !== region) {
      setRegion(value);
      clearSession();
    }
  };

  const handleLanguageChange = (value: string) => {
    if (value !== language) {
      setLanguage(value);
      clearSession();
    }
  };

  const handleWebsiteUrlChange = (value: string) => {
    setWebsiteUrl(value);
    if (sessionId) clearSession();
  };

  const handleBrandNameChange = (value: string) => {
    setBrandName(value);
    if (sessionId) clearSession();
  };

  const shellHeader = setupStepHeader(step, {
    discovering,
    loadingTopics,
    generatingPrompts,
  });

  const verticalStep = setupVerticalStep(step, {
    discovering,
    loadingTopics,
    generatingPrompts,
  });


  return {
    step,
    verticalStep,
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
    setupLabel,
    stepLabels,
    busy,
    activeTopics,
    shellHeader,
    setMode: setModeAndReset,
    setWebsiteUrl: handleWebsiteUrlChange,
    setBrandName: handleBrandNameChange,
    setRegion: handleRegionChange,
    setLanguage: handleLanguageChange,
    setTopicRows,
    setCompetitorRows,
    setPromptRows,
    handleContinue,
    handleBack,
  };
}
