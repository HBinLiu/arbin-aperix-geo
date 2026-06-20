type SetupLoadingFlags = {
  discovering: boolean;
  loadingTopics: boolean;
  generatingPrompts: boolean;
};

/** 右侧竖向步骤条：异步加载时指向即将进入的步骤 */
export function setupVerticalStep(step: number, flags: SetupLoadingFlags): number {
  if (step === 1 && flags.loadingTopics) return 2;
  if (step === 2 && flags.generatingPrompts) return 3;
  return step;
}

export function setupStepHeader(
  step: number,
  flags: SetupLoadingFlags,
): { title: string; subtitle: string } | null {
  if (step === 1 && flags.discovering) {
    return {
      title: "研究竞争对手",
      subtitle: "我们正在分析您所在的市场中最相关的竞争对手。",
    };
  }
  if (step === 1 && flags.loadingTopics) {
    return {
      title: "正在生成主题",
      subtitle: "我们正在根据您的竞品与市场分析生成主题。",
    };
  }
  if (step === 2 && flags.generatingPrompts) {
    return {
      title: "生成初始提示词",
      subtitle: "我们正基于您选择的主题、竞争对手和市场分析生成个性化提示词。",
    };
  }
  if (step === 1) {
    return {
      title: "你们的主要竞争对手是谁？",
      subtitle: "我们将展示您的可见度与他们的相比如何。",
    };
  }
  if (step === 2) {
    return {
      title: "审查监测主题",
      subtitle: "我们已根据您的品牌和竞争对手生成主题，请选择用于生成提示词的主题。",
    };
  }
  if (step === 3) {
    return {
      title: "查看您的初始提示词",
      subtitle:
        "您的提示词列表基于品牌画像、所选主题、目标受众与竞争格局生成，用于监测 AI 对话中的品牌可见度。",
    };
  }
  return null;
}
