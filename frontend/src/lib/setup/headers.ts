import type { SubjectMode } from "@/types";

type SetupLoadingFlags = {
  loadingTopics: boolean;
  generatingPrompts: boolean;
};

/** 右侧竖向步骤条：生成提示词时指向即将进入的步骤 */
export function setupVerticalStep(step: number, mode: SubjectMode, flags: SetupLoadingFlags): number {
  const topicsStep = mode === "brand" ? 3 : 2;
  const promptsStep = mode === "brand" ? 4 : 3;
  if (step === topicsStep && flags.generatingPrompts) return promptsStep;
  return step;
}

export function setupStepHeader(
  step: number,
  mode: SubjectMode,
  flags: SetupLoadingFlags,
): { title: string; subtitle: string } | null {
  const competitorStep = mode === "brand" ? 2 : 1;
  const topicsStep = mode === "brand" ? 3 : 2;
  const promptsStep = mode === "brand" ? 4 : 3;

  if (step === topicsStep && flags.loadingTopics) {
    return {
      title: "正在准备主题",
      subtitle: "若画像仍在生成将稍候；就绪后载入默认监测主题。",
    };
  }
  if (step === topicsStep && flags.generatingPrompts) {
    return {
      title: "生成初始提示词",
      subtitle: "正在生成可编辑的提示词初版，完成后续可随时修改。",
    };
  }
  if (mode === "brand" && step === 1) {
    return {
      title: "完善品牌资料",
      subtitle: "请填写品牌介绍并可选上传资料。",
    };
  }
  if (step === competitorStep) {
    return {
      title: "添加主要竞争对手",
      subtitle: "请添加竞品品牌与官网，用于采样监测。",
    };
  }
  if (step === topicsStep) {
    return {
      title: "审查监测主题",
      subtitle: "默认来自画像关键词，可自定义主题后生成提示词。",
    };
  }
  if (step === promptsStep) {
    return {
      title: "查看初始提示词",
      subtitle: "以下为系统生成的初版，请按需编辑；正式监测以您确认为准。",
    };
  }
  return null;
}
