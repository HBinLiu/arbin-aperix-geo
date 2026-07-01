import type { SubjectMode } from "@/types";

type SetupLoadingFlags = {
  discovering: boolean;
  loadingTopics: boolean;
  generatingPrompts: boolean;
};

/** 右侧竖向步骤条：异步加载时指向即将进入的步骤 */
export function setupVerticalStep(step: number, mode: SubjectMode, flags: SetupLoadingFlags): number {
  const topicsStep = mode === "brand" ? 3 : 2;
  const promptsStep = mode === "brand" ? 4 : 3;
  if (step === (mode === "brand" ? 2 : 1) && flags.loadingTopics) return topicsStep;
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

  if (mode === "brand" && step === 1 && flags.discovering) {
    return {
      title: "正在分析品牌资料",
      subtitle: "我们正在根据您提供的介绍与资料生成画像并发现竞品。",
    };
  }
  if (step === competitorStep && flags.discovering) {
    return {
      title: "研究竞争对手",
      subtitle: "我们正在分析您所在的市场中最相关的竞争对手。",
    };
  }
  if (step === topicsStep && flags.loadingTopics) {
    return {
      title: "正在生成主题",
      subtitle: "我们正在根据您的竞品与市场分析生成主题。",
    };
  }
  if (step === topicsStep && flags.generatingPrompts) {
    return {
      title: "生成初始提示词",
      subtitle: "我们正基于您选择的主题、竞争对手和市场分析生成个性化提示词。",
    };
  }
  if (mode === "brand" && step === 1) {
    return {
      title: "完善品牌资料",
      subtitle: "请填写品牌介绍并可选上传资料，我们将据此生成监测画像。",
    };
  }
  if (step === competitorStep) {
    return {
      title: "你们的主要竞争对手是谁？",
      subtitle: "我们将展示您的可见度与他们的相比如何。",
    };
  }
  if (step === topicsStep) {
    return {
      title: "审查监测主题",
      subtitle: "我们已根据您的品牌和竞争对手生成主题，请选择用于生成提示词的主题。",
    };
  }
  if (step === promptsStep) {
    return {
      title: "查看您的初始提示词",
      subtitle:
        "您的提示词列表基于品牌画像、所选主题、目标受众与竞争格局生成，用于监测 AI 对话中的品牌可见度。",
    };
  }
  return null;
}
