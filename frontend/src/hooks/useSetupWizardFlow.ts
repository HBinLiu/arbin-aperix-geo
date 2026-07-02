import * as React from "react";

import {
  createBrandSetupSession,
  deleteSetupMaterialFile,
  discoverSetup,
  finalizeSetup,
  generateSetupPrompts,
  generateSetupTopics,
  saveSetupMaterials,
  uploadSetupMaterialFile,
} from "@/api/setup";
import { maxCompetitorsPerSubject } from "@/lib/billing/limits";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { coalesceWebsiteUrl, hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import {
  clearSetupCache,
  defaultSetupCache,
  hasAnyBrandMaterial,
  loadSetupCache,
  MAX_SETUP_UPLOAD_FILES,
  rowsToPersist,
  saveSetupCache,
  selectedPromptRows,
  selectedTopicNames,
  selectedTopicRows,
  setupCompetitorStep,
  setupMaxStep,
  setupPromptsStep,
  setupStepHeader,
  setupStepLabels,
  setupTopicsStep,
  setupVerticalStep,
} from "@/lib/setup";
import { toast } from "@/lib/toast";
import type { CompetitorRow, PromptRow, SetupUploadFile, SubjectMode, TopicRow } from "@/types";

type UseSetupWizardFlowOptions = {
  onCompleted: (subjectId: string) => void;
};

export function useSetupWizardFlow({ onCompleted }: UseSetupWizardFlowOptions) {
  const initial = React.useMemo(() => loadSetupCache() ?? defaultSetupCache(), []);
  const { data: subscription } = useTenantSubscription();
  const maxCompetitors = maxCompetitorsPerSubject(subscription);

  const [step, setStep] = React.useState(initial.step);
  const [mode, setMode] = React.useState<SubjectMode>(initial.mode);
  const [websiteUrl, setWebsiteUrl] = React.useState(initial.websiteUrl);
  const [brandName, setBrandName] = React.useState(initial.brandName);
  const [brandIntro, setBrandIntro] = React.useState(initial.brandIntro);
  const [brandWebsiteUrl, setBrandWebsiteUrl] = React.useState(initial.brandWebsiteUrl);
  const [uploadFiles, setUploadFiles] = React.useState<SetupUploadFile[]>(initial.uploadFiles);
  const [region, setRegion] = React.useState(initial.region);
  const [language, setLanguage] = React.useState(initial.language);
  const [sessionId, setSessionId] = React.useState(initial.sessionId);
  const [topicRows, setTopicRows] = React.useState<TopicRow[]>(initial.topicRows);
  const [competitorRows, setCompetitorRows] = React.useState<CompetitorRow[]>(initial.competitorRows);
  const [promptRows, setPromptRows] = React.useState<PromptRow[]>(initial.promptRows);
  const [submitting, setSubmitting] = React.useState(false);
  const [discovering, setDiscovering] = React.useState(false);
  const [uploadingFiles, setUploadingFiles] = React.useState(false);
  const [loadingTopics, setLoadingTopics] = React.useState(false);
  const [generatingPrompts, setGeneratingPrompts] = React.useState(false);

  const maxStep = setupMaxStep(mode);
  const setupLabel = mode === "domain" ? "网站设置" : "品牌设置";
  const stepLabels = setupStepLabels(mode, setupLabel);
  const busy = discovering || loadingTopics || generatingPrompts || submitting;

  const hostPreview = hostnameFromWebsiteInput(websiteUrl);
  const activeTopics = React.useMemo(() => selectedTopicRows(topicRows), [topicRows]);

  React.useEffect(() => {
    saveSetupCache({
      sessionId,
      mode,
      websiteUrl,
      brandName,
      brandIntro,
      brandWebsiteUrl,
      uploadFiles,
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
    brandIntro,
    brandWebsiteUrl,
    uploadFiles,
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
    if (fromStep <= setupCompetitorStep(mode)) {
      setTopicRows([]);
      setPromptRows([]);
      return;
    }
    if (fromStep <= setupTopicsStep(mode)) {
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
    setStep(0);
    setBrandIntro("");
    setBrandWebsiteUrl("");
    setUploadFiles([]);
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

  const validateMaterials = (): boolean => {
    if (!sessionId) {
      toast.error("会话已失效，请返回上一步。");
      return false;
    }
    const url = brandWebsiteUrl.trim();
    if (url) {
      const host = hostnameFromWebsiteInput(url);
      if (!host || host.length < 3) {
        toast.error("请填写有效的品牌 URL。");
        return false;
      }
    }
    if (!hasAnyBrandMaterial({ brandWebsiteUrl, brandIntro, uploadFiles })) {
      toast.error("请至少填写品牌 URL、品牌介绍或上传文件其中一项。");
      return false;
    }
    return true;
  };

  const validateCompetitors = (): boolean => {
    const { competitors } = rowsToPersist(mode, competitorRows);
    if (mode === "domain" && competitors.filter((c) => c.domain).length < 1) {
      toast.error("请至少选择一个竞品域名。");
      return false;
    }
    if (mode === "brand" && competitors.filter((c) => c.brand).length < 1) {
      toast.error("请至少选择一个竞品品牌。");
      return false;
    }
    return true;
  };

  const validateTopics = (): boolean => {
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

  const validatePrompts = (): boolean => {
    if (selectedPromptRows(promptRows).length < 1) {
      toast.error("请至少选择一条提示词。");
      return false;
    }
    return true;
  };

  const runDiscover = async (targetStep: number) => {
    setDiscovering(true);
    setStep(targetStep);
    resetDownstream(0);
    try {
      const result = await discoverSetup({
        mode,
        domain: mode === "domain" ? websiteUrl.trim() : "",
        brand: mode === "brand" ? brandName.trim() : "",
        region,
        language,
        sessionId: sessionId || undefined,
        maxCompetitors,
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
      setStep(mode === "brand" ? 1 : 0);
    } finally {
      setDiscovering(false);
    }
  };

  const runCreateBrandSession = async () => {
    try {
      const result = await createBrandSetupSession({
        brand: brandName.trim(),
        region,
        language,
        sessionId: sessionId || undefined,
      });
      setSessionId(result.sessionId);
      setStep(1);
    } catch {
      /* API 拦截器已弹出 Toast */
    }
  };

  const runSaveMaterialsAndDiscover = async () => {
    if (!validateMaterials()) return;
    setDiscovering(true);
    setStep(2);
    resetDownstream(1);
    try {
      await saveSetupMaterials({
        sessionId,
        brandIntro,
        brandWebsiteUrl: coalesceWebsiteUrl(
          brandWebsiteUrl,
          registrableDomain(brandWebsiteUrl),
        ),
      });
      const result = await discoverSetup({
        mode: "brand",
        domain: "",
        brand: brandName.trim(),
        region,
        language,
        sessionId,
        maxCompetitors,
      });
      setSessionId(result.sessionId);
      setCompetitorRows(result.competitorRows);
      if (result.competitorRows.length === 0) {
        toast.info("未发现符合条件的竞品品牌，请手动添加。");
      }
    } catch {
      setStep(1);
    } finally {
      setDiscovering(false);
    }
  };

  const runLoadTopics = async () => {
    if (!sessionId) {
      toast.error("会话已失效，请返回上一步重新分析。");
      return;
    }
    setLoadingTopics(true);
    setStep(setupTopicsStep(mode));
    setTopicRows([]);
    setPromptRows([]);
    try {
      const { topicRows: rows } = await generateSetupTopics({
        sessionId,
        mode,
        competitorRows,
      });
      setTopicRows(rows);
    } catch {
      setStep(setupCompetitorStep(mode));
    } finally {
      setLoadingTopics(false);
    }
  };

  React.useEffect(() => {
    const topicsStep = setupTopicsStep(mode);
    if (step !== topicsStep) return;
    if (topicRows.length > 0) return;
    if (!sessionId) return;
    void runLoadTopics();
    // 缓存恢复到「审查主题」但无 topicRows 时补拉一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runGeneratePrompts = async () => {
    if (!sessionId) return;
    setGeneratingPrompts(true);
    const excludePrompts = selectedPromptRows(promptRows).map((row) => row.text);
    resetDownstream(setupTopicsStep(mode));
    try {
      const rows = await generateSetupPrompts({
        sessionId,
        topics: activeTopics,
        excludePrompts,
      });
      setPromptRows(rows);
      setStep(setupPromptsStep(mode));
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

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files?.length || !sessionId) {
      if (!sessionId) toast.error("请先完成品牌设置。");
      return;
    }
    const remaining = MAX_SETUP_UPLOAD_FILES - uploadFiles.length;
    if (remaining <= 0) {
      toast.error(`最多上传 ${MAX_SETUP_UPLOAD_FILES} 个文件。`);
      return;
    }
    setUploadingFiles(true);
    try {
      const batch = Array.from(files).slice(0, remaining);
      const uploaded: SetupUploadFile[] = [];
      for (const file of batch) {
        uploaded.push(await uploadSetupMaterialFile({ sessionId, file }));
      }
      setUploadFiles((prev) => [...prev, ...uploaded]);
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setUploadingFiles(false);
    }
  };

  const handleRemoveUploadFile = async (fileId: string) => {
    if (!sessionId) return;
    setUploadingFiles(true);
    try {
      await deleteSetupMaterialFile({ sessionId, fileId });
      setUploadFiles((prev) => prev.filter((item) => item.id !== fileId));
    } catch {
      /* API 拦截器已弹出 Toast */
    } finally {
      setUploadingFiles(false);
    }
  };

  const handleContinue = () => {
    if (step === 0) {
      if (!validateStep0()) return;
      if (mode === "brand") {
        void runCreateBrandSession();
      } else {
        void runDiscover(setupCompetitorStep(mode));
      }
      return;
    }
    if (mode === "brand" && step === 1) {
      void runSaveMaterialsAndDiscover();
      return;
    }
    if (step === setupCompetitorStep(mode)) {
      if (!validateCompetitors()) return;
      void runLoadTopics();
      return;
    }
    if (step === setupTopicsStep(mode)) {
      if (!validateTopics()) return;
      void runGeneratePrompts();
      return;
    }
    if (step === setupPromptsStep(mode)) {
      if (!validatePrompts()) return;
      void runFinalize();
    }
  };

  const handleBack = () => {
    if (busy) return;
    if (step === 0) return;
    if (step === setupCompetitorStep(mode)) {
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

  const handleBrandIntroChange = (value: string) => {
    setBrandIntro(value);
    if (sessionId && step > 1) clearSession();
  };

  const handleBrandWebsiteUrlChange = (value: string) => {
    setBrandWebsiteUrl(value);
    if (sessionId && step > 1) clearSession();
  };

  const shellHeader = setupStepHeader(step, mode, {
    discovering,
    loadingTopics,
    generatingPrompts,
  });

  const verticalStep = setupVerticalStep(step, mode, {
    discovering,
    loadingTopics,
    generatingPrompts,
  });

  return {
    step,
    maxStep,
    verticalStep,
    mode,
    websiteUrl,
    brandName,
    brandIntro,
    brandWebsiteUrl,
    uploadFiles,
    region,
    language,
    topicRows,
    competitorRows,
    promptRows,
    submitting,
    discovering,
    uploadingFiles,
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
    setBrandIntro: handleBrandIntroChange,
    setBrandWebsiteUrl: handleBrandWebsiteUrlChange,
    handleUploadFiles,
    handleRemoveUploadFile,
    setRegion: handleRegionChange,
    setLanguage: handleLanguageChange,
    setTopicRows,
    setCompetitorRows,
    setPromptRows,
    handleContinue,
    handleBack,
  };
}
